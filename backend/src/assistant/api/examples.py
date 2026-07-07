"""Reference examples library (diagrams + docs).

The architect/doc-writer subagents load these when creating a new diagram or
doc to mimic style/quality. Files live on the host filesystem under
ASSISTANT_EXAMPLES_PATH so delegated Claude Code instances (which run on the
host with file access) can read binary examples directly; only text examples
are inlined into the orchestrator's own context via the example tools.
"""

import re
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from assistant.config import get_settings
from assistant.memory.db import get_session_factory
from assistant.memory.models import Example, Project

router = APIRouter(prefix="/api/examples")

_KNOWN_KINDS = {"diagram", "doc"}
_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _slug(name: str) -> str:
    return _SAFE_RE.sub("_", (name or "global").strip()).lower() or "global"


def _examples_root() -> str:
    path = get_settings().examples_path
    if not path:
        raise HTTPException(500, "ASSISTANT_EXAMPLES_PATH is not configured.")
    return path


def _storage_dir(project: str, kind: str) -> str:
    import os
    root = _examples_root()
    out = os.path.join(root, _slug(project), kind)
    os.makedirs(out, exist_ok=True)
    return out


def _to_dict(e: Example) -> dict:
    return {"id": str(e.id), "project_id": str(e.project_id) if e.project_id else None,
            "kind": e.kind, "filename": e.filename, "mime": e.mime, "note": e.note,
            "created_at": e.created_at.isoformat()}


async def _resolve_project_id(name: str) -> uuid.UUID | None:
    if not name or name == "global":
        return None
    async with get_session_factory()() as s:
        row = (await s.execute(select(Project).where(Project.name == name))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, f"project '{name}' not found")
    return row.id


@router.post("")
async def upload(
    file: UploadFile = File(...),
    project: str = Form("global"),
    kind: str = Form(...),
    note: str = Form(""),
):
    """Upload a reference example (.drawio/.xml/.png for diagrams; .md/.docx/.pdf for docs)."""
    import os
    if kind not in _KNOWN_KINDS:
        raise HTTPException(400, f"kind must be one of {sorted(_KNOWN_KINDS)}")
    project_id = await _resolve_project_id(project)
    filename = os.path.basename(file.filename or "example")
    filename = _SAFE_RE.sub("_", filename) or f"example_{uuid.uuid4().hex[:8]}"
    dest_dir = _storage_dir(project, kind)
    dest = os.path.join(dest_dir, filename)
    with open(dest, "wb") as fh:
        fh.write(await file.read())
    async with get_session_factory()() as s:
        row = Example(project_id=project_id, kind=kind, filename=filename,
                      storage_path=dest, mime=file.content_type or "", note=note)
        s.add(row)
        await s.commit()
        return _to_dict(row)


@router.get("")
async def list_examples(project: str = "", kind: str = ""):
    async with get_session_factory()() as s:
        q = select(Example).order_by(Example.created_at.desc())
        if kind:
            q = q.where(Example.kind == kind)
        if project and project != "global":
            proj = (await s.execute(select(Project).where(Project.name == project))).scalar_one_or_none()
            if proj is None:
                return []
            q = q.where(Example.project_id == proj.id)
        elif project == "global":
            q = q.where(Example.project_id.is_(None))
        rows = (await s.execute(q)).scalars().all()
    return [_to_dict(e) for e in rows]


@router.get("/{example_id}/content")
async def example_content(example_id: uuid.UUID):
    async with get_session_factory()() as s:
        row = (await s.execute(select(Example).where(Example.id == example_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "example not found")
    import os
    if not os.path.isfile(row.storage_path):
        raise HTTPException(410, "example file missing on disk")
    return FileResponse(row.storage_path, filename=row.filename, media_type=row.mime or None)


@router.delete("/{example_id}")
async def delete_example(example_id: uuid.UUID):
    import os
    async with get_session_factory()() as s:
        row = (await s.execute(select(Example).where(Example.id == example_id))).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "example not found")
        try:
            os.remove(row.storage_path)
        except OSError:
            pass  # row is the source of truth; still drop it
        await s.delete(row)
        await s.commit()
    return {"deleted": str(example_id)}