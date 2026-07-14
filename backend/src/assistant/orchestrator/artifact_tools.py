"""Architect and doc-writer tools: diagrams from the LikeC4 model, document export."""

import re
from datetime import datetime
from pathlib import Path

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from assistant.diagrams.likec4 import export_drawio, find_model_dir
from assistant.docs_gen.pandoc import export_markdown
from assistant.orchestrator.context import current_project


def _project(config: RunnableConfig):
    return current_project(config)


@tool
def update_diagrams(*, config: RunnableConfig) -> str:
    """Regenerate draw.io diagrams from the project's LikeC4 model (source of truth).

    Exports every LikeC4 view to .drawio files under <repo>/diagrams/.
    """
    proj = _project(config)
    repo = proj.repo_path
    if not repo:
        return f"Project '{proj.name}' has no registered repo path."
    model_dir = find_model_dir(repo)
    if model_dir is None:
        return (f"No .likec4/.c4 model found in {repo}. Create the model first "
                f"(e.g. under {repo}/likec4/).")
    result = export_drawio(model_dir, Path(repo) / "diagrams")
    if not result["ok"]:
        return f"Export failed: {result['stderr']}"
    return "Exported diagrams:\n" + "\n".join(f"- {f}" for f in result["files"])


@tool
def export_document(markdown: str, filename: str, title: str = "", *, config: RunnableConfig) -> str:
    """Export markdown content as a .docx or .pdf deliverable.

    filename must end with .docx or .pdf; the file lands in the project repo's
    docs/ folder (or the current directory if the project has no repo path).
    """
    if not filename.endswith((".docx", ".pdf", ".html")):
        return "filename must end with .docx, .pdf or .html"
    base = _project(config).repo_path
    out = (Path(base) / "docs" / filename) if base else Path("docs") / filename
    result = export_markdown(markdown, out, title=title)
    return f"Written: {result['path']}" if result["ok"] else f"Export failed: {result['stderr']}"


ARCHITECT_TOOLS = [update_diagrams]
DOC_TOOLS = [export_document]


def _plan_status(path: Path) -> str:
    """Pull the `status:` value from a plan file's frontmatter (best-effort)."""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("status:"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "unknown"


@tool
def write_plan(slug: str, markdown: str, status: str = "proposed", *, config: RunnableConfig) -> str:
    """Write a future-improvement plan as a dated markdown file in the project's plans/ folder.

    Use this whenever you devise a plan for a future improvement — especially
    self-improvements to this orchestrator — so later iterations can discover
    and pick it up instead of starting from scratch. The file is named
    YYYY-MM-DD-<slug>.md and gets a frontmatter header (status, created, project).
    Writing the same slug on a later date creates a new dated file (history);
    writing the same date+slug overwrites (treat as an update to that plan).

    status is one of: proposed | in_progress | done | dropped.
    """
    proj = _project(config)
    repo = proj.repo_path
    if not repo:
        return f"Project '{proj.name}' has no registered repo path."
    if status not in {"proposed", "in_progress", "done", "dropped"}:
        return f"invalid status '{status}' (use proposed|in_progress|done|dropped)"
    plans_dir = Path(repo) / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    safe_slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-") or "plan"
    path = plans_dir / f"{date}-{safe_slug}.md"
    header = (
        "---\n"
        f"status: {status}\n"
        f"created: {date}\n"
        f"project: {proj.name}\n"
        "---\n\n"
    )
    path.write_text(header + markdown, encoding="utf-8")
    return f"Written plan: {path}"


@tool
def list_plans(*, config: RunnableConfig) -> str:
    """List future-improvement plans in the project's plans/ folder with their status.

    Call this at the start of an improvement session to discover plans already
    recorded so you can iterate on them. Plans are dated markdown files; the
    status comes from each file's frontmatter (proposed|in_progress|done|dropped).
    """
    proj = _project(config)
    repo = proj.repo_path
    if not repo:
        return f"Project '{proj.name}' has no registered repo path."
    plans_dir = Path(repo) / "plans"
    if not plans_dir.is_dir():
        return f"No plans/ folder in {repo}."
    files = sorted(plans_dir.glob("*.md"))
    if not files:
        return f"No plans yet in {plans_dir}."
    lines = [f"- {p.name}  [status: {_plan_status(p)}]" for p in files]
    return f"Plans in {plans_dir}:\n" + "\n".join(lines)


PLANS_TOOLS = [write_plan, list_plans]
