"""FastAPI application factory."""

import asyncio
import sys
from contextlib import asynccontextmanager

# psycopg async cannot run on Windows' default ProactorEventLoop; the cc_bridge
# runs claude-agent-sdk sessions on its own Proactor loop thread instead.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Push LANGSMITH_* into os.environ BEFORE langchain/langgraph are imported,
# so the LangSmith tracer picks up tracing + the API key at configure time.
from assistant.config import apply_langsmith_env, get_settings, langsmith_enabled

LS_TRACING = apply_langsmith_env()

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


@asynccontextmanager
async def lifespan(app: FastAPI):
    from assistant.jobs.queue import app as job_app
    from assistant.orchestrator.factory import build_orchestrator
    from assistant.orchestrator.planner import build_planner

    settings = get_settings()
    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        app.state.orchestrator = build_orchestrator(checkpointer=checkpointer)
        app.state.planner = build_planner(checkpointer=checkpointer)
        # .defer() needs the connector pool open; the API only enqueues jobs,
        # the separate worker container is what runs() them.
        with job_app.open():
            yield


def create_app() -> FastAPI:
    from fastapi.middleware.cors import CORSMiddleware

    from assistant.api.chat import router as chat_router
    from assistant.api.diagrams import router as diagrams_router
    from assistant.api.examples import router as examples_router
    from assistant.api.knowledge import router as knowledge_router
    from assistant.api.plan import router as plan_router
    from assistant.api.research import router as research_router
    from assistant.api.routers import router
    from assistant.api.stats import router as stats_router
    from assistant.api.statusline import router as statusline_router
    from assistant.api.util import router as util_router

    app = FastAPI(title="Personal AI Project Assistant", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        # vite may fall back to 5174+ when 5173 is held by a stale dev server
        allow_origins=[f"http://localhost:{p}" for p in range(5173, 5180)]
                   + [f"http://127.0.0.1:{p}" for p in range(5173, 5180)],
        allow_methods=["*"], allow_headers=["*"],
    )
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
        settings = get_settings()
        return {
            "status": "ok",
            "default_model": settings.default_model,
            "langsmith": {
                "tracing": langsmith_enabled(),
                "project": settings.langsmith_project,
                "endpoint": settings.langsmith_endpoint,
            },
        }

    return app


app = create_app()
