# Personal AI Project Assistant — top-level task runner.
# Targets wrap the README runbook. Override vars on the command line, e.g.
#   make backend PORT=8011
#   make delegate TASK="add login page" REPO=../some-repo

# --- corporate proxy (Zscaler) workaround, applied to every recipe ---
# uv needs native TLS and NO pinned cert bundle; make's export/unexport
# directives are shell-agnostic (work under cmd.exe and sh alike).
export UV_NATIVE_TLS := true
unexport SSL_CERT_FILE
unexport REQUESTS_CA_BUNDLE

# --- paths / knobs ---
BACKEND_DIR  := backend
FRONTEND_DIR := frontend
DOCKER_DIR   := docker
PORT         ?= 8000
UV           := uv
COMPOSE      := docker compose

.PHONY: help infra up down logs ps backend-setup migrate backend worker watch \
        chat delegate ingest search approvals runs frontend frontend-build \
        test clean prune

help:  ## show this help
	@echo "Personal AI Project Assistant — targets:"
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sed 's/##//'

# --- infrastructure (Postgres :5433, Qdrant :6333, draw.io :8080) ---
infra up:  ## start Postgres + Qdrant + draw.io containers
	cd $(DOCKER_DIR) && $(COMPOSE) up -d

down:  ## stop containers (keep volumes)
	cd $(DOCKER_DIR) && $(COMPOSE) down

logs:  ## tail container logs
	cd $(DOCKER_DIR) && $(COMPOSE) logs -f --tail=100

ps:  ## show container status
	cd $(DOCKER_DIR) && $(COMPOSE) ps

# --- backend ---
backend-setup:  ## uv sync (backend deps)
	cd $(BACKEND_DIR) && $(UV) sync

migrate:  ## alembic upgrade head (also runs on first setup)
	cd $(BACKEND_DIR) && $(UV) run alembic upgrade head

backend:  ## run the FastAPI API for the web UI (Windows needs the Selector loop)
	cd $(BACKEND_DIR) && $(UV) run uvicorn assistant.api.app:app \
	    --port $(PORT) --loop asyncio:SelectorEventLoop --reload

worker:  ## run the Procrastinate job worker (delegation + ingestion queues)
	cd $(BACKEND_DIR) && $(UV) run assistant worker

watch:  ## watch ASSISTANT_VAULT_PATH and auto-ingest changed markdown
	cd $(BACKEND_DIR) && $(UV) run assistant watch

# --- CLI usage ---
chat:  ## interactive orchestrator chat (optional PROJECT=/THREAD=)
	cd $(BACKEND_DIR) && $(UV) run assistant chat $(if $(PROJECT),--project $(PROJECT),) $(if $(THREAD),--thread $(THREAD),)

delegate:  ## delegate a coding task: make delegate TASK=.. REPO=.. [TEAMS=1] [CONSTRAINT="a b"] [CRITERIA="x y"]
	cd $(BACKEND_DIR) && $(UV) run assistant delegate "$(TASK)" --repo $(REPO) \
	    $(if $(TEAMS),--teams,) $(foreach c,$(CONSTRAINT),-c $(c)) $(foreach a,$(CRITERIA),-a $(a))

ingest:  ## ingest a path into the KB: make ingest PATH=.. [PROJECT=..]
	cd $(BACKEND_DIR) && $(UV) run assistant ingest $(PATH) $(if $(PROJECT),--project $(PROJECT),)

search:  ## hybrid KB search: make search QUERY=.. [PROJECT=..]
	cd $(BACKEND_DIR) && $(UV) run assistant search "$(QUERY)" $(if $(PROJECT),--project $(PROJECT),)

approvals:  ## show the milestone approval log
	cd $(BACKEND_DIR) && $(UV) run assistant approvals

runs:  ## show recent delegated CC runs
	cd $(BACKEND_DIR) && $(UV) run assistant runs list

# --- frontend ---
frontend:  ## run the React dev server (http://localhost:5173)
	cd $(FRONTEND_DIR) && npm run dev

frontend-build:  ## production build the frontend
	cd $(FRONTEND_DIR) && npm run build

# --- quality ---
test:  ## backend pytest suite
	cd $(BACKEND_DIR) && $(UV) run pytest -q

# --- teardown ---
clean:  ## stop containers and remove their volumes (DESTRUCTIVE)
	cd $(DOCKER_DIR) && $(COMPOSE) down -v

prune: clean  ## clean + drop the Postgres/Qdrant data volumes
	$(COMPOSE) volume rm -f assistant_pg_data_v17 assistant_qdrant_data || true