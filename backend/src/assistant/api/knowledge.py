"""Knowledge base endpoints: search and ingestion for the web UI."""

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from assistant.rag.ingest import ingest_path, ingest_text
from assistant.rag.store import hybrid_search

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


@router.post("/search")
async def search(body: SearchIn):
    # embedding + qdrant calls are sync/blocking
    return await run_in_threadpool(hybrid_search, body.query, body.project, body.limit)


@router.post("/ingest-text")
async def ingest_text_ep(body: IngestTextIn):
    n = await run_in_threadpool(ingest_text, body.text, body.source, body.project)
    return {"chunks": n}


@router.post("/ingest-path")
async def ingest_path_ep(body: IngestPathIn):
    return await run_in_threadpool(ingest_path, body.path, body.project)
