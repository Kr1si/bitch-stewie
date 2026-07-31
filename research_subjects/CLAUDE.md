# Netherbrain — Claude Code Instructions

Self-hosted knowledge platform ("library for companies"): agents/humans submit skills, guides, workflows; a librarian agent processes them; humans review via git PRs; approved knowledge is indexed and served to every agent via MCP.

**Read first**: `ARCHITECTURE.md` (system design, the 13 LangGraph rules, typing enforcement, testing strategy) and `MASTER_PLAN.md` (phases + definitions of done). **Every folder has a `plan.md`** — read the plan.md of any folder before working in it; it defines purpose, contracts, tests, and the dev workflow for that folder.

## Hard rules (non-negotiable)

1. **TDD is mandatory** — red-green-refactor for every feature and bugfix (`/tdd`, `ecc:tdd-guide`): failing test first, then implementation, then refactor.
2. **Typing**: mypy strict, no `Any` / bare `dict` / `dict[str, Any]`; every boundary shape is a Pydantic model; every tool has a docstring + explicit Pydantic `args_schema`. FE: TS strict + zod at API boundaries.
3. **The 13 LangGraph rules** in ARCHITECTURE.md apply to all graph/agent/tool code (deterministic-first, Command flow-hijacking, Send parallelism, async everywhere, idempotent pre-interrupt side effects, cognitive firewall at entry points).
4. **DDD import rules**: domain → shared_kernel only; application → domain; infrastructure implements domain ports; interface → application. Never cross context internals.
5. **Consult skills before designing/implementing** anything they cover; use deep research / web search for anything outside them — never answer from memory.
6. **Modularity (rule 14)**: single responsibility per file — size caps CI-enforced (`scripts/check_file_sizes.py`: code 400 / tests 600 / md 1000). Workflows split nodes by category (`nodes/agents|deterministic|routing`, one node per file) with prompts in XML-tagged prompt modules; one tool per file; per-resource routers; FE slice folders. See ARCHITECTURE.md §Modularity.
7. **Skillify**: whenever you figure out something non-obvious or solve a new class of problem, capture it immediately — `/ecc:learn` or create/update a skill in `.claude/skills/` (`skill-creator` / `write-a-skill`). This project's dev process dogfoods its own product philosophy.

## Pre-commit gates (in order, all mandatory)

1. `make check` (ruff + mypy strict + unit tests)
2. Language reviewer agent on touched code: `ecc:python-reviewer` / `ecc:react-reviewer` / `ecc:database-reviewer` (SQL/migrations)
3. `/ecc:quality-gate`
4. If auth, tokens, MCP surface, or user-input handling was touched: `/ecc:security-scan` (`ecc:security-reviewer`)

## Command playbook

| Situation | Use |
|---|---|
| Starting agent/graph/RAG work | `framework-selection` first, then `langgraph-fundamentals` / `langgraph-persistence` / `langgraph-human-in-the-loop` / `langchain-middleware` / `deep-agents-*` / `langchain-rag` as applicable |
| Planning a feature | `/ecc:plan` or `/ecc:feature-dev`; `ecc:architect` / `ecc:planner` for design input |
| Implementing (always) | `/tdd` red-green-refactor; `ecc:tdd-guide` |
| Build/type errors | `/ecc:build-fix`; `ecc:build-error-resolver`, `ecc:react-build-resolver` |
| DB schema, queries, migrations | `postgres-best-practices`, `ecc:database-reviewer` |
| Vector/RAG work | `qdrant-*` skills (search-quality, performance, scaling), `langchain-rag` |
| MCP surface | `ecc:mcp-server-patterns` |
| FastAPI work | `ecc:fastapi-patterns`, `ecc:fastapi-reviewer` |
| FE work | `ecc:react-patterns`, `vercel-react-best-practices`, `ecc:react-reviewer`, `web-design-guidelines` |
| Pre-commit | `make check` → reviewer agent → `/ecc:quality-gate` (+ `/ecc:security-scan` on sensitive code) |
| Docs upkeep | `/ecc:update-docs`, `/ecc:update-codemaps` (`ecc:doc-updater`) |
| Learned something new | **skillify**: `/ecc:learn`, `skill-creator` / `write-a-skill` |
| Unknowns outside skills | `deep-research` / web search / `ecc:docs-lookup` (context7) |
| Session end / handoff | `/ecc:save-session`, `/handoff`, `/ecc:checkpoint` |

Project skills in `.claude/skills/`: `netherbrain-conventions` (the 13 rules + typing, loadable), `netherbrain-workflow-authoring` (how to add a LangGraph workflow here), `netherbrain-testing` (fake gateway, graph tests, testcontainers). Load them when working on graphs, workflows, or tests.

## Commands (once Phase 0 lands)

- `make up` / `make down` — compose stack (api, worker, postgres, qdrant, tei, gitea, langfuse)
- `make migrate` / `make seed` — alembic migrations / seed users+tokens
- `make check` — ruff + mypy strict + unit tests (the floor for any commit)
- `make test-integration` / `make e2e` — testcontainers suite / full capture-loop E2E
- `nx serve netherbrain-web` — FE dev server

## Repo map

- `backend/src/netherbrain/` — DDD: `shared_kernel`, `platform/{config,db,queue,llm,telemetry}`, `contexts/{identity,knowledge,ingestion,retrieval,agents}` each with `domain/application/infrastructure/interface`
- `frontend/` — Nx: `apps/netherbrain-web`, `libs/{ui,auth,data-access,feature-review,feature-admin,feature-chat}`
- `bundle_spec/` — knowledge bundle format spec + validator
- `deploy/` — compose stack; `docs/` — prose docs
