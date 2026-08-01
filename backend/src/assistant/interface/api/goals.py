"""Goals CRUD: the data the autonomous scheduler dispatches on.

A Goal is a first-class, scheduleable objective (research / coding / testing).
The scheduler reads active goals and runs each on its cadence; the Goals API
lets the UI list, create, and pause/resume them. Creation is validated light —
the real guardrail is the human review gate before any goal's output ships.
"""

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from assistant.application.services.memory_service import (
    Goal,
    GoalKind,
    GoalStatus,
    Project,
    get_session_factory,
)
from assistant.shared.config import get_settings

router = APIRouter(prefix="/api/goals")


class GoalIn(BaseModel):
    project_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1)
    description: str = ""
    kind: GoalKind = GoalKind.research
    status: GoalStatus = GoalStatus.active
    cadence: str = Field("0 7 * * *", description="Cron expression (UTC).")
    config: dict = Field(default_factory=dict)


class GoalPatch(BaseModel):
    status: GoalStatus | None = None
    cadence: str | None = None
    description: str | None = None
    config: dict | None = None


def _serialize(g: Goal) -> dict[str, Any]:
    return {
        "id": str(g.id),
        "project_id": str(g.project_id) if g.project_id else None,
        "title": g.title,
        "description": g.description,
        "kind": g.kind.value,
        "status": g.status.value,
        "cadence": g.cadence,
        "config": g.config,
        "last_run_at": g.last_run_at.isoformat() if g.last_run_at else None,
        "next_run_at": g.next_run_at.isoformat() if g.next_run_at else None,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
    }


@router.get("")
async def list_goals() -> list[dict[str, Any]]:
    async with get_session_factory()() as s:
        rows = (await s.execute(select(Goal).order_by(Goal.created_at))).scalars().all()
    return [_serialize(g) for g in rows]


@router.post("", status_code=201)
async def create_goal(body: GoalIn) -> dict[str, Any]:
    async with get_session_factory()() as s:
        if body.project_id is not None:
            project = await s.get(Project, body.project_id)
            if project is None:
                raise HTTPException(404, "project not found")
        goal = Goal(**body.model_dump())
        s.add(goal)
        await s.flush()
        await s.refresh(goal)
        return _serialize(goal)


@router.patch("/{goal_id}")
async def update_goal(goal_id: uuid.UUID, body: GoalPatch) -> dict[str, Any]:
    async with get_session_factory()() as s:
        goal = await s.get(Goal, goal_id)
        if goal is None:
            raise HTTPException(404, "goal not found")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(goal, field, value)
        await s.flush()
        await s.refresh(goal)
        return _serialize(goal)


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

    market_ideas = read("../market-ideas.md")  # relative to date dir -> reports/market-ideas.md
    return {
        "date": date,
        "digest": read("digest.md"),
        "findings": findings,
        "market_ideas": market_ideas,
    }
