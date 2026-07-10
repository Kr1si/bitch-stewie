# Backend image: FastAPI orchestrator + Claude Code CLI (spawned via the SDK).
# CC needs Node; the orchestrator needs Python 3.12 + uv-managed deps.

FROM python:3.12-slim

# git: CC sessions commit in delegated repos. Node 22: runtime for the CC CLI.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7.13 /uv /uvx /usr/local/bin/

WORKDIR /app

# Dependency layer first so code edits don't re-resolve the lockfile
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

ENV ASSISTANT_API_HOST=0.0.0.0
EXPOSE 8000

# Migrations run here (the worker container skips them and just waits on the API)
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn assistant.api.app:app --host 0.0.0.0 --port 8000"]
