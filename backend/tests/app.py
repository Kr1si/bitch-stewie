"""Offline test application factory.

`create_app()` in production wires up a real Postgres checkpointer and builds
the orchestrator/planner deepagents graphs (which need an LLM). That makes the
raw app unusable in unit tests without docker + a live model.

`make_test_app()` builds a fresh app mounting the SAME routers as production
but with a lightweight lifespan that:
  - swaps the DB for an in-memory SQLite database (aiosqlite), so every router
    that goes through `get_session_factory()` works with no docker, and
  - installs fake orchestrator/planner graphs (AsyncMock) so the chat/plan SSE
    endpoints can be exercised without a real LLM.

Import this in tests and wrap with fastapi.testclient.TestClient, exactly like
the existing tests use `create_app()`:

    from tests.app import make_test_app
    with TestClient(make_test_app()) as client:
        ...
"""

import contextlib
from collections.abc import AsyncIterator
from unittest import mock

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from assistant.infrastructure.memory import db as db_module


def _fake_graph():
    """Fake deepagents graph: streams nothing, reports a clean non-gated state.

    The chat/plan SSE endpoints drive the graph via `agent.astream(...)` then
    `agent.aget_state(config)`; the router tests only assert the HTTP/SSE layer,
    so the fake yields no tokens and reports no pending interrupts -> a single
    `done` event.
    """
    g = mock.AsyncMock(name="fake_graph")

    async def astream_events(*args, **kwargs):
        return
        yield  # pragma: no cover - unreachable; makes this an async generator

    async def astream(*args, **kwargs):
        return
        yield  # pragma: no cover - unreachable; makes this an async generator

    async def aget_state(*args, **kwargs):
        return mock.Mock(values={}, next=(), tasks=())

    g.astream_events = astream_events
    g.astream = astream
    g.aget_state = aget_state
    return g


def make_test_app() -> FastAPI:
    """Build an app with in-memory SQLite + fake graphs, mirroring production."""
    # In-memory SQLite via aiosqlite. The engine is created once and held in a
    # closure; tables are created in the lifespan on the SAME engine so they
    # survive for the app's lifetime (in-memory SQLite lives/dies with the
    # engine, not the connection).
    engine = create_async_engine("sqlite+aiosqlite://", future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    tables_ready = False

    # Patch the factory everywhere it was imported. The API routers each did
    # `from ...memory_service import get_session_factory`, binding the original
    # into their own namespaces, so patching only db.py is not enough.
    import assistant.application.services.memory_service as memory_service
    for mod in (db_module, memory_service):
        mod.get_session_factory = lambda: session_factory  # type: ignore[assignment]
    for mod_name in (
        "assistant.interface.api.routers",
        "assistant.interface.api.chat",
        "assistant.interface.api.plan",
        "assistant.interface.api.statusline",
        "assistant.interface.api.stats",
        "assistant.interface.api.diagrams",
        "assistant.interface.api.examples",
    ):
        import importlib
        importlib.import_module(mod_name).get_session_factory = lambda: session_factory  # type: ignore[assignment]

    app = FastAPI(title="bitch-stewie test")

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        nonlocal tables_ready
        if not tables_ready:
            async with engine.begin() as conn:
                await conn.run_sync(db_module.Base.metadata.create_all)
            tables_ready = True
        app.state.checkpointer = mock.AsyncMock(name="fake_checkpointer")
        app.state.orchestrator = _fake_graph()
        app.state.planner = _fake_graph()
        yield

    app.router.lifespan_context = lifespan

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"http://localhost:{p}" for p in range(5173, 5180)]
        + [f"http://127.0.0.1:{p}" for p in range(5173, 5180)],
        allow_methods=["*"], allow_headers=["*"],
    )

    # Mount the same routers production mounts (see assistant.interface.api.app).
    from assistant.interface.api.chat import router as chat_router
    from assistant.interface.api.diagrams import router as diagrams_router
    from assistant.interface.api.examples import router as examples_router
    from assistant.interface.api.knowledge import router as knowledge_router
    from assistant.interface.api.plan import router as plan_router
    from assistant.interface.api.research import router as research_router
    from assistant.interface.api.routers import router
    from assistant.interface.api.stats import router as stats_router
    from assistant.interface.api.statusline import router as statusline_router
    from assistant.interface.api.util import router as util_router

    app.include_router(router)
    app.include_router(chat_router)
    app.include_router(plan_router)
    app.include_router(diagrams_router)
    app.include_router(knowledge_router)
    app.include_router(research_router)
    app.include_router(examples_router)
    app.include_router(stats_router)
    app.include_router(statusline_router)
    app.include_router(util_router)

    @app.get("/health")
    async def health() -> dict:
        from assistant.shared.config import get_settings
        return {"status": "ok", "default_model": get_settings().default_model, "langsmith": {}}

    return app


__all__ = ["make_test_app"]
