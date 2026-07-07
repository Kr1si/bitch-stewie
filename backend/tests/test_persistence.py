"""Integration tests against the dockerized Postgres (docker/ stack must be up)."""

import uuid

import pytest
from sqlalchemy import select

from assistant.memory.db import get_session_factory
from assistant.memory.models import Project


@pytest.mark.anyio
async def test_project_roundtrip() -> None:
    factory = get_session_factory()
    name = f"test-project-{uuid.uuid4().hex[:8]}"
    async with factory() as session:
        session.add(Project(name=name, description="integration test"))
        await session.commit()
    async with factory() as session:
        row = (await session.execute(select(Project).where(Project.name == name))).scalar_one()
        assert row.status == "active"
        await session.delete(row)
        await session.commit()


@pytest.mark.anyio
async def test_checkpointer_setup() -> None:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    from assistant.config import get_settings

    async with AsyncPostgresSaver.from_conn_string(get_settings().database_url) as cp:
        await cp.setup()
        # setup is idempotent; listing checkpoints of an unknown thread returns nothing
        found = [c async for c in cp.alist({"configurable": {"thread_id": "smoke-none"}})]
        assert found == []
