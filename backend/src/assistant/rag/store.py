"""Qdrant hybrid store: bge-m3 dense (via Ollama) + BM25 sparse (fastembed).

One collection per project plus a shared 'global' collection. Hybrid queries
use Qdrant's Query API with RRF fusion over dense and sparse prefetches.
"""

import hashlib
import uuid

import httpx
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient, models

from assistant.config import get_settings

DENSE = "dense"
SPARSE = "sparse"
_DIMS = 1024  # bge-m3

_sparse_model: SparseTextEmbedding | None = None
_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=get_settings().qdrant_url)
    return _client


def _sparse() -> SparseTextEmbedding:
    global _sparse_model
    if _sparse_model is None:
        _sparse_model = SparseTextEmbedding("Qdrant/bm25")
    return _sparse_model


def collection_name(project: str | None) -> str:
    return f"kb_{(project or 'global').lower().replace(' ', '_')}"


def ensure_collection(name: str) -> None:
    client = get_client()
    if client.collection_exists(name):
        return
    client.create_collection(
        collection_name=name,
        vectors_config={DENSE: models.VectorParams(size=_DIMS, distance=models.Distance.COSINE)},
        sparse_vectors_config={SPARSE: models.SparseVectorParams(
            modifier=models.Modifier.IDF)},
    )


def embed_dense(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    resp = httpx.post(f"{settings.ollama_base_url}/api/embed",
                      json={"model": settings.embedding_model, "input": texts}, timeout=300)
    resp.raise_for_status()
    return resp.json()["embeddings"]


def upsert_chunks(project: str | None, chunks: list[dict]) -> int:
    """chunks: [{"text": ..., "source": ..., "kind": doc|research|conversation}]"""
    if not chunks:
        return 0
    name = collection_name(project)
    ensure_collection(name)
    texts = [c["text"] for c in chunks]
    dense = embed_dense(texts)
    sparse = list(_sparse().embed(texts))
    points = []
    for chunk, dv, sv in zip(chunks, dense, sparse):
        # deterministic id: re-ingesting the same source+text overwrites, no dupes
        digest = hashlib.sha256((chunk["source"] + chunk["text"]).encode()).hexdigest()[:32]
        points.append(models.PointStruct(
            id=str(uuid.UUID(digest)),
            vector={DENSE: dv, SPARSE: models.SparseVector(
                indices=sv.indices.tolist(), values=sv.values.tolist())},
            payload={"text": chunk["text"], "source": chunk["source"],
                     "kind": chunk.get("kind", "doc")},
        ))
    get_client().upsert(collection_name=name, points=points)
    return len(points)


def hybrid_search(query: str, project: str | None = None, limit: int = 5) -> list[dict]:
    name = collection_name(project)
    if not get_client().collection_exists(name):
        return []
    dense = embed_dense([query])[0]
    sv = next(iter(_sparse().embed([query])))
    result = get_client().query_points(
        collection_name=name,
        prefetch=[
            models.Prefetch(query=dense, using=DENSE, limit=limit * 3),
            models.Prefetch(query=models.SparseVector(
                indices=sv.indices.tolist(), values=sv.values.tolist()),
                using=SPARSE, limit=limit * 3),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=limit,
    )
    return [{"text": p.payload["text"], "source": p.payload["source"],
             "kind": p.payload.get("kind"), "score": p.score} for p in result.points]


def list_collections() -> list[str]:
    """All knowledge-base collections (kb_*), sorted."""
    names = [c.name for c in get_client().get_collections().collections
             if c.name.startswith("kb_")]
    return sorted(names)


def collection_stats(name: str) -> dict:
    """{points, sources} for a collection. Points via count; distinct sources
    via a capped scroll (knowledge collections are small)."""
    client = get_client()
    if not client.collection_exists(name):
        return {"points": 0, "sources": []}
    points = client.count(collection_name=name, exact=True).count
    sources: dict[str, int] = {}
    if points:
        seen_ids: set[str] = set()
        offset = None
        for _ in range(50):  # cap at ~50 * 256 = 12.8k points
            rec, offset = client.scroll(collection_name=name, limit=256,
                                         with_payload=True, with_vectors=False,
                                         offset=offset)
            for p in rec:
                src = (p.payload or {}).get("source", "")
                sources[src] = sources.get(src, 0) + 1
            if offset is None:
                break
    return {"points": points,
            "sources": [{"source": s, "chunks": n}
                         for s, n in sorted(sources.items(),
                                            key=lambda kv: kv[1], reverse=True)]}
