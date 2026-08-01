"""Procrastinate job queue (Postgres-native) for long-running work with retries."""

from datetime import UTC

from procrastinate import App, PsycopgConnector

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


@app.periodic(cron="0 7 * * *")
@app.task(name="daily_report", queue="ingestion")
def daily_report(timestamp: int) -> dict:
    """Daily: run the research pipeline for every active ``research`` goal.

    Long-running (tens of minutes) -- the conductor fans out to researcher
    subagents and the composer writes the digest + market-ideas wiki, then both
    are ingested into the KB. Delegates to ``run_daily_report`` so the prompt
    logic lives alongside its module.
    """
    from datetime import datetime

    from sqlalchemy import select

    from assistant.application.orchestrator.daily_report import run_daily_report
    from assistant.application.services.memory_service import (
        Goal,
        GoalKind,
        GoalStatus,
        get_sync_session_factory,
    )

    results: list[dict] = []
    with get_sync_session_factory()() as s:
        goals = s.execute(
            select(Goal).where(Goal.status == GoalStatus.active,
                               Goal.kind == GoalKind.research)
        ).scalars().all()
        for goal in goals:
            result = run_daily_report(goal)
            goal.last_run_at = datetime.now(UTC)
            results.append({"goal_id": str(goal.id), "title": goal.title, **result})
        s.commit()
    return {"ran": len(results), "results": results}


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
