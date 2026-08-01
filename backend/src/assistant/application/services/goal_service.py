"""Shared Goal CRUD service.

Both the goals HTTP router (interface/api/goals.py) and the goal-creator graph's
persist node call into this module, so goal creation logic lives in one place
instead of being duplicated across the API layer and the agent layer.
"""

import uuid
from typing import Any

from sqlalchemy import select

from assistant.application.services.memory_service import (
    Goal,
    GoalKind,
    GoalStatus,
    Project,
    get_session_factory,
)


def _validate_kind(kind: str) -> GoalKind:
    try:
        return GoalKind(kind)
    except ValueError:
        raise ValueError(f"invalid goal kind '{kind}': must be one of "
                         f"{[k.value for k in GoalKind]}") from None


def _validate_cadence(cadence: str) -> str:
    fields = cadence.strip().split()
    if len(fields) != 5:
        raise ValueError(f"cadence '{cadence}' is not a valid 5-field cron expression")
    return cadence


def serialize(goal: Goal) -> dict[str, Any]:
    return {
        "id": str(goal.id),
        "project_id": str(goal.project_id) if goal.project_id else None,
        "title": goal.title,
        "description": goal.description,
        "kind": goal.kind.value,
        "status": goal.status.value,
        "cadence": goal.cadence,
        "config": goal.config,
        "last_run_at": goal.last_run_at.isoformat() if goal.last_run_at else None,
        "next_run_at": goal.next_run_at.isoformat() if goal.next_run_at else None,
        "created_at": goal.created_at.isoformat() if goal.created_at else None,
        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
    }


async def create_goal_entity(
    title: str,
    kind: str = "research",
    cadence: str = "0 7 * * *",
    description: str = "",
    status: str = "active",
    project_id: uuid.UUID | None = None,
    config: dict | None = None,
) -> Goal:
    """Validate + insert a Goal. Raises ValueError on bad kind/cadence/project."""
    goal_kind = _validate_kind(kind)
    goal_status = GoalStatus(status)
    clean_cadence = _validate_cadence(cadence)

    async with get_session_factory()() as s:
        if project_id is not None:
            project = await s.get(Project, project_id)
            if project is None:
                raise ValueError(f"project '{project_id}' not found")
        goal = Goal(
            project_id=project_id,
            title=title,
            description=description,
            kind=goal_kind,
            status=goal_status,
            cadence=clean_cadence,
            config=config if config is not None else {},
        )
        s.add(goal)
        await s.flush()
        await s.refresh(goal)
        return goal


async def list_goals() -> list[Goal]:
    async with get_session_factory()() as s:
        rows = (await s.execute(select(Goal).order_by(Goal.created_at))).scalars().all()
    return list(rows)


async def list_goals_for_project(project_id: uuid.UUID | None) -> list[Goal]:
    async with get_session_factory()() as s:
        q = select(Goal).order_by(Goal.created_at)
        if project_id is not None:
            q = q.where(Goal.project_id == project_id)
        rows = (await s.execute(q)).scalars().all()
    return list(rows)


async def get_goal(goal_id: uuid.UUID) -> Goal | None:
    async with get_session_factory()() as s:
        return await s.get(Goal, goal_id)


async def delete_goal(goal_id: uuid.UUID) -> bool:
    async with get_session_factory()() as s:
        goal = await s.get(Goal, goal_id)
        if goal is None:
            return False
        await s.delete(goal)
        await s.commit()
        return True
