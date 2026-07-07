"""Tools that expose the reference examples library to the architect and
doc-writer subagents.

`list_examples` returns metadata (including absolute file paths); the subagent
then passes the relevant paths into a delegated coding brief so the Claude Code
instance — which runs on the host with full file access — reads them directly.
`read_example` inlines *text* examples (markdown, drawio XML, plain text) into
the orchestrator's own context; binary examples (png/docx/pdf) are returned as a
pointer, never their bytes.
"""

from pathlib import Path

from langchain_core.tools import tool
from sqlalchemy import select

from assistant.memory.models import Example, Project
from assistant.memory.sync_db import get_sync_session_factory

_TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".rst", ".drawio", ".xml", ".svg"}


def _project_id(name: str):
    if not name or name == "global":
        return None
    with get_sync_session_factory()() as s:
        row = s.execute(select(Project).where(Project.name == name)).scalar_one_or_none()
    if row is None:
        raise ValueError(f"Unknown project '{name}'.")
    return row.id


def _rows(project: str, kind: str = ""):
    pid = _project_id(project)
    with get_sync_session_factory()() as s:
        q = select(Example).order_by(Example.created_at.desc())
        if kind:
            q = q.where(Example.kind == kind)
        if pid is None:
            q = q.where(Example.project_id.is_(None))
        else:
            q = q.where(Example.project_id == pid)
        return s.execute(q).scalars().all()


@tool
def list_examples(project: str, kind: str = "") -> str:
    """List reference examples for a project (kind: 'diagram', 'doc', or '' for both).

    Each line is: name | kind | path | note. The 'path' is an absolute file path
    you should pass into delegate_coding_task's 'examples' argument so the
    Claude Code instance reads the file directly for style/layout.
    """
    rows = _rows(project, kind)
    if not rows:
        return f"No reference examples for project '{project}'."
    return "\n".join(
        f"{e.filename} | {e.kind} | {e.storage_path} | {e.note}" for e in rows
    )


@tool
def read_example(name: str, project: str, kind: str = "") -> str:
    """Read one reference example into context.

    Text examples (.md/.txt/.drawio/.xml/.svg) are inlined. Binary examples
    (.png/.docx/.pdf) are NOT inlined — the tool returns their path so a
    delegated Claude Code instance can read them directly.
    """
    rows = _rows(project, kind)
    match = next((e for e in rows if e.filename == name), None)
    if match is None:
        return f"No example named '{name}' for project '{project}'."
    suffix = Path(match.filename).suffix.lower()
    if suffix in _TEXT_SUFFIXES:
        try:
            return Path(match.storage_path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"Could not read {match.storage_path}: {exc}"
    return (f"Binary example '{name}' at {match.storage_path} "
            f"(mime {match.mime or 'unknown'}). Do not inline it — pass this path "
            f"to delegate_coding_task's 'examples' so the Claude Code instance "
            f"reads it directly.")


EXAMPLE_TOOLS = [list_examples, read_example]