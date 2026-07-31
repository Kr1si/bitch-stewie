# Handdown: RULES_AND_GUIDELINES.md compliance refactor

> **Branch:** `refactor/ddd-layering-and-strict-typing`
> **Date:** 2026-08-01
> **Status:** In progress — ruff clean, layer relocation done, import-linter contract has 1 known blocker, mypy strict not yet green.

## Goal

Bring the `backend/` Python codebase into compliance with
`RULES_AND_GUIDELINES.md` (ruff + mypy strict, Pydantic boundaries, one-tool-per-file,
LangGraph package layout, DDD/layered architecture, file-size caps, fake-LLM testing).
The user scoped this pass to: **foundation tooling + full DDD relayering with hexagonal
enforcement**. Testing overhaul, tool splitting, LangGraph package layout, and
observability are explicitly deferred to later passes.

## Decisions made (confirmed with user)

1. **No domain layer.** The codebase is a thin LangGraph/Claude-Code orchestration app —
   every "pure" module is either an external-system adapter (infrastructure) or a Pydantic
   DTO. Forcing a 4th `domain/` layer would mean manufacturing fake objects. Adapted to
   **3 layers + shared kernel**: `interface -> application -> infrastructure -> shared`.
2. **Hexagonal enforcement (user chose "full").** Interface must ONLY ever call
   `application` (services), never `infrastructure` directly. Enforced via import-linter
   `layers` contract.
3. **MCP server placement.** `memory_mcp.py` moved to `interface/mcp/` (it's an inbound
   interface — Claude Code calls into it).

## What's done (committed)

### Commit `d641c64` — lint/type tooling + ruff clean
- `backend/pyproject.toml`: ruff select-list + per-file-ignores; mypy strict config with
  `ignore_missing_imports` overrides for `deepagents.*`, `procrastinate.*`, `fastembed.*`;
  import-linter root config; added `mypy` + `import-linter` to dev deps.
- `Makefile`: `lint`, `typecheck`, `sizes`, `import-linter`, `check` targets
  (`check` = lint + mypy + sizes + tests).
- `backend/scripts/check_file_sizes.py`: enforces src<=400, test<=600, md<=1000
  (migrations exempt). **Passing.**
- Cleared all ruff violations across the codebase (return types, arg types, line length,
  `str+Enum` -> `StrEnum`). **ruff is green: `All checks passed!`**

### Commit `2756726` — DDD layer relocation (pure move, no logic changes)
- `backend/scripts/reorg_ddd.py`: the migration script (git mv + regex import rewrite).
- Relocated every module into `shared/` / `application/orchestrator/` / `infrastructure/` /
  `interface/{api,cli,mcp}/`. Created all 14 missing `__init__.py` files.
- Rewrote all internal import paths.
- Created 4 application-service facades in `application/services/`:
  - `memory_service.py` — re-exports `get_session_factory`, `get_sync_session_factory`, and
    ORM models (Session, Message, Approval, etc.).
  - `knowledge_service.py` — re-exports `ingest_path`, `ingest_text`, `hybrid_search`,
    `list_collections`, `collection_stats`.
  - `jobs_service.py` — re-exports `job_app`, `delegate_brief`, `watch_vault`, `Brief`,
    `DelegationRunner`.
  - `orchestrator_service.py` — re-exports `build_orchestrator`, `build_planner`.
- Dispatched 2 parallel subagents that rewrote all `interface/api/*.py` (9 files) and
  `interface/cli/*.py` + `interface/mcp/memory_mcp.py` to import from the service facades
  instead of infrastructure directly. Both verified clean.

## Current state (uncommitted)

```
ruff:          All checks passed!
import-linter: BROKEN (1 violation) — see Blocker below
mypy strict:   126 errors in 29 files (not yet addressed)
tests:         1 pass, 6 pre-existing infra failures (Postgres/Qdrant not running locally)
```

Working tree additionally has uncommitted edits to `interface/api/*.py`,
`interface/cli/*.py`, `interface/mcp/*.py` (the service-facade import rewrites) and the new
`application/services/` package — these are **not yet staged/committed**.

## The blocker

import-linter `layers` contract reports one illegal upward dependency:

```
assistant.infrastructure is not allowed to import assistant.interface:
- assistant.infrastructure.cc_bridge.runner -> assistant.interface.mcp.memory_mcp (l.34)
```

`infrastructure/cc_bridge/runner.py:34` does
`from assistant.interface.mcp.memory_mcp import build_memory_server` (used at l.214 to
build the MCP server config passed to spawned CC sessions).

