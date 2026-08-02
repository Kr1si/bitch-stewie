"""Procrastinate job queue (Postgres-native) for long-running work with retries.

Goals are executed by kind via ``_KIND_HANDLERS``. The periodic ``daily_report``
task does NOT run goals inline — it defers one ``run_one_goal`` sub-job per
active goal so Procrastinate can run them concurrently (cap the parallelism
with the worker ``--concurrency`` flag; recommended 5). Adding a new goal kind
means registering a handler here; the scheduler picks it up automatically.
"""

from datetime import UTC

from procrastinate import App, PsycopgConnector

from assistant.application.services.memory_service import Goal
from assistant.shared.config import get_settings


def _connector() -> PsycopgConnector:
    return PsycopgConnector(conninfo=get_settings().database_url)


app = App(connector=_connector())


@app.task(name="delegate_brief", retry=1, queue="delegation")
def delegate_brief(goal: str, repo_path: str, constraints: list[str] | None = None,
                   acceptance_criteria: list[str] | None = None,
                   parallel: bool = False) -> dict:
    """Run a Claude Code delegation as a background job (worker process)."""
    from assistant.infrastructure.cc_bridge.brief import Brief
    from assistant.infrastructure.cc_bridge.worker import get_worker

    brief = Brief(goal=goal, repo_path=repo_path, constraints=constraints or [],
                  acceptance_criteria=acceptance_criteria or [])
    outcome = get_worker().delegate(brief, agent_teams=parallel)
    return {"run_id": str(outcome.run_id), "status": outcome.status.value,
            "result": outcome.result}


# --------------------------------------------------------------------------- #
# Goal execution — dispatch by kind
# --------------------------------------------------------------------------- #

async def _run_research_goal(goal: "Goal") -> dict:
    """Research: fan-out conductor -> researcher subagents -> composer -> KB."""
    from assistant.application.orchestrator.daily_report import run_daily_report
    return run_daily_report(goal)


async def _run_coding_goal(goal: "Goal") -> dict:
    """Coding: delegate the configured task to Claude Code on a branch.

    Stub — dispatches a CC delegation from the goal's config (repo + brief).
    Milestone-gated; the orchestrator's delegate path does the real work.
    """
    from assistant.infrastructure.cc_bridge.brief import Brief
    from assistant.infrastructure.cc_bridge.worker import get_worker

    cfg = goal.config or {}
    repo = cfg.get("repo_path", "")
    if not repo:
        return {"goal_id": str(goal.id), "status": "failed",
                "error": "coding goal has no repo_path in config"}
    brief = Brief(
        goal=cfg.get("goal", goal.title),
        repo_path=repo,
        constraints=cfg.get("constraints", []),
        acceptance_criteria=cfg.get("acceptance_criteria", []),
    )
    outcome = get_worker().delegate(brief)
    return {"goal_id": str(goal.id), "run_id": str(outcome.run_id),
            "status": outcome.status.value, "result": outcome.result}


async def _run_testing_goal(goal: "Goal") -> dict:
    """Testing: run the configured test command via Claude Code and report.

    Stub — opens a CC session that runs the goal's test command + scope.
    """
    from assistant.infrastructure.cc_bridge.worker import get_worker

    cfg = goal.config or {}
    command = cfg.get("command", "")
    if not command:
        return {"goal_id": str(goal.id), "status": "failed",
                "error": "testing goal has no command in config"}
    prompt = (
        f"Run the test suite for this project and report pass/fail.\n"
        f"command: {command}\nscope: {cfg.get('scope', '.')}\n"
        f"green criteria: {cfg.get('green_criteria', 'all tests pass')}\n"
        "Run the command, report the result, and whether it meets the green criteria."
    )
    repo = cfg.get("repo_path", ".")
    report = get_worker().run_prompt(prompt, cwd=repo, timeout=1800)
    return {"goal_id": str(goal.id), "status": "succeeded", "report": report[:2000]}


