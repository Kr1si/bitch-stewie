# Personal AI Project Assistant

Orchestration layer over Claude Code for System Architect work: diagrams
(LikeC4 → draw.io), documentation (Markdown → docx/pdf), research (native
/deep-research + Qdrant knowledge base), and delegated coding — everything on
GLM 5.2 via Ollama.

See `PLAN.md` for the approved architecture and phases.

## Layout

| Path | What |
|---|---|
| `backend/` | Python: FastAPI + LangGraph/deepagents orchestrator, cc_bridge, RAG, jobs (own git repo) |
| `frontend/` | React web UI: chat with approval gates, projects, CC run monitor, knowledge, diagrams (own git repo) |
| `docker/` | Compose stack: Postgres (host port **5433**), Qdrant (6333), draw.io (8080) |
| `cc-skills/` | Claude Code plugin with the thin contract skills for delegated instances |
| `backend/skills/orchestrator/` | Deep-agent skills for the orchestrator itself |

## Running

```bash
# 1. infrastructure (Postgres/Qdrant/drawio) — Ollama + Claude Code run on the host
cd docker && docker compose up -d

# 2. backend setup (corporate proxy: unset SSL_CERT_FILE REQUESTS_CA_BUNDLE; UV_NATIVE_TLS=true)
cd backend && uv sync && uv run alembic upgrade head

# 3. use it
uv run assistant chat                       # talk to the orchestrator
uv run assistant delegate "<task>" --repo <path>   # direct delegation
uv run assistant ingest <path> [--project X]       # feed the knowledge base
uv run assistant search "<query>"                  # hybrid KB search
uv run assistant runs list / approvals             # inspect activity
uv run assistant watch                             # vault auto-ingest
uv run uvicorn assistant.api.app:app --port 8000 --loop asyncio:SelectorEventLoop   # API for the web UI
# Windows: the --loop flag is required — async psycopg (checkpointer) cannot run
# on uvicorn's default Proactor loop. Pick any free port (8000 is often taken locally).

# 4. web UI
cd frontend && npm run dev                  # http://localhost:5173
```

## Model configuration

Default model is `ollama:glm-5.2:cloud` everywhere (orchestrator via LangChain,
Claude Code instances via `ANTHROPIC_BASE_URL` → Ollama). Override with
`ASSISTANT_DEFAULT_MODEL` / `ASSISTANT_CC_MODEL`. Embeddings: `bge-m3` local.
