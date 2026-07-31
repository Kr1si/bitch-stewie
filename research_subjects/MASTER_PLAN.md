# Netherbrain — Master Implementation Plan

Phases are sequential; a phase starts only when the previous phase's definition of done (DoD) is green. Every folder's `plan.md` maps its contents to these phases in its **Phase** section. Development method for all phases: **TDD mandatory** (red-green-refactor), pre-commit gates per `CLAUDE.md`.

## Step A — Plan tree & skeleton (this step)

Deliverables: directory skeleton, `plan.md` in every folder, `ARCHITECTURE.md`, this file, `CLAUDE.md`, `.claude/skills/` starter skills, comment-only `Makefile` placeholder. No implementation code.

**DoD**: every folder has a filled `plan.md` (template sections complete, no TBD); consistency between this file and folder plans; no code files.

## Phase 0 — Foundation

Everything needed so that Phase 1 development is pure feature work.

- `deploy/`: docker-compose stack — `api`, `worker`, `postgres`, `qdrant`, `tei` (embeddings), `gitea` (dev git host), `langfuse` (+ its deps). Dev override file with hot-reload mounts.
- `Makefile`: real targets — `up`, `down`, `migrate`, `seed`, `lint`, `typecheck`, `test`, `check` (= lint + typecheck + unit tests), `test-integration`, `e2e`, `logs`.
- `backend/`: uv project, `pyproject.toml` with ruff + mypy strict config (see ARCHITECTURE.md → Typing enforcement) wired from the first commit; import-linter contracts for DDD layer rules.
- `platform/`: typed Pydantic Settings config; SQLAlchemy async engine + alembic migrations; Postgres job queue (SKIP LOCKED) with typed payloads; LLM gateway (BYO endpoint, OpenAI-compatible + Anthropic adapters); telemetry wiring (LangSmith env for dev / Langfuse for the stack) live from the first LLM call.
- `identity` context: users/tokens/roles schema + migrations, token hashing, RBAC policy, FastAPI auth middleware, seed CLI (`make seed` creates admin/librarian/contributor/reader users + tokens).
- `frontend/`: Nx workspace actually generated (`nx serve netherbrain-web` runs), TS strict + ESLint strict-type-checked, auth stub against token endpoint.
- CI pipeline: `make check` + FE `nx affected -t lint,typecheck,test`.

**DoD**: `make up && make seed` works on a clean machine; `make check` green; `nx serve netherbrain-web` shows the shell; a scripted request with a seeded token passes auth middleware; a traced dummy LLM call appears in Langfuse (stack) and LangSmith (dev env).

## Phase 1 — Skill capture loop (headless MVP)

The core value loop, no UI.

- `bundle_spec/`: bundle format spec + validator (frontmatter schema per type, structural lint).
- `knowledge` context: artifact/bundle domain model, repo layout mapping, artifact metadata store; Gitea adapter (branch, commit, PR, merge-webhook parsing) behind the `GitHostPort`.
- `ingestion` context: submissions state machine; **librarian pipeline** (see `backend/src/netherbrain/contexts/ingestion/application/pipelines/librarian/plan.md` for node-level detail): intake firewall → validate (Send fan-out per file) → dedupe (vector similarity) → categorize → quality pass → PR proposal → durable interrupt → webhook resume → index handoff.
- `retrieval` context: chunker, embedding client (TEI/BYO), Qdrant store + `knowledge` collection, RBAC-filtered search.
- `agents` context: tool registry + Phase-1 MCP tools; firewall subgraph (deterministic checks + classifier).
- `interface`: MCP server (streamable HTTP) with `search_knowledge`, `get_artifact`, `get_artifact_file`, `submit_knowledge`, `get_submission_status` + REST mirrors; merge-webhook receiver.

**DoD**: `make e2e` green on a clean machine — scripted MCP client submits a multi-file bundle → librarian PR appears in Gitea → merge → search returns the artifact → bundle file fetch works; RBAC denial case (reader token cannot submit); junk submission rejected by firewall with reason. Unit coverage per folder plans; `make check` green.

