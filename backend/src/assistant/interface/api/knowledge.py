"""Knowledge base endpoints: search and ingestion for the web UI."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from assistant.application.services.knowledge_service import (
    collection_stats,
    hybrid_search,
    ingest_path,
    ingest_text,
    list_collections,
)

router = APIRouter(prefix="/api/knowledge")


class SearchIn(BaseModel):
    query: str
    project: str | None = None
    limit: int = 5


class IngestTextIn(BaseModel):
    text: str
    source: str
    project: str | None = None


class IngestPathIn(BaseModel):
    path: str
    project: str | None = None


@router.get("/collections")
async def collections() -> list[dict[str, Any]]:
    """All kb_* collections with point + source counts for the Knowledge overview."""
    def _gather() -> list[dict[str, Any]]:
        return [{"name": n, **collection_stats(n)} for n in list_collections()]
    return await run_in_threadpool(_gather)


@router.get("/collections/{name}/sources")
async def collection_sources(name: str) -> dict[str, Any]:
    """Distinct sources + per-source chunk counts for one collection."""
    return await run_in_threadpool(collection_stats, name)


@router.post("/search")
async def search(body: SearchIn) -> list[dict[str, Any]]:
    # embedding + qdrant calls are sync/blocking
    return await run_in_threadpool(hybrid_search, body.query, body.project, body.limit)


@router.post("/ingest-text")
async def ingest_text_ep(body: IngestTextIn) -> dict[str, Any]:
    n = await run_in_threadpool(ingest_text, body.text, body.source, body.project)
    return {"chunks": n}


@router.post("/ingest-path")
async def ingest_path_ep(body: IngestPathIn) -> dict[str, Any]:
    return await run_in_threadpool(ingest_path, body.path, body.project)
