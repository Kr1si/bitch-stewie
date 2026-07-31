"""Knowledge/RAG service facade.

Re-exports the ingestion and search entry points the interface layer needs,
so routers never import `assistant.infrastructure.rag` directly.
"""

from assistant.infrastructure.rag.ingest import ingest_path, ingest_text
from assistant.infrastructure.rag.store import (
    collection_stats,
    hybrid_search,
    list_collections,
)

__all__ = [
    "collection_stats",
    "hybrid_search",
    "ingest_path",
    "ingest_text",
    "list_collections",
]