# Register a handler here to add a new goal kind.
_KIND_HANDLERS: dict[str, callable] = {
    "research": _run_research_goal,
    "coding": _run_coding_goal,
    "testing": _run_testing_goal,
}


def _dispatch_goal(goal: "Goal") -> dict:
    """Route a goal to its kind's handler, or report an unhandled kind."""
    kind_key = goal.kind.value if hasattr(goal.kind, "value") else goal.kind
    handler = _KIND_HANDLERS.get(kind_key)
    if handler is None:
        return {"goal_id": str(goal.id), "status": "failed",
                "error": f"no handler for goal kind '{goal.kind}'"}
    import asyncio
    return asyncio.run(handler(goal))


@app.task(name="run_one_goal", retry=1, queue="ingestion")
def run_one_goal(goal_id: str) -> dict:
    """Load one goal by id and run it through its kind's handler.

    Deferred by ``daily_report`` so goals run concurrently across worker
    threads. Updates last_run_at on success.
    """
    import asyncio
    from datetime import datetime
    from uuid import UUID

    from assistant.application.services.goal_service import get_goal
    from assistant.application.services.memory_service import get_sync_session_factory

    goal = asyncio.run(get_goal(UUID(goal_id)))
    if goal is None:
        return {"goal_id": goal_id, "status": "failed", "error": "goal not found"}

    result = _dispatch_goal(goal)

    if result.get("status") not in ("failed",):
        from assistant.application.services.memory_service import Goal as _Goal
        with get_sync_session_factory()() as s:
            g = s.get(_Goal, UUID(goal_id))
            if g is not None:
                g.last_run_at = datetime.now(UTC)
                s.commit()
    return result


@app.periodic(cron="0 7 * * *")
@app.task(name="daily_report", queue="ingestion")
def daily_report(timestamp: int) -> dict:
    """Daily: schedule every active goal for execution.

    Defers one ``run_one_goal`` sub-job per active goal (all kinds) so they
    run concurrently up to the worker concurrency cap, instead of blocking the
    periodic task sequentially.
    """
    from sqlalchemy import select

    from assistant.application.services.memory_service import (
        Goal,
        GoalStatus,
        get_sync_session_factory,
    )

    with get_sync_session_factory()() as s:
        goals = s.execute(
            select(Goal).where(Goal.status == GoalStatus.active)
        ).scalars().all()
        for goal in goals:
            run_one_goal.defer(goal_id=str(goal.id))
    return {"deferred": len(goals)}


@app.task(name="ingest_path_job", retry=2, queue="ingestion")
def ingest_path_job(path: str, project: str | None = None) -> dict:
    from assistant.infrastructure.rag.ingest import ingest_path

    return ingest_path(path, project=project)


@app.periodic(cron="0 3 * * *")
@app.task(name="summarize_conversations", queue="ingestion")
def summarize_conversations(timestamp: int) -> dict:
    """Nightly: ingest yesterday's conversation messages into the KB."""
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from assistant.infrastructure.memory.models import Message, Session
    from assistant.infrastructure.memory.sync_db import get_sync_session_factory
    from assistant.infrastructure.rag.ingest import ingest_text

    cutoff = datetime.now(UTC) - timedelta(days=1)
    total = 0
    with get_sync_session_factory()() as s:
        sessions = s.execute(select(Session)).scalars().all()
        for sess in sessions:
            msgs = s.execute(
                select(Message).where(Message.session_id == sess.id,
                                      Message.created_at >= cutoff)
                .order_by(Message.created_at)
            ).scalars().all()
            if not msgs:
                continue
            transcript = "\n".join(f"{m.role}: {m.content}" for m in msgs)
            total += ingest_text(
                transcript,
                source=f"conversation:{sess.thread_id}:{cutoff:%Y%m%d}",
                kind="conversation",
            )
    return {"chunks": total}
