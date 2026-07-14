"""Chat endpoints: one orchestrator, thread-scoped conversations, HITL gates over HTTP."""

import json
import uuid

from fastapi import APIRouter, Request
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from assistant.memory.db import get_session_factory
from assistant.memory.models import Approval, ApprovalStatus, Message, Session

router = APIRouter(prefix="/api/chat")


class ChatIn(BaseModel):
    message: str
    project_id: uuid.UUID
    thread_id: str | None = None


class ResumeIn(BaseModel):
    thread_id: str
    approved: bool
    note: str = ""


def _extract_text(result: dict) -> str:
    for message in reversed(result.get("messages", [])):
        content = getattr(message, "content", None)
        if getattr(message, "type", "") == "ai" and content:
            if isinstance(content, list):
                return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
            return str(content)
    return ""


def _interrupt_payload(result: dict):
    if "__interrupt__" not in result:
        return None
    value = result["__interrupt__"][0].value
    return {"requests": value if isinstance(value, list) else [value]}


async def _ensure_session(
    thread_id: str | None, title: str, project_id: uuid.UUID | None = None, channel: str = "web"
) -> tuple[str, uuid.UUID, uuid.UUID | None]:
    async with get_session_factory()() as s:
        row = None
        if thread_id:
            row = (await s.execute(
                select(Session).where(Session.thread_id == thread_id))).scalar_one_or_none()
        if row is None:
            row = Session(thread_id=thread_id or f"{channel}-{uuid.uuid4().hex[:12]}",
                          title=title[:80], channel=channel, project_id=project_id)
            s.add(row)
            await s.commit()
        return row.thread_id, row.id, row.project_id


async def _persist(session_id: uuid.UUID, role: str, content: str) -> None:
    async with get_session_factory()() as s:
        s.add(Message(session_id=session_id, role=role, content=content))
        await s.commit()


def _respond(result: dict, thread_id: str) -> dict:
    interrupt = _interrupt_payload(result)
    return {"thread_id": thread_id, "reply": _extract_text(result),
            "interrupt": interrupt, "pending": interrupt is not None}


def _chunk_text(chunk) -> str:
    """Pull incremental text from an astream(message) chunk."""
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def _tool_calls(chunk) -> list[dict]:
    tc = getattr(chunk, "tool_call_chunks", None) or getattr(chunk, "tool_calls", None)
    if not tc:
        return []
    out = []
    for c in tc:
        name = getattr(c, "name", None) or (c.get("name") if isinstance(c, dict) else None)
        if name:
            out.append({"name": name})
    return out


async def _stream(agent, invoke_input, config):
    """Yield SSE events: token, tool, then interrupt/done via aget_state.

    Streaming is best-effort over astream(stream_mode='messages'); the gate is
    detected from the post-stream state (robust to the deep-agent stream shape).
    """
    full_text = []
    async for chunk, metadata in agent.astream(invoke_input, config, stream_mode="messages"):
        # Only stream the top-level assistant tokens, not subagent tool messages.
        if getattr(chunk, "type", "") in ("AIMessageChunk", "ai"):
            text = _chunk_text(chunk)
            if text:
                full_text.append(text)
                yield {"event": "token", "data": json.dumps({"text": text})}
            calls = _tool_calls(chunk)
            if calls:
                yield {"event": "tool", "data": json.dumps({"calls": calls})}
    state = await agent.aget_state(config)
    interrupt = None
    if state and state.tasks:
        for task in state.tasks:
            if getattr(task, "interrupts", None):
                value = task.interrupts[0].value
                interrupt = {"requests": value if isinstance(value, list) else [value]}
                break
    yield {"event": "interrupt" if interrupt else "done",
           "data": json.dumps({"interrupt": interrupt, "reply": "".join(full_text)})}


@router.post("/stream")
async def chat_stream(body: ChatIn, request: Request):
    agent = request.app.state.orchestrator
    thread_id, session_id, project_id = await _ensure_session(
        body.thread_id, body.message, project_id=body.project_id)
    await _persist(session_id, "user", body.message)
    config = {"configurable": {"thread_id": thread_id, "project_id": str(project_id)}}
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


@router.post("/resume/stream")
async def resume_stream(body: ResumeIn, request: Request):
    agent = request.app.state.orchestrator
    thread_id, session_id, project_id = await _ensure_session(body.thread_id, "resume")
    decision = ({"type": "approve"} if body.approved
                else {"type": "reject", "message": body.note or "rejected"})
    async with get_session_factory()() as s:
        s.add(Approval(session_id=session_id, thread_id=thread_id, kind="delegate",
                       payload={"via": "web", "note": body.note},
                       status=ApprovalStatus.approved if body.approved else ApprovalStatus.rejected))
        await s.commit()
    config = {"configurable": {"thread_id": thread_id, "project_id": str(project_id)}}
    invoke_input = Command(resume={"decisions": [decision]})

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


@router.post("")
async def chat(body: ChatIn, request: Request):
    agent = request.app.state.orchestrator
    thread_id, session_id, project_id = await _ensure_session(
        body.thread_id, body.message, project_id=body.project_id)
    await _persist(session_id, "user", body.message)
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": body.message}]},
        {"configurable": {"thread_id": thread_id, "project_id": str(project_id)}},
    )
    if "__interrupt__" not in result:
        await _persist(session_id, "assistant", _extract_text(result))
    return _respond(result, thread_id)


@router.post("/resume")
async def resume(body: ResumeIn, request: Request):
    agent = request.app.state.orchestrator
    thread_id, session_id, project_id = await _ensure_session(body.thread_id, "resume")
    decision = ({"type": "approve"} if body.approved
                else {"type": "reject", "message": body.note or "rejected"})
    async with get_session_factory()() as s:
        s.add(Approval(session_id=session_id, thread_id=thread_id, kind="delegate",
                       payload={"via": "web", "note": body.note},
                       status=ApprovalStatus.approved if body.approved else ApprovalStatus.rejected))
        await s.commit()
    result = await agent.ainvoke(
        Command(resume={"decisions": [decision]}),
        {"configurable": {"thread_id": thread_id, "project_id": str(project_id)}},
    )
    if "__interrupt__" not in result:
        await _persist(session_id, "assistant", _extract_text(result))
    return _respond(result, thread_id)


@router.get("/sessions")
async def list_sessions(project_id: uuid.UUID | None = None, limit: int = 30):
    """List recent threads so the Chat/Diagrams UI can switch conversations."""
    async with get_session_factory()() as s:
        q = select(Session).order_by(Session.updated_at.desc()).limit(limit)
        if project_id:
            q = q.where(Session.project_id == project_id)
        rows = (await s.execute(q)).scalars().all()
    return [{"id": str(r.id), "thread_id": r.thread_id, "title": r.title,
             "channel": r.channel, "project_id": str(r.project_id) if r.project_id else None,
             "created_at": r.created_at.isoformat(),
             "updated_at": r.updated_at.isoformat()} for r in rows]


@router.get("/sessions/{session_id}/messages")
async def session_messages(session_id: uuid.UUID, limit: int = 200):
    """Prior turns for a thread so the UI can render history."""
    async with get_session_factory()() as s:
        rows = (await s.execute(
            select(Message).where(Message.session_id == session_id)
            .order_by(Message.created_at).limit(limit)
        )).scalars().all()
    return [{"id": str(m.id), "role": m.role, "content": m.content,
             "meta": m.meta, "created_at": m.created_at.isoformat()} for m in rows]
