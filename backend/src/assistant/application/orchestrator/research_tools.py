"""Researcher tools: local knowledge base + native /deep-research via Claude Code."""

import logging
import shutil
import tempfile
from pathlib import Path

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from assistant.application.orchestrator.context import current_project
from assistant.infrastructure.cc_bridge.worker import get_worker
from assistant.infrastructure.rag.ingest import ingest_text
from assistant.infrastructure.rag.store import hybrid_search

logger = logging.getLogger(__name__)


@tool
def search_knowledge(query: str, *, config: RunnableConfig) -> str:
    """Search the ingested knowledge base (vault docs, standards, past research)
    scoped to the current project."""
    proj = current_project(config)
    hits = hybrid_search(query, project=proj.name, limit=5)
    if not hits:
        return "No results in the knowledge base for that query."
    return "\n\n".join(
        f"[{h['kind']}] {h['source']} (score {h['score']:.3f})\n{h['text'][:800]}" for h in hits
    )


_DEEP_RESEARCH_SKILL = "deep-research-review"


def _stage_deep_research_skill(workdir: str) -> list[str]:
    """Stage the global deep-research-review skill into the scratch workdir.

    The SDK's ``skills=`` takes NAMES resolved from ``setting_sources`` — with
    setting_sources=["project"] that means <cwd>/.claude/skills/. Staging the
    file there is what makes the name resolvable (same trick delegation uses for
    delegate-coding-task). Returns the staged name(s) to pass to run_prompt.
    """
    src = Path.home() / ".agents" / "skills" / _DEEP_RESEARCH_SKILL / "SKILL.md"
    if not src.is_file():
        logger.warning("deep-research-review skill not found at %s; "
                       "research will run without it", src)
        return []
    dest_dir = Path(workdir) / ".claude" / "skills" / _DEEP_RESEARCH_SKILL
    dest = dest_dir / "SKILL.md"
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        return [_DEEP_RESEARCH_SKILL]
    except OSError as exc:
        logger.warning("could not stage %s: %r", _DEEP_RESEARCH_SKILL, exc)
        return []


def run_deep_research(question: str, project: str = "") -> str:
    """Run deep web research via a headless Claude Code session.

    Synchronous and long-running (minutes): the CC worker blocks the calling
    thread, so callers on an event loop must dispatch this to a threadpool
    (e.g. ``asyncio.to_thread``). The resulting report is ingested into the
    knowledge base automatically so future questions can reuse it.

    The ``deep-research-review`` skill is staged into the scratch workdir so its
    research→verify→report plan is available to the session. The prompt then
    inlines that plan as a DIRECT instruction (NOT a ``/deep-research`` slash
    command — that slash command delegates to an async background workflow that
    does not exist headless, so the model would just describe the plan instead
    of executing it). Returns the full Markdown report (empty string if CC
    produced nothing).
    """
    workdir = tempfile.mkdtemp(prefix="deep-research-")
    try:
        skill_names = _stage_deep_research_skill(workdir)
        prompt = (
            f"Research the following question and produce a concise, well-cited "
            f"Markdown report. Execute the research yourself using WebSearch and "
            f"WebFetch — do NOT delegate to any background workflow.\n\n"
            f"Question: {question}\n\n"
            f"Steps:\n"
            f"1. Break the question into 3-5 independent sub-questions and research "
            f"each in parallel with WebSearch/WebFetch. Collect findings with a "
            f"source URL per claim.\n"
            f"2. Verify: for each cited claim, attempt to refute it — does the "
            f"source actually say this? Drop or flag claims that don't survive.\n"
            f"3. Write the cited report: headline findings, detail per "
            f"sub-question, then a sources list.\n"
            f"Do not ask clarifying questions — make reasonable assumptions and "
            f"state them. Return the completed report as your final text."
        )
        report = get_worker().run_prompt(prompt, cwd=workdir,
                                          skill_names=skill_names)
        if report.strip():
            ingest_text(report, source=f"deep-research:{question[:80]}",
                        project=project or None, kind="research")
        return report
    finally:
        # the CC session is done once run_prompt returns; free the scratch dir
        shutil.rmtree(workdir, ignore_errors=True)


@tool
def deep_research(question: str, *, config: RunnableConfig) -> str:
    """Run deep web research with citations via Claude Code's native /deep-research skill,
    scoped to the current project.

    Long-running (minutes). The resulting report is ingested into the knowledge
    base automatically so future questions can reuse it.
    """
    proj = current_project(config)
    report = run_deep_research(question, project=proj.name)
    return report[:6000] if report.strip() else "Research returned no content."


RESEARCH_TOOLS = [search_knowledge, deep_research]
