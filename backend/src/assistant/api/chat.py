"""Chat endpoints: one orchestrator, thread-scoped conversations, HITL gates over HTTP."""

import uuid

from fastapi import APIRouter, Request
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy import select

from assistant.memory.db import get_session_factory
from assistant.memory.models import Approval, ApprovalStatus, Message, Session

router = APIRouter(prefix="/api/chat")


class ChatIn(BaseModel):
    message: str
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


async def _ensure_session(thread_id: str | None, title: str) -> tuple[str, uuid.UUID]:
    async with get_session_factory()() as s:
        row = None
        if thread_id:
            row = (await s.execute(
                select(Session).where(Session.thread_id == thread_id))).scalar_one_or_none()
        if row is None:
            row = Session(thread_id=thread_id or f"web-{uuid.uuid4().hex[:12]}",
                          title=title[:80], channel="web")
            s.add(row)
            await s.commit()
        return row.thread_id, row.id


async def _persist(session_id: uuid.UUID, role: str, content: str) -> None:
    async with get_session_factory()() as s:
        s.add(Message(session_id=session_id, role=role, content=content))
        await s.commit()


def _respond(result: dict, thread_id: str) -> dict:
    interrupt = _interrupt_payload(result)
    return {"thread_id": thread_id, "reply": _extract_text(result),
            "interrupt": interrupt, "pending": interrupt is not None}


@router.post("")
async def chat(body: ChatIn, request: Request):
    agent = request.app.state.orchestrator
    thread_id, session_id = await _ensure_session(body.thread_id, body.message)
    await _persist(session_id, "user", body.message)
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": body.message}]},
        {"configurable": {"thread_id": thread_id}},
    )
    if "__interrupt__" not in result:
        await _persist(session_id, "assistant", _extract_text(result))
    return _respond(result, thread_id)


@router.post("/resume")
async def resume(body: ResumeIn, request: Request):
    agent = request.app.state.orchestrator
    thread_id, session_id = await _ensure_session(body.thread_id, "resume")
    decision = ({"type": "approve"} if body.approved
                else {"type": "reject", "message": body.note or "rejected"})
    async with get_session_factory()() as s:
        s.add(Approval(session_id=session_id, thread_id=thread_id, kind="delegate",
                       payload={"via": "web", "note": body.note},
                       status=ApprovalStatus.approved if body.approved else ApprovalStatus.rejected))
        await s.commit()
    result = await agent.ainvoke(
        Command(resume={"decisions": [decision]}),
        {"configurable": {"thread_id": thread_id}},
    )
    if "__interrupt__" not in result:
        await _persist(session_id, "assistant", _extract_text(result))
    return _respond(result, thread_id)
