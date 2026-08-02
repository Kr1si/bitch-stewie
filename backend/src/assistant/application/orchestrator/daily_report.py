"""Daily AI-intelligence report pipeline: conductor -> researchers -> composer.

Spawned by the ``daily_report`` Procrastinate periodic task for each active
``research`` goal (see ``infrastructure/jobs/queue.py``). Two Claude Code
one-shots run back-to-back on the shared CCWorker:

  1. conductor -- fans out to one read-only ``researcher`` subagent per category
                  (each runs the inlined deep-research-review workflow and
                  returns a cited report as text); the conductor persists each
                  report to reports/<date>/findings/<category>.md.
  2. composer  -- reads the findings, writes the daily digest + appends modular
                  market-ideas to the living wiki.

Both outputs are ingested into the knowledge base. The whole pipeline blocks
the calling thread for tens of minutes, so it only ever runs inside the
Procrastinate worker process -- never on the FastAPI event loop.

The ``deep-research-review`` skill normally lives in user-global
``~/.claude/skills/`` and is invisible to sessions running with
``setting_sources=["project"]``, so its workflow is inlined here and adapted:
researcher subagents are read-only, so they RETURN their cited report and the
conductor writes it to disk.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from assistant.application.services.memory_service import Goal
from assistant.infrastructure.cc_bridge.worker import get_worker
from assistant.infrastructure.rag.ingest import ingest_text
from assistant.shared.config import get_settings

# --------------------------------------------------------------------------- #
# Inlined deep-research-review workflow (adapted: subagents return text, the
# conductor persists). Kept self-contained so a fresh CC session can run it.
# --------------------------------------------------------------------------- #
_RESEARCH_WORKFLOW = """\
Deep research workflow (execute per category):

1. Fan-out: break the category topic into 3-5 independent sub-questions and
   research each in parallel using WebSearch / WebFetch. Collect raw findings
   with a source URL per claim. Do not synthesize yet.
2. Verify: for each cited claim, attempt to refute it — does the source actually
   say this? Is there a stronger or contradicting source? Drop or flag-as-uncertain
   any claim that does not survive. (Single verification pass.)
3. Report: produce a cited Markdown report: headline findings, then detail per
   sub-questions, then a sources list. Return this report as your final text.
   Do NOT attempt to write files — the conductor persists your output.
"""


def _today_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _build_conductor_prompt(date: str, root: Path, categories: list[dict]) -> str:
    lines = [f"# Daily report conductor — {date}", "",
             f"Reports root: {root}",
             f"Create the directory {root / date / 'findings'} (and parents).",
             "",
             "For EACH category below, spawn a `researcher` subagent (registered",
             "in this session) to do deep research following this workflow:",
             _RESEARCH_WORKFLOW, "",
             "The researcher subagent CANNOT write files (read-only tools) — it",
             "returns its cited report as text. Collect each researcher's returned",
             f"report and write it to {root / date / 'findings' / '<category-id>.md'}.",
             "Use the category's `id` as the filename slug.",
             "",
             "Research every category. Categories:",
             "```yaml"]
    for c in categories:
        lines.append(f"- id: {c['id']}")
        lines.append(f"  name: {c['name']}")
        if c.get("sources"):
            lines.append(f"  sources: {c['sources']}")
        if c.get("themes"):
            lines.append(f"  themes: {c['themes']}")
        if c.get("notes"):
            lines.append(f"  notes: {c['notes']}")
    lines.extend(["```", "",
                  "After all findings files are written, reply with a one-line",
                  "summary of what was researched."])
    return "\n".join(lines)


def _build_composer_prompt(date: str, root: Path) -> str:
    return (
        f"# Daily report composer — {date}\n\n"
        f"Read ALL findings in {root / date / 'findings'} and synthesize them.\n\n"
        f"1. Write a daily digest to {root / date / 'digest.md'}: headline findings\n"
        f"   per category, then sources. Well-cited Markdown.\n\n"
        f"2. Update the market-ideas wiki (modular, single-responsibility, monetizable):\n"
        f"   - Read the living index {root / 'market-ideas.md'} if it exists.\n"
        f"   - For each new market opportunity spotted in today's findings, create a\n"
        f"     module {root / 'ideas' / '<slug>.md'} with YAML frontmatter: name,\n"
        f"     monetization_vector, scope, features[], source, confidence, status,\n"
        f"     related[]. Each module = one single-responsibility part you can monetize.\n"
        f"   - Update the living index to link new modules and cross-link related ones.\n\n"
        f"Reply with a one-line summary of what you wrote."
    )


def _project_name_for(goal: Goal) -> str | None:
    """Resolve the KB collection name for a goal's project, if any."""
    if goal.project_id is None:
        return None
    from assistant.application.services.memory_service import (
        Project,
        get_sync_session_factory,
    )
    with get_sync_session_factory()() as s:
        project = s.get(Project, goal.project_id)
        return project.name if project else None


async def run_research_pipeline(goal: Goal) -> dict:
    """Run conductor -> composer for one research goal and ingest the outputs.

    Long-running (tens of minutes): the CC worker blocks its calling thread, so
    the blocking ``run_prompt`` calls are dispatched to a threadpool via
    ``asyncio.to_thread`` — callers (the test, the queue job) can ``await`` this
    without stalling the event loop. Raises on stage failure so the job can retry.
    """
    settings = get_settings()
    root = Path(settings.reports_path)
    date = _today_str()
    categories = goal.config.get("categories", [])
    output = goal.config.get("output", {})
    project = _project_name_for(goal)

    # Allow goal config to override the default path layout (paths are relative
    # to the reports root; "{date}" is substituted).
    def rel(template: str) -> Path:
        return root / template.format(date=date)

    digest_file = rel(output.get("digest_file", "{date}/digest.md"))
    ideas_index = rel(output.get("market_ideas_index", "market-ideas.md"))

    # --- stage 1: conductor -------------------------------------------------
    conductor_prompt = _build_conductor_prompt(date, root, categories)
    await asyncio.to_thread(get_worker().run_prompt, conductor_prompt, str(root), 3600)

    # --- stage 2: composer --------------------------------------------------
    composer_prompt = _build_composer_prompt(date, root)
    await asyncio.to_thread(get_worker().run_prompt, composer_prompt, str(root), 1800)

    # --- stage 3: ingest ----------------------------------------------------
    ingested = {"digest_chunks": 0, "market_ideas_chunks": 0}
    if digest_file.is_file():
        ingested["digest_chunks"] = ingest_text(
            digest_file.read_text(encoding="utf-8"),
            source=f"daily-report:{date}",
            project=project,
            kind="daily-report",
        )
    if ideas_index.is_file():
        ingested["market_ideas_chunks"] = ingest_text(
            ideas_index.read_text(encoding="utf-8"),
            source="market-ideas:living-index",
            project=project,
            kind="market-ideas",
        )

    return {"date": date, "categories": len(categories), "ingested": ingested}


# Module-level alias kept stable for the scheduler import.
run_daily_report = run_research_pipeline
