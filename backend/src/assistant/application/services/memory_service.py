"""Memory service facade.

Re-exports the persistence entry points and ORM models the interface layer
needs, so routers/CLI/MCP never import `assistant.infrastructure.memory`
directly. Application code talks to this module; it delegates to
infrastructure, where the SQLAlchemy engine and models actually live.
"""

from assistant.infrastructure.memory.db import get_session_factory
from assistant.infrastructure.memory.models import (
    Approval,
    ApprovalStatus,
    CCRun,
    CCRunEvent,
    CCRunStatus,
    Decision,
    Example,
    Goal,
    GoalKind,
    GoalStatus,
    Message,
    Preference,
    Project,
    Session,
)
from assistant.infrastructure.memory.sync_db import get_sync_session_factory

__all__ = [
    "Approval",
    "ApprovalStatus",
    "CCRun",
    "CCRunEvent",
    "CCRunStatus",
    "Decision",
    "Example",
    "Goal",
    "GoalKind",
    "GoalStatus",
    "Message",
    "Preference",
    "Project",
    "Session",
    "get_session_factory",
    "get_sync_session_factory",
]
