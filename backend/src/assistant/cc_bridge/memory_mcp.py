"""In-process MCP server exposing the assistant's memory to Claude Code sessions.

Runs inside our Python process via the Agent SDK and is proxied into every
spawned CC instance, so delegated agents can read the workspace registry and
record decisions without us stuffing everything into the brief.
"""

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool
from sqlalchemy import select

from assistant.memory.models import Decision, Preference, Project
from assistant.memory.sync_db import get_sync_session_factory


def _text(payload: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": payload}]}


@tool(
    "list_projects",
    "List all projects in the architect's workspace registry with status and repo path.",
    {},
)
async def list_projects(args: dict[str, Any]) -> dict[str, Any]:
    with get_sync_session_factory()() as session:
        rows = session.execute(select(Project)).scalars().all()
        if not rows:
            return _text("No projects registered yet.")
        lines = [f"- {p.name} [{p.status}] repo={p.repo_path or '-'} :: {p.description}" for p in rows]
        return _text("\n".join(lines))


@tool(
    "get_preferences",
    "Get the user's stored conventions and preferences (coding style, doc style, recurring instructions).",
    {},
)
async def get_preferences(args: dict[str, Any]) -> dict[str, Any]:
    with get_sync_session_factory()() as session:
        rows = session.execute(select(Preference)).scalars().all()
        if not rows:
            return _text("No preferences stored yet.")
        return _text("\n".join(f"- {p.key}: {p.value}" for p in rows))


@tool(
    "record_decision",
    "Record an ADR-style decision made during this task (title, decision, optional context/consequences, project name).",
    {"title": str, "decision": str, "context": str, "project": str},
)
async def record_decision(args: dict[str, Any]) -> dict[str, Any]:
    with get_sync_session_factory()() as session:
        project = session.execute(
            select(Project).where(Project.name == args.get("project", ""))
        ).scalar_one_or_none()
        if project is None:
            return _text(f"Unknown project '{args.get('project')}'. Use list_projects first.")
        session.add(
            Decision(
                project_id=project.id,
                title=args["title"],
                decision=args["decision"],
                context=args.get("context", ""),
            )
        )
        session.commit()
        return _text("Decision recorded.")


def build_memory_server():
    return create_sdk_mcp_server(
        name="assistant-memory",
        version="0.1.0",
        tools=[list_projects, get_preferences, record_decision],
    )
