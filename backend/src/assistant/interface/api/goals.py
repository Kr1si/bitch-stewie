"""Goals CRUD + goal-creation interview stream.

A Goal is a first-class, scheduleable objective (research / coding / testing).
The scheduler reads active goals and runs each on its cadence; the Goals API
lets the UI list, create, pause/resume, and delete them.

This router also owns the **dedicated goal-creation interview endpoint**
(POST /api/goals/chat/stream). It is fully separate from /api/chat — chat stays
chat, goal-creation is its own flow that runs the goal_creator_graph.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from assistant.application.orchestrator.goal_creator_graph import build_goal_creator_graph
from assistant.application.services.goal_service import (
    Goal,
    create_goal_entity,
    delete_goal,
    get_goal,
    list_goals,
    serialize,
)
from assistant.shared.config import get_settings

router = APIRouter(prefix="/api/goals")


class GoalIn(BaseModel):
    project_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1)
    description: str = ""
    kind: str = "research"
    status: str = "active"
    cadence: str = Field("0 7 * * *", description="Cron expression (UTC).")
    config: dict = Field(default_factory=dict)


class GoalPatch(BaseModel):
    status: str | None = None
    cadence: str | None = None
    description: str | None = None
    config: dict | None = None


class GoalChatIn(BaseModel):
    message: str
    thread_id: str | None = None
    project_id: uuid.UUID | None = None


# --- CRUD ---------------------------------------------------------------------

@router.get("")
async def list_goals_route() -> list[dict[str, Any]]:
    return [serialize(g) for g in await list_goals()]


@router.post("", status_code=201)
async def create_goal_route(body: GoalIn) -> dict[str, Any]:
    try:
        goal = await create_goal_entity(
            title=body.title,
            kind=body.kind,
            cadence=body.cadence,
            description=body.description,
            status=body.status,
            project_id=body.project_id,
            config=body.config,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return serialize(goal)


@router.patch("/{goal_id}")
async def update_goal_route(goal_id: uuid.UUID, body: GoalPatch) -> dict[str, Any]:
    goal = await _get_or_404(goal_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    from assistant.application.services.memory_service import get_session_factory
    async with get_session_factory()() as s:
        await s.flush()
        await s.refresh(goal)
        return serialize(goal)


@router.delete("/{goal_id}", status_code=204)
async def delete_goal_route(goal_id: uuid.UUID) -> None:
    ok = await delete_goal(goal_id)
    if not ok:
        raise HTTPException(404, "goal not found")


# --- goal-creation interview stream (dedicated endpoint, NOT /api/chat) ---------

def _chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


async def _stream_goal_chat(
    graph: Any, state: dict[str, Any], config: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    """Stream the goal-creator graph: token -> done/error. Mirrors chat.py."""
    full_text: list[str] = []
    try:
        async for chunk, _metadata in graph.astream(state, config, stream_mode="messages"):
            if getattr(chunk, "type", "") in ("AIMessageChunk", "ai"):
                text = _chunk_text(chunk)
                if text:
                    full_text.append(text)
                    yield {"event": "token", "data": json.dumps({"text": text})}
    except Exception as exc:
        yield {"event": "error", "data": json.dumps({"error": str(exc) or type(exc).__name__})}
        return
    yield {"event": "done", "data": json.dumps({"reply": "".join(full_text)})}


@router.post("/chat/stream")
async def goal_chat_stream(body: GoalChatIn) -> EventSourceResponse:
    """Run one turn of the goal-creator interview.

    The FE starts a thread_id, sends the user's message, and streams the agent's
    reply (questions, or a confirmation after persist). To continue the interview
    the FE appends the user's answer to the message list and POSTs again on the
    same thread_id; the checkpointer restores GoalState with accumulated messages.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    from assistant.shared.config import get_settings as _gs

    saver = AsyncPostgresSaver.from_conn_string(_gs().database_url)
    async with saver as checkpointer:
        await checkpointer.setup()
        graph = build_goal_creator_graph(checkpointer=checkpointer)

        thread_id = body.thread_id or f"goal-{uuid.uuid4().hex[:12]}"
        config = {"configurable": {"thread_id": thread_id,
                                   "project_id": str(body.project_id) if body.project_id else None}}

        # Rebuild state from the checkpointer so prior turns survive.
        existing = await graph.aget_state(config)
        if existing and existing.values:
            prior_messages = list(existing.values.get("messages", []))
            prior_goal = existing.values.get("goal", {})
            prior_status = existing.values.get("status", "interviewing")
            prior_kind = existing.values.get("kind")
        else:
            prior_messages, prior_goal, prior_status, prior_kind = [], {}, "interviewing", None

        user_msg = {"role": "user", "content": body.message}
        state = {"messages": [*prior_messages, user_msg], "goal": prior_goal,
                 "status": prior_status, "kind": prior_kind}

        async def event_gen() -> AsyncIterator[dict[str, Any]]:
            async for ev in _stream_goal_chat(graph, state, config):
                yield ev

        return EventSourceResponse(event_gen())


# --- report reading (raw markdown files the pipeline wrote) --------------------

def _reports_root() -> Path:
    return Path(get_settings().reports_path)


@router.get("/reports")
async def list_reports() -> list[str]:
    """List dated report dirs (YYYY-MM-DD), newest first."""
    root = _reports_root()
    if not root.is_dir():
        return []
    dirs = [d.name for d in root.iterdir() if d.is_dir() and len(d.name) == 10]
    return sorted(dirs, reverse=True)


@router.get("/reports/{date}")
async def read_report(date: str) -> dict[str, Any]:
    """Return the digest + market-ideas wiki for a dated report."""
    root = _reports_root() / date
    if not root.is_dir():
        raise HTTPException(404, "report not found")

    def read(name: str) -> str:
        p = root / name
        return p.read_text(encoding="utf-8") if p.is_file() else ""

    findings_dir = root / "findings"
    findings: list[dict[str, str]] = []
    if findings_dir.is_dir():
        for f in sorted(findings_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                findings.append({"category": f.stem, "markdown": f.read_text(encoding="utf-8")})

    return {
        "date": date,
        "digest": read("digest.md"),
        "findings": findings,
        "market_ideas": read("../market-ideas.md"),
    }


async def _get_or_404(goal_id: uuid.UUID) -> Goal:
    goal = await get_goal(goal_id)
    if goal is None:
        raise HTTPException(404, "goal not found")
    return goal