## Phase 2 — Review console + admin

- `frontend/libs/feature-review`: pending queue, librarian diff/summary view, approve (= merge via API), edit-then-approve, reject with reason.
- `frontend/libs/feature-admin`: user + token management.
- `identity`: team-scoped visibility (beyond coarse roles).
- `knowledge`: GitHub + GitLab adapters hardened (same `GitHostPort`).
- `agents/interface`: **debug MCP toolset** (`get_trace`, `search_traces`, `get_submission_state`, `get_thread_checkpoints`, `list_jobs`, `tail_errors`) behind admin tokens.

**DoD**: Playwright E2E — review a pending submission in the browser end-to-end (approve + reject paths); GitHub adapter passes the same contract tests as Gitea; debug toolset returns real trace + checkpoint data for a completed submission.

## Phase 3 — Chat

- `agents/application/supervisor`: custom supervisor StateGraph — firewall entry, `Command`-routed intents, async tool invocation (retrieval tools, workflow dispatch, submission status), bounded loops only.
- Token streaming (`messages` mode) over SSE/WS to `frontend/libs/feature-chat`; progress events via `custom` stream mode.
- `retrieval`: hybrid search (dense + sparse), reranking, citations back to artifacts.
- **Internal debugging agent**: StateGraph over the debug toolset + trace API; reachable from chat and MCP.

**DoD**: chat session answers a knowledge question with citations, dispatches a workflow and reports its progress, and explains a failed submission using the debug agent; all streamed live to the FE.

## Phase 4 — File ingestion

- Upload endpoint (files/folders/archives); parsing pipeline (docling/unstructured) as ingestion workflows; auto-categorization by librarian into the standard taxonomy; same PR review gate for generated guides/wikis.

**DoD**: PDF + docx + repo archive each land as reviewed, indexed, searchable artifacts through the normal loop.

## Phase 5 — Specialist agents

- Doc-writer agent and code-wiki agent as **Deep Agents** (todo/filesystem/subagent middleware, skills directory), emitting PRs through the same review gate.
- Repo push webhooks keep `wikis/<project>/` fresh.

**DoD**: pointing Netherbrain at a sample repo produces a reviewed wiki; a raw submission is upgraded into a polished guide by the doc-writer, PR-reviewed and indexed.

## Phase 6 — Enterprise hardening

- OIDC/SSO (Keycloak/Okta/Entra) via the identity OIDC port; coding-agent controllers exposed as chat tools; Helm chart; full OTel trace propagation MCP → graphs → LLM; skill-sync client (install approved skills into local agent skill dirs).

**DoD**: login via a Keycloak test realm; helm install on a test cluster; a Claude Code session installs an approved skill bundle locally via the sync client.

---

## Cross-reference index (phase → primary folder plans)

| Phase | Primary plan.md files |
|---|---|
| 0 | `deploy/`, `backend/`, `backend/src/netherbrain/platform/*`, `contexts/identity/*`, `frontend/` |
| 1 | `bundle_spec/`, `contexts/knowledge/*`, `contexts/ingestion/*` (incl. `pipelines/librarian`), `contexts/retrieval/*`, `contexts/agents/tools`, `contexts/agents/application/firewall`, `contexts/agents/interface` |
| 2 | `frontend/libs/feature-review`, `frontend/libs/feature-admin`, `contexts/knowledge/infrastructure/git`, `contexts/agents/interface` (debug toolset) |
| 3 | `contexts/agents/application/supervisor`, `frontend/libs/feature-chat`, `contexts/retrieval/*` (hybrid) |
| 4 | `contexts/ingestion/*` (upload workflows) |
| 5 | `contexts/agents/application/workflows` (Deep Agents workers) |
| 6 | `contexts/identity/*` (OIDC), `deploy/` (Helm), `contexts/agents/*` (controllers, sync) |
