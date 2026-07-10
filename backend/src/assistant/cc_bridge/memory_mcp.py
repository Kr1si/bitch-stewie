"""In-process MCP server exposing the assistant's memory to Claude Code sessions.

Runs inside our Python process via the Agent SDK and is proxied into every
spawned CC instance, so delegated agents can read the workspace registry,
browse the reference-examples library, search the knowledge base, and record
decisions without us stuffing everything into the brief.

Decisions and conventions are additionally bridged into the target repo's
`.claude/rules/*.md` (when `write_project_rules` is on) so the *next* CC
session in that repo sees them natively via setting_sources=["project"] —
native CC memory, not a reimplementation.
"""

import logging
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool
from sqlalchemy import select

logger = logging.getLogger(__name__)

from assistant.config import get_settings
from assistant.memory.models import Decision, Example, Preference, Project
from assistant.memory.sync_db import get_sync_session_factory

_TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".rst", ".drawio", ".xml", ".svg"}


def _text(payload: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": payload}]}


def _project_by_name(session, name: str) -> Project | None:
    return session.execute(
        select(Project).where(Project.name == name)
    ).scalar_one_or_none()


def _append_project_rule(repo_path: str | None, filename: str, line: str) -> bool:
    """Append one line to <repo>/.claude/rules/<filename>; never raises.

    Returns True only when the line actually landed (skips exact duplicates).
    """
    if not get_settings().write_project_rules or not repo_path:
        return False
    try:
        rules_dir = Path(repo_path) / ".claude" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        target = rules_dir / filename
        line = line.rstrip()
        if target.is_file() and line in target.read_text(encoding="utf-8").splitlines():
            return True  # already recorded; don't accrete duplicates
        with target.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        return True
    except OSError as exc:
        logger.warning("project rule write failed (%s): %r", filename, exc)
        return False  # read-only repo must never break a delegation


# -- registry / preferences ---------------------------------------------------


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


# -- decisions ----------------------------------------------------------------


@tool(
    "record_decision",
    "Record an ADR-style decision made during this task (title, decision, optional context/consequences, project name).",
    {"title": str, "decision": str, "context": str, "project": str},
)
async def record_decision(args: dict[str, Any]) -> dict[str, Any]:
    with get_sync_session_factory()() as session:
        project = _project_by_name(session, args.get("project", ""))
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
        repo_path = project.repo_path
    _append_project_rule(
        repo_path, "decisions.md",
        f"- **{args['title']}**: {args['decision']}"
        + (f" _(context: {args['context']})_" if args.get("context") else ""),
    )
    return _text("Decision recorded (DB + project .claude/rules/decisions.md).")


@tool(
    "list_decisions",
    "List recent ADR-style decisions for a project (most recent first).",
    {"project": str},
)
async def list_decisions(args: dict[str, Any]) -> dict[str, Any]:
    with get_sync_session_factory()() as session:
        project = _project_by_name(session, args.get("project", ""))
        if project is None:
            return _text(f"Unknown project '{args.get('project')}'. Use list_projects first.")
        rows = session.execute(
            select(Decision).where(Decision.project_id == project.id)
            .order_by(Decision.created_at.desc()).limit(20)
        ).scalars().all()
        if not rows:
            return _text(f"No decisions recorded for '{project.name}' yet.")
        return _text("\n".join(
            f"- [{d.created_at:%Y-%m-%d}] {d.title}: {d.decision}" for d in rows
        ))


@tool(
    "write_convention",
    "Record a recurring convention/preference for a project (key + value). Persists to DB "
    "and to the project's .claude/rules/conventions.md so future CC sessions see it natively.",
    {"key": str, "value": str, "project": str},
)
async def write_convention(args: dict[str, Any]) -> dict[str, Any]:
    with get_sync_session_factory()() as session:
        project = _project_by_name(session, args.get("project", ""))
        repo_path = project.repo_path if project else None
        # Preference.key is unique — upsert, don't blindly insert
        existing = session.execute(
            select(Preference).where(Preference.key == args["key"])
        ).scalar_one_or_none()
        if existing:
            existing.value = args["value"]
            existing.source = "cc_session"
        else:
            session.add(Preference(key=args["key"], value=args["value"], source="cc_session"))
        session.commit()
    _append_project_rule(repo_path, "conventions.md", f"- **{args['key']}**: {args['value']}")
    where = "DB + project .claude/rules/conventions.md" if repo_path else "DB (no project repo)"
    return _text(f"Convention recorded ({where}).")


# -- reference examples ---------------------------------------------------------


def _example_rows(session, project_name: str, kind: str = ""):
    q = select(Example).order_by(Example.created_at.desc())
    if kind:
        q = q.where(Example.kind == kind)
    if not project_name or project_name == "global":
        q = q.where(Example.project_id.is_(None))
    else:
        project = _project_by_name(session, project_name)
        if project is None:
            return None
        q = q.where(Example.project_id == project.id)
    return session.execute(q).scalars().all()


@tool(
    "list_examples",
    "List reference examples (diagrams/docs the user uploaded to mimic). "
    "kind: 'diagram', 'doc', or '' for both; project: name or 'global'. "
    "Each line: name | kind | absolute path | note — read the path directly for style/layout.",
    {"project": str, "kind": str},
)
async def list_examples(args: dict[str, Any]) -> dict[str, Any]:
    with get_sync_session_factory()() as session:
        rows = _example_rows(session, args.get("project", ""), args.get("kind", ""))
        if rows is None:
            return _text(f"Unknown project '{args.get('project')}'. Use list_projects first.")
        if not rows:
            return _text(f"No reference examples for project '{args.get('project') or 'global'}'.")
        return _text("\n".join(
            f"{e.filename} | {e.kind} | {e.storage_path} | {e.note}" for e in rows
        ))


@tool(
    "read_example",
    "Read one reference example. Text examples (.md/.txt/.drawio/.xml/.svg) are inlined; "
    "binary ones return their absolute path — read that file directly instead.",
    {"name": str, "project": str, "kind": str},
)
async def read_example(args: dict[str, Any]) -> dict[str, Any]:
    with get_sync_session_factory()() as session:
        rows = _example_rows(session, args.get("project", ""), args.get("kind", ""))
        if rows is None:
            return _text(f"Unknown project '{args.get('project')}'. Use list_projects first.")
        match = next((e for e in rows if e.filename == args.get("name")), None)
    if match is None:
        return _text(f"No example named '{args.get('name')}' for project '{args.get('project')}'.")
    suffix = Path(match.filename).suffix.lower()
    if suffix in _TEXT_SUFFIXES:
        try:
            return _text(Path(match.storage_path).read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            return _text(f"Could not read {match.storage_path}: {exc}")
    return _text(
        f"Binary example '{match.filename}' at {match.storage_path} "
        f"(mime {match.mime or 'unknown'}). Read that file directly with the Read tool."
    )


# -- knowledge base -------------------------------------------------------------


@tool(
    "search_knowledge",
    "Hybrid-search the assistant's knowledge base (project notes, ingested docs). "
    "project: name or '' for the global collection.",
    {"query": str, "project": str, "limit": int},
)
async def search_knowledge(args: dict[str, Any]) -> dict[str, Any]:
    from anyio import to_thread

    from assistant.rag.store import hybrid_search

    limit = min(int(args.get("limit") or 5), 10)
    project = args.get("project") or None
    try:
        hits = await to_thread.run_sync(
            lambda: hybrid_search(args["query"], project=project, limit=limit)
        )
    except Exception as exc:  # noqa: BLE001 - qdrant down must not kill the session
        return _text(f"Knowledge search unavailable: {exc}")
    if not hits:
        return _text("No knowledge-base hits.")
    lines = []
    for h in hits:
        src = h.get("source", "?")
        score = h.get("score", 0)
        text = str(h.get("text", ""))[:400].replace("\n", " ")
        lines.append(f"[{score:.2f}] {src}: {text}")
    return _text("\n".join(lines))


def build_memory_server():
    return create_sdk_mcp_server(
        name="assistant-memory",
        version="0.2.0",
        tools=[
            list_projects, get_preferences,
            record_decision, list_decisions, write_convention,
            list_examples, read_example, search_knowledge,
        ],
    )