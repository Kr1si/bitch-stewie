"""Plan endpoints: the planning agent's chat transport, plus handoff to the orchestrator."""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from assistant.api.chat import _ensure_session, _extract_text, _interrupt_payload, _persist, _stream
from assistant.memory.db import get_session_factory
from assistant.memory.models import Message, Project, Session

router = APIRouter(prefix="/api/plan")


class PlanChatIn(BaseModel):
    message: str
    thread_id: str | None = None


class HandoffIn(BaseModel):
    thread_id: str
    project_id: uuid.UUID


def _plan_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()[:80] or fallback
    return fallback


@router.post("/stream")
async def plan_stream(body: PlanChatIn, request: Request):
    agent = request.app.state.planner
    thread_id, session_id = await _ensure_session(body.thread_id, body.message, channel="plan")
    await _persist(session_id, "user", body.message)
    config = {"configurable": {"thread_id": thread_id}}
    invoke_input = {"messages": [{"role": "user", "content": body.message}]}

    async def event_gen():
        final_text = ""
        interrupted = False
        try:
            async for ev in _stream(agent, invoke_input, config):
                if ev["event"] == "token":
                    final_text += json.loads(ev["data"])["text"]
                elif ev["event"] == "interrupt":
                    interrupted = True
                yield ev
        finally:
            if not interrupted and final_text:
                await _persist(session_id, "assistant", final_text)

    return EventSourceResponse(event_gen())


@router.get("/sessions")
async def list_sessions(project_id: uuid.UUID | None = None, limit: int = 30):
    async with get_session_factory()() as s:
        q = (select(Session).where(Session.channel == "plan")
             .order_by(Session.updated_at.desc()).limit(limit))
        if project_id:
            q = q.where(Session.project_id == project_id)
        rows = (await s.execute(q)).scalars().all()
    return [{"id": str(r.id), "thread_id": r.thread_id, "title": r.title,
             "channel": r.channel, "project_id": str(r.project_id) if r.project_id else None,
             "created_at": r.created_at.isoformat(),
             "updated_at": r.updated_at.isoformat()} for r in rows]


@router.get("/sessions/{session_id}/messages")
async def session_messages(session_id: uuid.UUID, limit: int = 200):
    async with get_session_factory()() as s:
        rows = (await s.execute(
            select(Message).where(Message.session_id == session_id)
            .order_by(Message.created_at).limit(limit)
        )).scalars().all()
    return [{"id": str(m.id), "role": m.role, "content": m.content,
             "meta": m.meta, "created_at": m.created_at.isoformat()} for m in rows]


@router.post("/handoff")
async def handoff(body: HandoffIn, request: Request):
    """Take the newest plan file for a project and hand it to the orchestrator
    as a new session, so the user can find it in the Chat page's thread list.
    """
    async with get_session_factory()() as s:
        project = (await s.execute(
            select(Project).where(Project.id == body.project_id))).scalar_one_or_none()
    if project is None or not project.repo_path:
        raise HTTPException(404, "Project not found or has no registered repo_path.")

    plans_dir = Path(project.repo_path) / "plans"
    if not plans_dir.is_dir():
        raise HTTPException(404, f"No plans/ folder in {project.repo_path}.")
    files = sorted(plans_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise HTTPException(404, f"No plan files found in {plans_dir}.")
    plan_path = files[0]
    plan_content = plan_path.read_text(encoding="utf-8")

    title = _plan_title(plan_content, plan_path.stem)
    orch_thread_id = f"web-{uuid.uuid4().hex[:12]}"
    orch_thread_id, orch_session_id = await _ensure_session(orch_thread_id, title, channel="web")

    initial_message = f"Implement the following plan:\n\n{plan_content}"
    await _persist(orch_session_id, "user", initial_message)

    agent = request.app.state.orchestrator
    config = {"configurable": {"thread_id": orch_thread_id}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": initial_message}]}, config,
    )
    interrupt = _interrupt_payload(result)
    reply = _extract_text(result)
    if interrupt is None and reply:
        await _persist(orch_session_id, "assistant", reply)

    return {
        "orchestrator_thread_id": orch_thread_id,
        "orchestrator_session_id": str(orch_session_id),
        "reply": reply,
        "interrupt": interrupt,
    }
