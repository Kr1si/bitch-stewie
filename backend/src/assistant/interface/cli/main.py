"""assistant CLI - Phase 1 drives delegation directly; later phases go through the API."""

import asyncio
import sys

# Windows consoles default to legacy codepages (cp1250); KB content is UTF-8.
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich.console import Console
from rich.table import Table

from assistant.shared.config import apply_anthropic_env

# Mirror ANTHROPIC_AUTH_TOKEN -> ANTHROPIC_API_KEY if needed (chat model).
apply_anthropic_env()

app = typer.Typer(help="Personal AI project assistant CLI")
runs_app = typer.Typer(help="Inspect delegated Claude Code runs")
app.add_typer(runs_app, name="runs")
console = Console()


@app.command()
def version() -> None:
    """Show CLI version."""
    from importlib.metadata import version as pkg_version

    console.print(f"assistant {pkg_version('assistant')}")


# Built-in project presets seeded on every backend boot (idempotent). Add a row
# here when a project should always exist with a fixed repo_path, e.g. the
# orchestrator's own repo so CC can self-rewrite it. Keep names unique — the
# Project.name column is unique and create_project rejects duplicates.
SEED_PROJECTS = [
    {
        "name": "bitch-stewie",
        "description": (
            "Self-improvement target — the orchestrator's own repo. CC edits here "
            "on a feature branch; merge the PR -> CI redeploys -> the running "
            "orchestrator restarts with the upgraded code."
        ),
        "repo_path": "/projects/bitch-stewie",
    },
]

# Default autonomous goals seeded on every backend boot (idempotent). These are
# the data the scheduler dispatches on: kind determines the handler, cadence is
# a cron expr, config is whatever that kind needs. Add a row here when a goal
# should always exist (e.g. the daily AI-intelligence report). Title is the
# natural key the upsert matches on.
SEED_GOALS = [
    {
        "title": "Daily AI Intelligence Report",
        "description": (
            "Autonomous daily research: fan out to researcher subagents per category, "
            "write findings to dated dirs, compose a daily digest + market-ideas wiki."
        ),
        "kind": "research",
        "status": "active",
        "cadence": "0 7 * * *",
        "config": {
            "categories": [
                {
                    "id": "claude-code",
                    "name": "Everything Claude Code",
                    "sources": [
                        "https://docs.claude.com/en/docs/claude-code/overview",
                        "https://anthropic.com/news",
                        "https://github.com/anthropics/claude-code",
                    ],
                    "notes": "#1 priority — use CC maximally as the research tool.",
                },
                {
                    "id": "ai-security",
                    "name": "AI Security",
                    "themes": ["prompt injection", "guardrails", "AI safety", "red teaming",
                               "alignment", "OWASP for LLM"],
                },
                {
                    "id": "protocols",
                    "name": "Protocols & Standards",
                    "themes": ["MCP", "A2A", "open agent protocols", "agent communication standards"],
                },
                {
                    "id": "langchain",
                    "name": "LangChain & LLM Frameworks",
                    "sources": ["https://blog.langchain.dev", "https://youtube.com/@LangChain"],
                    "themes": ["LangChain", "LangGraph", "deepagents", "LangSmith"],
                },
                {
                    "id": "news-media",
                    "name": "AI News & Media",
                    "sources": ["https://youtube.com/@aiherchephko",
                               "https://youtube.com/@EverydayAI"],
                    "themes": ["YouTube", "podcasts", "major AI news"],
                },
                {
                    "id": "research-blogs",
                    "name": "Research & Blogs",
                    "sources": ["https://karpathy.blog", "https://medium.com (public)",
                               "https://news.ycombinator.com"],
                    "themes": ["Karpathy", "Medium", "Hacker News", "academic papers",
                               "AI blogs/forums"],
                },
            ],
            "output": {
                "findings_dir": "reports/{date}/findings",
                "digest_file": "reports/{date}/digest.md",
                "market_ideas_index": "reports/market-ideas.md",
                "market_ideas_dir": "reports/ideas",
            },
        },
    },
]


