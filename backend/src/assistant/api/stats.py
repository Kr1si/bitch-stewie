"""Aggregated dashboard statistics: one round-trip for the whole dashboard."""

from fastapi import APIRouter
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from assistant.memory.db import get_session_factory
from assistant.memory.models import (Approval, ApprovalStatus, CCRun, Decision,
                                     Project)
from assistant.rag.store import collection_stats, list_collections

router = APIRouter(prefix="/api/stats")


@router.get("")
async def stats():
    async with get_session_factory()() as s:
        projects = (await s.execute(select(func.count(Project.id)))).scalar_one()

        runs_rows = (await s.execute(
            select(CCRun.status, func.count(CCRun.id)).group_by(CCRun.status)
        )).all()
        runs_by_status = {row[0].value if hasattr(row[0], "value") else str(row[0]):
                          row[1] for row in runs_rows}

        pending_approvals = (await s.execute(
            select(func.count(Approval.id)).where(Approval.status == ApprovalStatus.pending)
        )).scalar_one()

        decisions = (await s.execute(select(func.count(Decision.id)))).scalar_one()

        recent_runs = (await s.execute(
            select(CCRun).order_by(CCRun.created_at.desc()).limit(8)
        )).scalars().all()
        recent_approvals = (await s.execute(
            select(Approval).order_by(Approval.created_at.desc()).limit(8)
        )).scalars().all()
        recent_decisions = (await s.execute(
            select(Decision).order_by(Decision.created_at.desc()).limit(8)
        )).scalars().all()

    collections = await run_in_threadpool(lambda: [
        {"name": n, **collection_stats(n)} for n in list_collections()
    ])
    kb_points = sum(c["points"] for c in collections)
    kb_sources = len({src["source"] for c in collections for src in c["sources"]})

    return {
        "projects": projects,
        "runs_total": sum(runs_by_status.values()),
        "runs_by_status": runs_by_status,
        "pending_approvals": pending_approvals,
        "decisions": decisions,
        "kb_points": kb_points,
        "kb_sources": kb_sources,
        "collections": collections,
        "recent": {
            "runs": [{"id": str(r.id), "status": r.status.value, "model": r.model,
                      "repo_path": r.repo_path,
                      "created_at": r.created_at.isoformat()} for r in recent_runs],
            "approvals": [{"id": str(a.id), "kind": a.kind, "status": a.status.value,
                           "created_at": a.created_at.isoformat()} for a in recent_approvals],
            "decisions": [{"id": str(d.id), "title": d.title, "status": d.status,
                           "created_at": d.created_at.isoformat()} for d in recent_decisions],
        },
    }