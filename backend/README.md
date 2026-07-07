# Assistant Backend

Orchestration layer of the personal AI project assistant: LangChain + LangGraph + Deep Agents over FastAPI, delegating heavy coding work to Claude Code instances running on GLM 5.2 via Ollama.

See `../PLAN.md` for the full architecture and phase plan.

## Development

```bash
uv sync                     # install deps (corporate proxy: UV_NATIVE_TLS=true, unset SSL_CERT_FILE)
uv run pytest               # tests
uv run uvicorn assistant.api.app:app --reload   # API on :8000
uv run assistant --help     # CLI
```

## Stack services

`docker compose up -d` from `../docker/` starts Postgres, Qdrant, and draw.io. Ollama and Claude Code run on the host.
