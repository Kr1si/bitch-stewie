"""Researcher tools: local knowledge base + native /deep-research via Claude Code."""

import tempfile

from langchain_core.tools import tool

from assistant.cc_bridge.worker import get_worker
from assistant.rag.ingest import ingest_text
from assistant.rag.store import hybrid_search


@tool
def search_knowledge(query: str, project: str = "") -> str:
    """Search the ingested knowledge base (vault docs, standards, past research).

    Searches the project's collection if given, otherwise the global one.
    """
    hits = hybrid_search(query, project=project or None, limit=5)
    if not hits:
        return "No results in the knowledge base for that query."
    return "\n\n".join(
        f"[{h['kind']}] {h['source']} (score {h['score']:.3f})\n{h['text'][:800]}" for h in hits
    )


def run_deep_research(question: str, project: str = "") -> str:
    """Run deep web research via Claude Code's native /deep-research skill.

    Synchronous and long-running (minutes): the CC worker blocks the calling
    thread, so callers on an event loop must dispatch this to a threadpool
    (e.g. ``asyncio.to_thread``). The resulting report is ingested into the
    knowledge base automatically so future questions can reuse it.

    Returns the full Markdown report (empty string if CC produced nothing).
    """
    workdir = tempfile.mkdtemp(prefix="deep-research-")
    prompt = (
        f"/deep-research {question}\n\n"
        "Produce a concise, well-cited report in Markdown. Do not ask clarifying "
        "questions - make reasonable assumptions and state them."
    )
    report = get_worker().run_prompt(prompt, cwd=workdir)
    if report.strip():
        ingest_text(report, source=f"deep-research:{question[:80]}",
                    project=project or None, kind="research")
    return report


@tool
def deep_research(question: str, project: str = "") -> str:
    """Run deep web research with citations via Claude Code's native /deep-research skill.

    Long-running (minutes). The resulting report is ingested into the knowledge
    base automatically so future questions can reuse it.
    """
    report = run_deep_research(question, project=project)
    return report[:6000] if report.strip() else "Research returned no content."


RESEARCH_TOOLS = [search_knowledge, deep_research]
