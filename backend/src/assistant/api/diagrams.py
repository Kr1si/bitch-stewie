"""Serve generated .drawio diagrams for a project's repo (Phase 5+ UI)."""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from assistant.memory.db import get_session_factory
from assistant.memory.models import Project

router = APIRouter(prefix="/api/projects/{project_id}/diagrams")


async def _project_repo(project_id: uuid.UUID) -> str:
    async with get_session_factory()() as s:
        row = (await s.execute(select(Project).where(Project.id == project_id))
               ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "project not found")
    if not row.repo_path:
        raise HTTPException(404, "project has no registered repo path")
    return row.repo_path


@router.get("")
async def list_diagrams(project_id: uuid.UUID):
    """List generated .drawio files (basename + modified time) under <repo>/diagrams."""
    repo = await _project_repo(project_id)
    diagrams_dir = Path(repo) / "diagrams"
    if not diagrams_dir.is_dir():
        return []
    files = sorted(diagrams_dir.glob("*.drawio"), key=lambda p: p.stat().st_mtime,
                   reverse=True)
    return [{"name": p.name, "modified": int(p.stat().st_mtime)} for p in files]


@router.get("/{name}")
async def get_diagram(project_id: uuid.UUID, name: str):
    """Return the raw .drawio XML for the embed's `xml` prop."""
    repo = await _project_repo(project_id)
    # basename only — never escape the diagrams dir
    path = (Path(repo) / "diagrams" / Path(name).name).resolve()
    diagrams_dir = (Path(repo) / "diagrams").resolve()
    if not path.is_relative_to(diagrams_dir) or not path.is_file():
        raise HTTPException(404, "diagram not found")
    return FileResponse(str(path), media_type="application/xml", filename=path.name)