@app.command()
def seed() -> None:
    """Idempotently seed built-in project + goal presets (run by the backend on boot)."""
    import json

    from sqlalchemy import select

    from assistant.application.services.memory_service import (
        Goal,
        Project,
        get_sync_session_factory,
    )

    created, updated = 0, 0
    with get_sync_session_factory()() as s:
        for preset in SEED_PROJECTS:
            row = s.execute(
                select(Project).where(Project.name == preset["name"])
            ).scalar_one_or_none()
            if row is None:
                s.add(Project(**preset))
                created += 1
            elif row.repo_path != preset["repo_path"]:
                # Re-sync repo_path if a preset changed (e.g. mount path moved).
                row.repo_path = preset["repo_path"]
                updated += 1
        s.commit()
    console.print(f"[green]Seeded[/green] project presets: {created} new, {updated} updated.")

    gc, gu = 0, 0
    with get_sync_session_factory()() as s:
        for goal in SEED_GOALS:
            row = s.execute(
                select(Goal).where(Goal.title == goal["title"])
            ).scalar_one_or_none()
            if row is None:
                s.add(Goal(**goal))
                gc += 1
            else:
                # Re-sync mutable fields if a preset changed (categories, cadence, ...).
                changed = False
                for field in ("description", "kind", "status", "cadence"):
                    if getattr(row, field) != goal[field]:
                        setattr(row, field, goal[field])
                        changed = True
                if json.dumps(row.config, sort_keys=True) != json.dumps(goal["config"], sort_keys=True):
                    row.config = goal["config"]
                    changed = True
                if changed:
                    gu += 1
        s.commit()
    console.print(f"[green]Seeded[/green] goal presets: {gc} new, {gu} updated.")


@app.command()
def delegate(
    task: str,
    repo: str = typer.Option(..., "--repo", help="Path to the target repository"),
    constraint: list[str] = typer.Option([], "--constraint", "-c"),  # noqa: B008  # typer API pattern
    criteria: list[str] = typer.Option([], "--criteria", "-a"),  # noqa: B008  # typer API pattern
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Stream session events",
    ),
    teams: bool = typer.Option(
        False, "--teams", help="Enable experimental Agent Teams parallelism",
    ),
) -> None:
    """Delegate a coding task to a Claude Code instance (GLM 5.2 via Ollama)."""
    from assistant.application.services.jobs_service import Brief, DelegationRunner
    from assistant.application.services.memory_service import (
        Approval,
        ApprovalStatus,
        CCRunStatus,
        get_sync_session_factory,
    )

    # The Agent SDK spawns the claude CLI as a subprocess: needs the Proactor loop.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    brief = Brief(goal=task, repo_path=repo, constraints=constraint, acceptance_criteria=criteria)
    console.print(f"[bold]Delegating to Claude Code[/bold] (repo: {repo})")
    runner = DelegationRunner(on_event=console.log if verbose else None)
    outcome = asyncio.run(runner.run(brief, agent_teams=teams))

    console.print(
        f"\nRun [bold]{outcome.run_id}[/bold] finished: [bold]{outcome.status.value}[/bold] "
        f"after {outcome.review_iterations} review iteration(s)"
    )
    if outcome.result:
        for key, value in outcome.result.items():
            console.print(f"  {key}: {value}")

    if outcome.status == CCRunStatus.succeeded:
        branch = outcome.result.get("branch", "(unknown branch)")
        approved = typer.confirm(f"Milestone gate: accept the work on '{branch}'?")
        with get_sync_session_factory()() as s:
            s.add(Approval(
                thread_id=str(outcome.run_id), kind="merge",
                payload={"run_id": str(outcome.run_id), "branch": branch},
                status=ApprovalStatus.approved if approved else ApprovalStatus.rejected,
            ))
            s.commit()
        console.print("[green]Approved[/green] - merge the branch when ready."
                      if approved else "[red]Rejected[/red] - branch left for inspection.")


