"""FastAPI application factory."""

import asyncio
import sys
from contextlib import asynccontextmanager

# psycopg async cannot run on Windows' default ProactorEventLoop; the cc_bridge
# runs claude-agent-sdk sessions on its own Proactor loop thread instead.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from assistant.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from assistant.orchestrator.factory import build_orchestrator

    settings = get_settings()
    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        app.state.orchestrator = build_orchestrator(checkpointer=checkpointer)
        yield


def create_app() -> FastAPI:
    from fastapi.middleware.cors import CORSMiddleware

    from assistant.api.chat import router as chat_router
    from assistant.api.diagrams import router as diagrams_router
    from assistant.api.examples import router as examples_router
    from assistant.api.knowledge import router as knowledge_router
    from assistant.api.routers import router
    from assistant.api.stats import router as stats_router
    from assistant.api.util import router as util_router

    app = FastAPI(title="Personal AI Project Assistant", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"], allow_headers=["*"],
    )
    app.include_router(router)
    app.include_router(chat_router)
    app.include_router(diagrams_router)
    app.include_router(knowledge_router)
    app.include_router(examples_router)
    app.include_router(stats_router)
    app.include_router(util_router)

    @app.get("/health")
    async def health() -> dict:
        settings = get_settings()
        return {"status": "ok", "default_model": settings.default_model}

    return app


app = create_app()
