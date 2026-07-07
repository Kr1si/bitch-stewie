"""Unified memory: workspace registry, decisions, sessions, approvals, CC runs.

Everything is project-scoped (workspace registry pattern). LangGraph checkpoint
tables and the Procrastinate queue live in the same database but are managed by
their own libraries, not by these models.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from assistant.memory.db import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    repo_path: Mapped[str | None]  # local checkout, if any
    vault_subdir: Mapped[str | None]  # project docs inside the vault
    status: Mapped[str] = mapped_column(default="active")  # active | archived

    work_items: Mapped[list["WorkItem"]] = relationship(back_populates="project")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="project")


class WorkItem(TimestampMixin, Base):
    """Tasks in the architect's work registry (not agent-internal todos)."""

    __tablename__ = "work_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str]
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(default="open")  # open | in_progress | done | dropped

    project: Mapped[Project] = relationship(back_populates="work_items")


class Decision(TimestampMixin, Base):
    """ADR-style decision log entry, linkable to the session that produced it."""

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id"))
    title: Mapped[str]
    context: Mapped[str] = mapped_column(Text, default="")
    decision: Mapped[str] = mapped_column(Text)
    consequences: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(default="accepted")  # proposed | accepted | superseded

    project: Mapped[Project] = relationship(back_populates="decisions")


class Preference(TimestampMixin, Base):
    """User conventions and recurring instructions, learned or stated."""

    __tablename__ = "preferences"

    id: Mapped[uuid.UUID] = _uuid_pk()
    key: Mapped[str] = mapped_column(unique=True)
    value: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(default="user")  # user | learned


class Session(TimestampMixin, Base):
    """One conversation with the orchestrator (CLI or web); maps to a LangGraph thread."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    thread_id: Mapped[str] = mapped_column(unique=True)  # LangGraph thread
    title: Mapped[str] = mapped_column(default="")
    channel: Mapped[str] = mapped_column(default="cli")  # cli | web

    messages: Mapped[list["Message"]] = relationship(back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str]  # user | assistant | tool | system
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="messages")


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Approval(TimestampMixin, Base):
    """Milestone gate raised by a LangGraph interrupt; answered from UI or CLI."""

    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id"))
    thread_id: Mapped[str]  # LangGraph thread to resume with Command(resume=...)
    kind: Mapped[str]  # plan | delegate | publish | merge | custom
    payload: Mapped[dict] = mapped_column(JSON, default=dict)  # what is being approved
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, native_enum=False), default=ApprovalStatus.pending
    )
    resolution_note: Mapped[str] = mapped_column(Text, default="")


class CCRunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    reviewing = "reviewing"
    succeeded = "succeeded"
    failed = "failed"
    aborted = "aborted"


class CCRun(TimestampMixin, Base):
    """One delegated Claude Code job (may internally use Agent Teams)."""

    __tablename__ = "cc_runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    repo_path: Mapped[str]
    brief: Mapped[str] = mapped_column(Text)
    model: Mapped[str]
    status: Mapped[CCRunStatus] = mapped_column(
        Enum(CCRunStatus, native_enum=False), default=CCRunStatus.queued
    )
    review_iterations: Mapped[int] = mapped_column(default=0)
    result: Mapped[dict] = mapped_column(JSON, default=dict)  # diff summary, commits, tests
    cc_session_id: Mapped[str | None]  # Agent SDK session id, for resume

    events: Mapped[list["CCRunEvent"]] = relationship(back_populates="run")


class CCRunEvent(Base):
    """Streamed event from an Agent SDK session or the CC hooks webhook."""

    __tablename__ = "cc_run_events"

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cc_runs.id"))
    source: Mapped[str]  # sdk | hook
    event_type: Mapped[str]  # tool_use | text | stop | subagent_stop | ...
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[CCRun] = relationship(back_populates="events")


class Example(TimestampMixin, Base):
    """A reference example the architect/doc-writer load when creating a new
    diagram or doc. Stored on the host filesystem so delegated Claude Code
    instances (which run on the host with file access) can read binary files
    directly for style/layout — only text examples are inlined into the
    orchestrator's own context."""

    __tablename__ = "examples"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    kind: Mapped[str]  # diagram | doc
    filename: Mapped[str]
    storage_path: Mapped[str]  # absolute path on the host
    mime: Mapped[str] = mapped_column(default="")
    note: Mapped[str] = mapped_column(Text, default="")