@app.command()
def chat(
    project: str = typer.Option("", "--project", help="Project context"),
    thread: str = typer.Option("", "--thread", help="Resume an existing thread id"),
    once: str = typer.Option("", "--once", help="Single message, then exit (scripting)"),
    yes: bool = typer.Option(False, "--yes", help="Auto-approve milestone gates"),
) -> None:
    """Chat with the orchestrator (deep agent with architect/doc/research/code subagents)."""
    from assistant.interface.cli.chat import run_chat

    if sys.platform == "win32":
        # async psycopg checkpointer needs the Selector loop; CC delegation
        # runs on the dedicated Proactor worker thread.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_chat(project, thread, once=once, auto_approve=yes))


@app.command()
def ingest(
    path: str,
    project: str = typer.Option("", "--project", help="Project collection (default: global)"),
) -> None:
    """Ingest a markdown/text file or directory into the knowledge base."""
    from assistant.application.services.knowledge_service import ingest_path

    result = ingest_path(path, project=project or None)
    console.print(f"Ingested {result['files']} file(s), {result['chunks']} chunk(s): "
                  f"{', '.join(result['names'])}")


@app.command()
def search(
    query: str,
    project: str = typer.Option("", "--project", help="Project collection (default: global)"),
) -> None:
    """Hybrid search over the knowledge base."""
    from assistant.application.services.knowledge_service import hybrid_search

    for h in hybrid_search(query, project=project or None):
        console.print(f"[bold]{h['source']}[/bold] [dim]({h['kind']}, {h['score']:.3f})[/dim]")
        console.print(h["text"][:300] + "\n")


@app.command()
def watch() -> None:
    """Watch the vault folder and auto-ingest changed markdown files."""
    from assistant.application.services.jobs_service import watch_vault

    watch_vault()


@app.command()
def worker() -> None:
    """Run the Procrastinate job worker (delegation + ingestion queues)."""
    from assistant.application.services.jobs_service import job_app

    with job_app.open():
        job_app.run_worker()


@app.command()
def approvals(limit: int = 20) -> None:
    """Show the milestone approval log."""
    from sqlalchemy import select

    from assistant.application.services.memory_service import Approval, get_sync_session_factory

    with get_sync_session_factory()() as s:
        rows = s.execute(select(Approval).order_by(Approval.created_at.desc())
                         .limit(limit)).scalars().all()
    table = Table("id", "kind", "status", "thread", "created")
    for a in rows:
        table.add_row(str(a.id), a.kind, a.status.value, a.thread_id,
                      a.created_at.strftime("%Y-%m-%d %H:%M"))
    console.print(table)


@runs_app.command("list")
def runs_list(limit: int = 10) -> None:
    """Show recent delegated runs."""
    from sqlalchemy import select

    from assistant.application.services.memory_service import CCRun, get_sync_session_factory

    with get_sync_session_factory()() as s:
        rows = s.execute(
            select(CCRun).order_by(CCRun.created_at.desc()).limit(limit)
        ).scalars().all()
    table = Table("id", "status", "model", "repo", "reviews", "created")
    for r in rows:
        table.add_row(str(r.id), r.status.value, r.model, r.repo_path,
                      str(r.review_iterations), r.created_at.strftime("%Y-%m-%d %H:%M"))
    console.print(table)


@runs_app.command("events")
def runs_events(run_id: str, limit: int = 50) -> None:
    """Show events for one run."""
    from sqlalchemy import select

    from assistant.application.services.memory_service import CCRunEvent, get_sync_session_factory

    with get_sync_session_factory()() as s:
        rows = s.execute(
            select(CCRunEvent).where(CCRunEvent.run_id == run_id)
            .order_by(CCRunEvent.created_at).limit(limit)
        ).scalars().all()
    for e in rows:
        console.print(f"[dim]{e.created_at:%H:%M:%S}[/dim] [{e.event_type}] {str(e.payload)[:160]}")


if __name__ == "__main__":
    app()
