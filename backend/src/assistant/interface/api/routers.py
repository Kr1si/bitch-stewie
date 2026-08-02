"""Read/manage endpoints for the web UI (Phase 5 consumes these)."""

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select

from assistant.application.services.memory_service import (
    Approval,
    CCRun,
    CCRunEvent,
    Decision,
    Project,
    get_session_factory,
)

router = APIRouter(prefix="/api")


class RunIn(BaseModel):
    goal: str
    project_id: uuid.UUID
    constraints: list[str] = []
    acceptance_criteria: list[str] = []
    parallel: bool = False


@router.post("/cc-runs", status_code=202)
async def start_run(body: RunIn) -> dict[str, Any]:
    """Enqueue a delegation on the worker queue; the Runs UI picks it up by polling."""
    from assistant.application.services.jobs_service import delegate_brief

    async with get_session_factory()() as s:
        project = await s.get(Project, body.project_id)
        if project is None:
            raise HTTPException(404, "project not found")
        if not project.repo_path:
            raise HTTPException(422, f"project '{project.name}' has no repo_path configured")

    job_id = delegate_brief.defer(
        goal=body.goal, repo_path=project.repo_path,
        constraints=body.constraints, acceptance_criteria=body.acceptance_criteria,
        parallel=body.parallel,
    )
    return {"job_id": job_id}


class ProjectIn(BaseModel):
    name: str = ""
    description: str = ""
    repo_path: str | None = None
    git_url: str | None = None  # GitHub URL / owner/repo -> clone into projects_path


@router.get("/projects")
async def list_projects() -> list[dict[str, Any]]:
    async with get_session_factory()() as s:
        rows = (await s.execute(select(Project))).scalars().all()
    return [{"id": str(p.id), "name": p.name, "status": p.status,
             "repo_path": p.repo_path, "description": p.description} for p in rows]


@router.post("/projects", status_code=201)
async def create_project(body: ProjectIn) -> dict[str, Any]:
    """Create a project. Two modes:

    - Local: ``name`` + optional ``repo_path`` (folder on disk).
    - From GitHub: ``git_url`` (https/ssh/owner/repo). The repo is validated
      and cloned via the unified ``gh`` client into ``projects_path``; ``name``
      and ``description`` auto-derive from the repo metadata if not given.
    """
    from assistant.infrastructure.github import (
        clone_repo,
        parse_git_url,
        repo_info,
    )
    from assistant.shared.config import get_settings

    name = (body.name or "").strip()
    repo_path: str | None = body.repo_path
    description = body.description

    if body.git_url:
        owner, repo = parse_git_url(body.git_url)
        info = repo_info(f"{owner}/{repo}")  # raises RuntimeError if inaccessible
        if not name:
            name = info["name"]
        if not description:
            description = (info.get("description") or "")[:500]
        dest = Path(get_settings().projects_path) / name
        clone_repo(f"{owner}/{repo}", dest)
        repo_path = str(dest)

    if not name:
        raise HTTPException(422, "name is required (or provide a git_url to derive it)")

    async with get_session_factory()() as s:
        exists = (
            await s.execute(select(Project).where(Project.name == name))
        ).scalar_one_or_none()
        if exists:
            raise HTTPException(409, f"project '{name}' exists")
        p = Project(name=name, description=description, repo_path=repo_path)
        s.add(p)
        await s.commit()
        return {"id": str(p.id), "name": p.name}


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID) -> None:
    """Delete a project and its decisions.

    Runs in a single transaction: decisions are deleted first (no FK on
    cascade), then the project. CC runs / sessions / messages are left in
    place as historical records — delete those explicitly if needed.
    """
    async with get_session_factory()() as s:
        project = await s.get(Project, project_id)
        if project is None:
            raise HTTPException(404, "project not found")
        await s.execute(delete(Decision).where(Decision.project_id == project_id))
        await s.delete(project)
        await s.commit()


@router.get("/projects/{project_id}/decisions")
async def list_decisions(project_id: uuid.UUID) -> list[dict[str, Any]]:
    async with get_session_factory()() as s:
        rows = (await s.execute(select(Decision).where(Decision.project_id == project_id)
                                .order_by(Decision.created_at))).scalars().all()
    return [{"id": str(d.id), "title": d.title, "decision": d.decision,
             "status": d.status, "created_at": d.created_at.isoformat()} for d in rows]


@router.get("/approvals")
async def list_approvals(status: str | None = None) -> list[dict[str, Any]]:
    async with get_session_factory()() as s:
        q = select(Approval).order_by(Approval.created_at.desc()).limit(50)
        if status:
            q = q.filter(Approval.status == status)
        rows = (await s.execute(q)).scalars().all()
    return [{"id": str(a.id), "kind": a.kind, "status": a.status.value,
             "thread_id": a.thread_id, "payload": a.payload,
             "created_at": a.created_at.isoformat()} for a in rows]


@router.get("/cc-runs")
async def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    async with get_session_factory()() as s:
        rows = (await s.execute(select(CCRun).order_by(CCRun.created_at.desc())
                                .limit(limit))).scalars().all()
    return [{"id": str(r.id), "status": r.status.value, "model": r.model,
             "repo_path": r.repo_path, "review_iterations": r.review_iterations,
             "result": r.result, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/cc-runs/{run_id}/events")
async def run_events(run_id: uuid.UUID, limit: int = 200) -> list[dict[str, Any]]:
    async with get_session_factory()() as s:
        rows = (await s.execute(select(CCRunEvent).where(CCRunEvent.run_id == run_id)
                                .order_by(CCRunEvent.created_at).limit(limit))).scalars().all()
    return [{"type": e.event_type, "payload": e.payload,
             "at": e.created_at.isoformat()} for e in rows]
