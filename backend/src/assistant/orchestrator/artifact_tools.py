"""Architect and doc-writer tools: diagrams from the LikeC4 model, document export."""

from pathlib import Path

from langchain_core.tools import tool
from sqlalchemy import select

from assistant.diagrams.likec4 import export_drawio, find_model_dir
from assistant.docs_gen.pandoc import export_markdown
from assistant.memory.models import Project
from assistant.memory.sync_db import get_sync_session_factory


def _project_repo(project: str) -> str | None:
    with get_sync_session_factory()() as s:
        row = s.execute(select(Project).where(Project.name == project)).scalar_one_or_none()
        return row.repo_path if row else None


@tool
def update_diagrams(project: str) -> str:
    """Regenerate draw.io diagrams from the project's LikeC4 model (source of truth).

    Exports every LikeC4 view to .drawio files under <repo>/diagrams/.
    """
    repo = _project_repo(project)
    if not repo:
        return f"Project '{project}' has no registered repo path."
    model_dir = find_model_dir(repo)
    if model_dir is None:
        return (f"No .likec4/.c4 model found in {repo}. Create the model first "
                f"(e.g. under {repo}/likec4/).")
    result = export_drawio(model_dir, Path(repo) / "diagrams")
    if not result["ok"]:
        return f"Export failed: {result['stderr']}"
    return "Exported diagrams:\n" + "\n".join(f"- {f}" for f in result["files"])


@tool
def export_document(markdown: str, filename: str, project: str = "", title: str = "") -> str:
    """Export markdown content as a .docx or .pdf deliverable.

    filename must end with .docx or .pdf; the file lands in the project repo's
    docs/ folder (or the current directory if no project repo is registered).
    """
    if not filename.endswith((".docx", ".pdf", ".html")):
        return "filename must end with .docx, .pdf or .html"
    base = _project_repo(project) if project else None
    out = (Path(base) / "docs" / filename) if base else Path("docs") / filename
    result = export_markdown(markdown, out, title=title)
    return f"Written: {result['path']}" if result["ok"] else f"Export failed: {result['stderr']}"


ARCHITECT_TOOLS = [update_diagrams]
DOC_TOOLS = [export_document]
