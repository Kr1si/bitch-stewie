"""LangChain tools for the orchestrator and its subagents.

All tools are sync (LangGraph runs them in a threadpool) and persist through
the sync engine, so they work regardless of the host event loop.
"""

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import select

from assistant.cc_bridge.brief import Brief
from assistant.cc_bridge.worker import get_worker
from assistant.memory.models import Decision, Preference, Project
from assistant.memory.sync_db import get_sync_session_factory
from assistant.orchestrator.context import current_project


@tool
def register_project(name: str, description: str = "", repo_path: str = "") -> str:
    """Register a new project in the workspace registry (or report if it exists)."""
    with get_sync_session_factory()() as s:
        if s.execute(select(Project).where(Project.name == name)).scalar_one_or_none():
            return f"Project '{name}' already exists."
        s.add(Project(name=name, description=description, repo_path=repo_path or None))
        s.commit()
    return f"Project '{name}' registered."


@tool
def list_projects() -> str:
    """List all projects in the workspace registry."""
    with get_sync_session_factory()() as s:
        rows = s.execute(select(Project)).scalars().all()
    if not rows:
        return "No projects registered."
    return "\n".join(f"- {p.name} [{p.status}] repo={p.repo_path or '-'} :: {p.description}"
                     for p in rows)


@tool
def record_decision(title: str, decision: str, context: str = "",
                    consequences: str = "", *, config: RunnableConfig) -> str:
    """Record an ADR-style architecture decision for the current project."""
    proj = current_project(config)
    with get_sync_session_factory()() as s:
        s.add(Decision(project_id=proj.id, title=title, decision=decision,
                       context=context, consequences=consequences))
        s.commit()
    return f"Decision '{title}' recorded for {proj.name}."


@tool
def list_decisions(*, config: RunnableConfig) -> str:
    """List recorded decisions for the current project."""
    proj = current_project(config)
    with get_sync_session_factory()() as s:
        rows = s.execute(select(Decision).where(Decision.project_id == proj.id)
                         .order_by(Decision.created_at)).scalars().all()
    if not rows:
        return f"No decisions recorded for {proj.name}."
    return "\n".join(f"- [{d.status}] {d.title}: {d.decision[:200]}" for d in rows)


@tool
def set_preference(key: str, value: str) -> str:
    """Store or update a user preference/convention (e.g. doc style, review strictness)."""
    with get_sync_session_factory()() as s:
        row = s.execute(select(Preference).where(Preference.key == key)).scalar_one_or_none()
        if row:
            row.value = value
        else:
            s.add(Preference(key=key, value=value))
        s.commit()
    return f"Preference '{key}' saved."


@tool
def list_preferences() -> str:
    """List stored user preferences and conventions."""
    with get_sync_session_factory()() as s:
        rows = s.execute(select(Preference)).scalars().all()
    return "\n".join(f"- {p.key}: {p.value}" for p in rows) or "No preferences stored."


@tool
def delegate_coding_task(goal: str, constraints: list[str] | None = None,
                         acceptance_criteria: list[str] | None = None,
                         examples: list[str] | None = None,
                         parallel: bool = False, *, config: RunnableConfig) -> str:
    """Delegate a coding task to a Claude Code instance working in the project's repository.

    The instance implements on a feature branch, self-reviews with /code-review,
    and returns a structured result. Use parallel=True only for tasks that split
    into independent parts (enables an agent team). This is a long-running call.

    Pass absolute file paths in 'examples' to give the instance reference files
    (e.g. example diagrams/docs) to read on the host for style/layout.
    """
    proj = current_project(config)
    repo_path = proj.repo_path
    if not repo_path:
        return f"Project '{proj.name}' has no registered repo path."
    brief = Brief(goal=goal, repo_path=repo_path, constraints=constraints or [],
                  acceptance_criteria=acceptance_criteria or [],
                  examples=examples or [],
                  skills=["delegate-coding-task"])
    outcome = get_worker().delegate(brief, agent_teams=parallel)
    r = outcome.result
    return (
        f"Delegation {outcome.status.value} (run {outcome.run_id}, "
        f"{outcome.review_iterations} review iteration(s)).\n"
        f"branch: {r.get('branch', '?')}\ncommits: {r.get('commits', [])}\n"
        f"tests: {r.get('tests', '?')}\nreview: {r.get('review_verdict', '?')}\n"
        f"summary: {r.get('summary', r.get('error', ''))}"
    )


REGISTRY_TOOLS = [register_project, list_projects, record_decision, list_decisions,
                  set_preference, list_preferences]
DELEGATION_TOOLS = [delegate_coding_task]
