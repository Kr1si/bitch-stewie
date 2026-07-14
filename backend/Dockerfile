# Backend image: FastAPI orchestrator + Claude Code CLI (spawned via the SDK).
# CC needs Node; the orchestrator needs Python 3.12 + uv-managed deps.

FROM python:3.12-slim

# git: CC sessions commit in delegated repos. openssh-client: git push over
# SSH to github.com (worker mounts deploy's key, see docker-compose.prod.yml).
# Node 22: runtime for the CC CLI.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git openssh-client \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7.13 /uv /uvx /usr/local/bin/

# CC runtime provisioning: git identity for delegated commits + local plugin
# clones under /opt/cc-plugins/enabled (see ASSISTANT_CC_PLUGINS_DIR)
COPY cc-setup.sh /tmp/cc-setup.sh
RUN sh /tmp/cc-setup.sh && rm /tmp/cc-setup.sh

WORKDIR /app

# Dependency layer first so code edits don't re-resolve the lockfile
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

# The CC CLI refuses --dangerously-skip-permissions (our bypassPermissions
# runner option) as root, and running as root also root-owns anything CC
# writes into the bind-mounted /projects on the host. UID/GID 1001 matches
# `deploy` on krisiserver so bind-mount ownership lines up either way.
RUN groupadd -g 1001 assistant && useradd -m -u 1001 -g 1001 assistant \
    && chown -R assistant:assistant /app /opt/cc-plugins \
    && mkdir -p /home/assistant/.cache && chown -R assistant:assistant /home/assistant/.cache
USER assistant

ENV ASSISTANT_API_HOST=0.0.0.0
EXPOSE 8000

# Migrations run here (the worker container skips them and just waits on the API).
# `assistant seed` (idempotent) ensures built-in project presets exist, e.g. the
# bitch-stewie self-rewrite target at /projects/bitch-stewie.
CMD ["sh", "-c", "uv run alembic upgrade head && uv run assistant seed && uv run uvicorn assistant.api.app:app --host 0.0.0.0 --port 8000"]