**Fix options** (not yet implemented — pick one):
- **A. Move `build_memory_server()` to `application/services/`.** It's a composition concern
  (wires the MCP tools into a server config). Then `runner` (infra) imports it from
  application — but infra->application is *also* upward, so this alone doesn't fix it.
- **B. Move `build_memory_server()` to `infrastructure/`.** The runner stays infra->infra.
  But the function references the `@tool` handlers defined in `memory_mcp.py` (interface),
  so you'd also have to move or re-import those tools — risks a new infra->interface edge.
- **C. Dependency inversion (cleanest, more work).** Define the MCP-server factory as a
  callable/protocol in `application/`, have the interface layer register the concrete
  builder, and pass it into the runner via its constructor instead of a direct import.
  Removes the import edge entirely.
- **D. Make `runner.py` itself application-layer.** It orchestrates a CC delegation run,
  which is arguably a use-case, not infra. Then `runner` (app) importing
  `build_memory_server` (interface) is app->interface = still upward. Doesn't fix alone.

The combination that works cleanly: keep `build_memory_server` in `interface/mcp/`, and
inject it into the runner (option C) — or accept a narrow `ignore_imports` exception in the
import-linter contract for this one infra->interface edge if the user decides the runner is
special. **Confirm direction with the user before implementing.**

## Layout (post-reorg)

```
src/assistant/
  shared/config.py                         # shared kernel (pydantic-settings only)
  application/
    services/                              # NEW: facades (interface calls these)
      memory_service.py  knowledge_service.py  jobs_service.py  orchestrator_service.py
    orchestrator/                          # orchestration internals (unchanged logic)
      artifact_tools.py  context.py  example_tools.py  factory.py
      planner.py  research_tools.py  tools.py
  infrastructure/                         # external-system adapters
    memory/{db,models,sync_db}.py  rag/{ingest,store}.py
    cc_bridge/{brief,lifecycle_hooks,runner,subagents,worker}.py
    jobs/{queue,watcher}.py  diagrams/likec4.py  docs_gen/pandoc.py
  interface/                               # inbound adapters
    api/{app,chat,diagrams,examples,knowledge,plan,research,routers,stats,statusline,util}.py
    cli/{chat,main}.py
    mcp/memory_mcp.py
  agents/                                  # empty placeholder __init__.py only; leave as-is
```

## Commands to verify from `backend/`

```bash
uv run ruff check src tests          # lint (green)
uv run mypy                          # typecheck (126 errors remaining)
uv run python scripts/check_file_sizes.py   # size caps (green)
uv run import-linter lint --no-cache # layer contracts (1 blocker)
uv run pytest tests/test_health.py -q       # smoke test (passes; other tests need Postgres/Qdrant)
```

Note: import-linter reads a cache at `backend/.import_linter_cache/`; pass `--no-cache`
(or delete the dir) after any import change to avoid stale results.

## Remaining work (suggested order)

1. **Resolve the import-linter blocker** (runner -> memory_mcp) — confirm fix direction with
   user first.
2. **Commit** the service facades + interface import rewrites (the uncommitted working-tree
   changes). This is a clean checkpoint: "introduce application services + rewrite
   interface."
3. **Get mypy strict green** (126 errors). Mostly `Missing type arguments for generic type
   "dict"` and a few `no-untyped-def` / `type-arg` — mechanical. The reorg changed many
   import paths, so re-baseline mypy after the interface-rewrite commit.
4. **Wire import-linter into `make check`** (add it as a dependency of the `check` target).
5. Final verification: full `make check` green, package imports, health test.

## Explicitly deferred (out of this pass)

- One-tool-per-file + central registry (§4)
- LangGraph state/graph/nodes package layout (§5)
- Fake-LLM-gateway test rewrite (§9)
- Observability / structured-logging tracing (§11)
- Pre-commit hook wiring (§10)

## Notes & gotchas

- `backend/pyproject.toml` mypy overrides: `deepagents.*`, `procrastinate.*`,
  `fastembed.*` have `ignore_missing_imports = true`. Add other untyped third-party deps
  here as mypy surfaces them (e.g. `claude_agent_sdk`, `langchain.*`, `langgraph.*`,
  `sse_starlette`, `qdrant_client`).
- `tests/` has no subdirectories and effectively no suite — flag as a real gap.
- The `.env.example` / `docker/.env.example` / `docs/command-library.md` modifications
   are PRE-EXISTING unrelated work (LongCat provider additions) — left uncommitted, do not
   bundle into this refactor's commits.
- `CLAUDE.md` was edited externally (graphify/ruflo sections added) — not part of this work.
- Alembic migrations are EXEMPT from the source size cap.
