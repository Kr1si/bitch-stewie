"""Shared helper for resolving the session's fixed project from RunnableConfig.

This app is project-scoped per session (one chat thread / plan thread = one
project). The project's UUID is threaded through LangGraph's ``RunnableConfig``
as ``config["configurable"]["project_id"]`` rather than being a model-supplied
tool argument, so tools resolve it here instead of taking a ``project``
parameter.
"""

import uuid

from langchain_core.runnables import RunnableConfig
from sqlalchemy import select

from assistant.memory.models import Project
from assistant.memory.sync_db import get_sync_session_factory


def current_project(config: RunnableConfig) -> Project:
    """Resolve the ``Project`` row for this session from ``config``.

    Raises ``ValueError`` if ``project_id`` is missing from config or no
    matching project exists — callers should let this propagate rather than
    swallow it, since it indicates a config-plumbing bug, not a runtime state.
    """
    configurable = (config or {}).get("configurable", {}) if isinstance(config, dict) else {}
    raw_project_id = configurable.get("project_id")
    if not raw_project_id:
        raise ValueError(
            "No project_id in config['configurable'] — every session must be "
            "project-scoped; this is a config-plumbing bug, not a runtime error."
        )
    project_id = raw_project_id if isinstance(raw_project_id, uuid.UUID) else uuid.UUID(str(raw_project_id))

    with get_sync_session_factory()() as s:
        proj = s.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()
    if proj is None:
        raise ValueError(f"No project found for project_id={project_id}.")
    return proj
