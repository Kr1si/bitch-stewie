"""Ingestion: files/directories/raw text -> chunks -> hybrid store."""

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from assistant.rag.store import upsert_chunks

_SUFFIXES = {".md", ".markdown", ".txt", ".rst"}

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200, chunk_overlap=150, separators=["\n## ", "\n### ", "\n\n", "\n", " "]
)


def ingest_text(text: str, source: str, project: str | None = None, kind: str = "doc") -> int:
    chunks = [{"text": c, "source": source, "kind": kind} for c in _splitter.split_text(text) if c.strip()]
    return upsert_chunks(project, chunks)


def ingest_path(path: str, project: str | None = None, kind: str = "doc") -> dict:
    """Ingest a file or all supported files under a directory."""
    p = Path(path)
    files = [p] if p.is_file() else [f for f in p.rglob("*") if f.suffix.lower() in _SUFFIXES]
    total_chunks = 0
    ingested: list[str] = []
    for f in files:
        if f.suffix.lower() not in _SUFFIXES:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        n = ingest_text(text, source=str(f), project=project, kind=kind)
        if n:
            ingested.append(f.name)
            total_chunks += n
    return {"files": len(ingested), "chunks": total_chunks, "names": ingested[:20]}
