"""Interactive chat with the orchestrator (Selector loop; delegation runs on the CC worker thread)."""

import uuid

import typer
from rich.console import Console
from sqlalchemy import select

console = Console()


def _extract_text(result: dict) -> str:
    for message in reversed(result.get("messages", [])):
        content = getattr(message, "content", None)
        if getattr(message, "type", "") == "ai" and content:
            if isinstance(content, list):
                return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
            return str(content)
    return "(no reply)"


def _resume_value(interrupt_value, approved: bool, note: str = ""):
    """Build the HITL resume payload for however many action requests were raised."""
    decision = {"type": "approve"} if approved else {"type": "reject", "message": note or "rejected"}
    if isinstance(interrupt_value, list):
        return {"decisions": [dict(decision) for _ in interrupt_value]}
    return {"decisions": [decision]}


async def run_chat(project: str, thread: str, once: str = "", auto_approve: bool = False) -> None:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.types import Command

    from assistant.config import get_settings
    from assistant.memory.models import Approval, ApprovalStatus, Message, Session
    from assistant.memory.sync_db import get_sync_session_factory
    from assistant.orchestrator.factory import build_orchestrator

    settings = get_settings()
    factory = get_sync_session_factory()

    # session row (persistent conversation registry, distinct from LangGraph checkpoints)
    with factory() as s:
        session_row = None
        if thread:
            session_row = s.execute(
                select(Session).where(Session.thread_id == thread)
            ).scalar_one_or_none()
        if session_row is None:
            session_row = Session(thread_id=thread or f"cli-{uuid.uuid4().hex[:12]}",
                                  title=once[:80] or "cli chat", channel="cli")
            s.add(session_row)
            s.commit()
        thread_id = session_row.thread_id
        session_id = session_row.id
    console.print(f"[dim]thread: {thread_id}[/dim]")

    def persist(role: str, content: str) -> None:
        with factory() as s:
            s.add(Message(session_id=session_id, role=role, content=content))
            s.commit()

    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        await checkpointer.setup()
        agent = build_orchestrator(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        async def turn(user_text: str) -> None:
            persist("user", user_text)
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": user_text}]}, config
            )
            while "__interrupt__" in result:
                intr = result["__interrupt__"][0]
                console.print("\n[bold yellow]Milestone gate[/bold yellow] - approval required:")
                console.print(intr.value)
                approved = True if auto_approve else typer.confirm("Approve?", default=False)
                with factory() as s:
                    s.add(Approval(
                        session_id=session_id, thread_id=thread_id, kind="delegate",
                        payload={"interrupt": str(intr.value)[:2000]},
                        status=ApprovalStatus.approved if approved else ApprovalStatus.rejected,
                    ))
                    s.commit()
                result = await agent.ainvoke(
                    Command(resume=_resume_value(intr.value, approved)), config
                )
            reply = _extract_text(result)
            persist("assistant", reply)
            console.print(f"\n[bold green]assistant>[/bold green] {reply}\n")

        if once:
            await turn(once)
            return
        console.print("Type 'exit' to quit.")
        while True:
            user_text = console.input("[bold cyan]you>[/bold cyan] ")
            if user_text.strip().lower() in {"exit", "quit"}:
                break
            if user_text.strip():
                await turn(user_text)
