"""Read/manage endpoints for the web UI (Phase 5 consumes these)."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from assistant.memory.db import get_session_factory
from assistant.memory.models import Approval, CCRun, CCRunEvent, Decision, Project

router = APIRouter(prefix="/api")


class RunIn(BaseModel):
    goal: str
    project_id: uuid.UUID
    constraints: list[str] = []
    acceptance_criteria: list[str] = []
    parallel: bool = False


@router.post("/cc-runs", status_code=202)
async def start_run(body: RunIn):
    """Enqueue a delegation on the worker queue; the Runs UI picks it up by polling."""
    from assistant.jobs.queue import delegate_brief

    async with get_session_factory()() as s:
        project = await s.get(Project, body.project_id)
        if project is None:
            raise HTTPException(404, "project not found")
        if not project.repo_path:
            raise HTTPException(422, f"project '{project.name}' has no repo_path configured")

    job = delegate_brief.defer(
        goal=body.goal, repo_path=project.repo_path,
        constraints=body.constraints, acceptance_criteria=body.acceptance_criteria,
        parallel=body.parallel,
    )
    return {"job_id": job.id}


class ProjectIn(BaseModel):
    name: str
    description: str = ""
    repo_path: str | None = None


@router.get("/projects")
async def list_projects():
    async with get_session_factory()() as s:
        rows = (await s.execute(select(Project))).scalars().all()
    return [{"id": str(p.id), "name": p.name, "status": p.status,
             "repo_path": p.repo_path, "description": p.description} for p in rows]


@router.post("/projects", status_code=201)
async def create_project(body: ProjectIn):
    async with get_session_factory()() as s:
        exists = (await s.execute(select(Project).where(Project.name == body.name))).scalar_one_or_none()
        if exists:
            raise HTTPException(409, f"project '{body.name}' exists")
        p = Project(name=body.name, description=body.description, repo_path=body.repo_path)
        s.add(p)
        await s.commit()
        return {"id": str(p.id), "name": p.name}


@router.get("/projects/{project_id}/decisions")
async def list_decisions(project_id: uuid.UUID):
    async with get_session_factory()() as s:
        rows = (await s.execute(select(Decision).where(Decision.project_id == project_id)
                                .order_by(Decision.created_at))).scalars().all()
    return [{"id": str(d.id), "title": d.title, "decision": d.decision,
             "status": d.status, "created_at": d.created_at.isoformat()} for d in rows]


@router.get("/approvals")
async def list_approvals(status: str | None = None):
    async with get_session_factory()() as s:
        q = select(Approval).order_by(Approval.created_at.desc()).limit(50)
        if status:
            q = q.filter(Approval.status == status)
        rows = (await s.execute(q)).scalars().all()
    return [{"id": str(a.id), "kind": a.kind, "status": a.status.value,
             "thread_id": a.thread_id, "payload": a.payload,
             "created_at": a.created_at.isoformat()} for a in rows]


@router.get("/cc-runs")
async def list_runs(limit: int = 20):
    async with get_session_factory()() as s:
        rows = (await s.execute(select(CCRun).order_by(CCRun.created_at.desc())
                                .limit(limit))).scalars().all()
    return [{"id": str(r.id), "status": r.status.value, "model": r.model,
             "repo_path": r.repo_path, "review_iterations": r.review_iterations,
             "result": r.result, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/cc-runs/{run_id}/events")
async def run_events(run_id: uuid.UUID, limit: int = 200):
    async with get_session_factory()() as s:
        rows = (await s.execute(select(CCRunEvent).where(CCRunEvent.run_id == run_id)
                                .order_by(CCRunEvent.created_at).limit(limit))).scalars().all()
    return [{"type": e.event_type, "payload": e.payload,
             "at": e.created_at.isoformat()} for e in rows]
