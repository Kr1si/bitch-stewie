"""Run telemetry for Claude Code's statusLine / subagentStatusLine scripts.

CC's statusLine script reads a rich JSON object from stdin (session + workspace
state) and prints one line. This endpoint hands that script the per-run
telemetry we reconstruct from CCRun + CCRunEvent so an interactive CC session
can show live run status (model, elapsed, tool/task counts, review verdict)
without the UI's 10s poll.

SDK-driven runs already surface telemetry via the Runs page and the lifecycle
hooks (#4); this closes the loop for the interactive terminal.
"""

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from assistant.memory.db import get_session_factory
from assistant.memory.models import CCRun, CCRunEvent

router = APIRouter(prefix="/api/runs")


@router.get("/{run_id}/statusline")
async def run_statusline(run_id: uuid.UUID):
    async with get_session_factory()() as s:
        run = (await s.execute(select(CCRun).where(CCRun.id == run_id))).scalar_one_or_none()
        if run is None:
            raise HTTPException(404, "run not found")

        # event-type counts + last activity
        counts_rows = (
            await s.execute(
                select(CCRunEvent.event_type, func.count())
                .where(CCRunEvent.run_id == run_id)
                .group_by(CCRunEvent.event_type)
            )
        ).all()
        counts = {et: n for et, n in counts_rows}

        last = (
            await s.execute(
                select(CCRunEvent)
                .where(CCRunEvent.run_id == run_id)
                .order_by(CCRunEvent.created_at.desc())
                .limit(1)
            )
        ).scalars().first()

    elapsed_s: float = 0.0
    if run.updated_at and run.created_at:
        elapsed_s = (run.updated_at - run.created_at).total_seconds()

    return {
        "run_id": str(run.id),
        "status": run.status.value,
        "model": run.model,
        "repo_path": run.repo_path,
        "elapsed_s": round(elapsed_s, 1),
        "review_iterations": run.review_iterations,
        "review_verdict": (run.result or {}).get("review_verdict"),
        "events": {
            "pre_tool": counts.get("pre_tool", 0),
            "post_tool": counts.get("post_tool", 0),
            "subagent_start": counts.get("subagent_start", 0),
            "subagent_stop": counts.get("subagent_stop", 0),
            "text": counts.get("text", 0),
            "stop": counts.get("stop", 0),
        },
        "last_event_at": last.created_at.isoformat() if last else None,
        # CC statusLine also wants these; we don't track cost/rate_limits per-run
        # yet, so surface placeholders the script can render as "—".
        "cost": None,
        "rate_limits": None,
        "effort": None,
    }