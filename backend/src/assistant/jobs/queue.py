"""Procrastinate job queue (Postgres-native) for long-running work with retries."""

from procrastinate import App, PsycopgConnector

from assistant.config import get_settings


def _connector() -> PsycopgConnector:
    return PsycopgConnector(conninfo=get_settings().database_url)


app = App(connector=_connector())


@app.task(name="delegate_brief", retry=1, queue="delegation")
def delegate_brief(goal: str, repo_path: str, constraints: list[str] | None = None,
                   acceptance_criteria: list[str] | None = None,
                   parallel: bool = False) -> dict:
    """Run a Claude Code delegation as a background job (worker process)."""
    from assistant.cc_bridge.brief import Brief
    from assistant.cc_bridge.worker import get_worker

    brief = Brief(goal=goal, repo_path=repo_path, constraints=constraints or [],
                  acceptance_criteria=acceptance_criteria or [])
    outcome = get_worker().delegate(brief, agent_teams=parallel)
    return {"run_id": str(outcome.run_id), "status": outcome.status.value,
            "result": outcome.result}


@app.task(name="ingest_path_job", retry=2, queue="ingestion")
def ingest_path_job(path: str, project: str | None = None) -> dict:
    from assistant.rag.ingest import ingest_path

    return ingest_path(path, project=project)


@app.periodic(cron="0 3 * * *")
@app.task(name="summarize_conversations", queue="ingestion")
def summarize_conversations(timestamp: int) -> dict:
    """Nightly: ingest yesterday's conversation messages into the KB."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from assistant.memory.models import Message, Session
    from assistant.memory.sync_db import get_sync_session_factory
    from assistant.rag.ingest import ingest_text

    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
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
            total += ingest_text(transcript, source=f"conversation:{sess.thread_id}:{cutoff:%Y%m%d}",
                                 kind="conversation")
    return {"chunks": total}
