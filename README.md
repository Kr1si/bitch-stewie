# Personal AI Project Assistant

Orchestration layer over Claude Code for System Architect work: diagrams
(LikeC4 → draw.io), documentation (Markdown → docx/pdf), research (native
/deep-research + Qdrant knowledge base), and delegated coding — default LLM
is LongCat-2.0 (Anthropic-Messages-native).

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
# 1. infrastructure (Postgres/Qdrant/drawio) — Claude Code runs on the host
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

## Remote server (krisiserver)

Personal VPS at `194.182.86.101` — the deployment target for this stack
(docker compose, SSH-tunnel-only access). Connect as `deploy` (key-only).
Server setup, hardening, deployment plan, and gotchas:
[`docs/krisiserver.md`](docs/krisiserver.md).

## Model configuration

Default model is LongCat-2.0 (`anthropic:LongCat-2.0`) everywhere — orchestrator
via LangChain, Claude Code instances via `ANTHROPIC_BASE_URL` → LongCat — set in
`docker-compose.prod.yml` and `docker/.env.example`. LongCat speaks the
Anthropic Messages API natively (no model-name mapping). Ollama is still in the
stack for `bge-m3` embeddings; to use it for inference instead, switch the
`ASSISTANT_CC_*` / `ANTHROPIC_*` vars (see `docker/.env.example`).
