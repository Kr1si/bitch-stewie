# Netherbrain — Architecture

Netherbrain is a self-hosted "library for companies": agents and humans deposit skills, guides, workflows, and docs; a **librarian agent** processes and categorizes them; humans review via git PRs; approved knowledge is indexed and retrievable by every agent in the org through MCP.

The flywheel: an agent fixes an issue → submits the learning → librarian normalizes it → human approves the PR → indexed → available org-wide.

> **Working rule for anyone (human or LLM) building this project**: consult the installed skills before designing or implementing anything they cover — `framework-selection` first, then `langgraph-*` / `deep-agents-*` / `langchain-rag` for agent work, `qdrant-*` for vectors, `postgres-best-practices` for schema/queries, `ecc:mcp-server-patterns` for the MCP surface. For anything outside skill coverage (library versions, API changes), use deep research / web search — never answer from memory. See `CLAUDE.md` for the full command playbook.

## System overview

```
                        ┌─────────────────────────────────────────────┐
 Client agents          │               NETHERBRAIN                   │
 (Claude Code, CI       │                                             │
 hooks, MCP clients) ─► │  api: FastAPI + MCP (streamable HTTP)       │
 w/ user token          │   ├─ auth middleware (token→user→roles)     │
                        │   ├─ MCP tools (search/fetch/submit/status) │
 netherbrain-web ────►  │   └─ webhook receiver (PR merged)           │
 (Nx React: review,     │                                             │
 admin, chat later)     │  worker: LangGraph pipelines + agents       │
                        │   └─ jobs via Postgres queue (SKIP LOCKED)  │
 Humans ─────────────►  │                                             │
 (git PRs)              │  Postgres ── Qdrant ── TEI (embeddings)     │
                        └───────┬────────────────────┬────────────────┘
                                │                    │
                     Customer git host        Customer LLM endpoint
                     (GitHub/GitLab; Gitea    (Anthropic/OpenAI/vLLM…)
                     bundled for local dev)
```

Core decisions:

| Topic | Decision |
|---|---|
| Backend | Python (FastAPI, MCP Python SDK, LangGraph), DDD with 5 bounded contexts, uv-managed |
| Frontend | Nx workspace (FE only): one shell app `netherbrain-web` + feature libs |
| LLM | BYO endpoint — provider-agnostic gateway (Anthropic/OpenAI/Azure/vLLM via config) |
| Embeddings | BYO OpenAI-compatible endpoint; bundled local default (TEI container) |
| Storage | Postgres (metadata, users, jobs, checkpoints, audit) + Qdrant (vectors) |
| Source of truth | Git repo on the customer's git host; review = PR merge (Gitea bundled for dev) |
| Knowledge format | Multi-file bundles: directory with SKILL.md/GUIDE.md entry point + scripts/assets |
| Distribution | MCP search + fetch at task time, RBAC-filtered per token |
| Auth | Built-in API tokens + roles (admin, librarian, contributor, reader); OIDC-ready ports |
| Tenancy | Single-tenant per company deployment; Docker Compose + Makefile |

## Knowledge bundle format (git repo = source of truth)

```
knowledge/
  skills/<slug>/      SKILL.md + scripts/, assets/, anything
  guides/<slug>/      GUIDE.md (+ files)
  workflows/<slug>/   WORKFLOW.md (+ files)
  wikis/<project>/    pages…
```

Entry-point markdown carries YAML frontmatter (`name, description, type, tags, version, owners, visibility`), compatible with the agent-skills convention. The entry markdown is chunked/embedded for search; bundle files are listed in metadata and fetched on demand via MCP (progressive disclosure — agents read the entry doc first, pull scripts as needed).

## Data model (Postgres, high level)

- `users`, `api_tokens` (hashed, scoped, expiring) — roles: `admin | librarian | contributor | reader`
- `submissions` — status machine: `received → processing → pr_open → merged → indexed` (or `rejected | failed`)
- `artifacts`, `artifact_files` — indexed knowledge + bundle file manifests (repo_path, commit_sha, tags, visibility)
- `jobs` — Postgres queue (`FOR UPDATE SKIP LOCKED`)
- LangGraph checkpoint tables (`PostgresSaver`, `.setup()` at deploy time, never at app startup)
- `audit_log`

## Qdrant

One `knowledge` collection; payload: `artifact_id, type, tags, visibility, project, commit_sha`. RBAC is enforced at query time via payload filters derived from the caller's token. Retrieval sits behind a domain port so hybrid search/reranking can be added without touching callers.

---

# DDD structure — 5 bounded contexts

Each context has four layers:

- `domain` — entities, value objects, domain services, **ports** (repository/adapter interfaces). Imports nothing app-specific.
- `application` — use cases, DTOs, pipelines/graphs. Imports `domain`.
- `infrastructure` — adapter implementations (db, qdrant, git, http). Implements `domain` ports.
- `interface` — FastAPI routers, MCP tool definitions, CLI. Imports `application`.

**Import rules** (identical everywhere; enforced by import-linter in Phase 0): `domain → shared_kernel` only; `application → domain`; `infrastructure → domain (ports)`; `interface → application`. Cross-context communication only through application services and domain events — never reach into another context's internals. `platform` may be imported by `infrastructure`/`interface` layers, never by `domain`.

| Context | Owns |
|---|---|
| **identity** | Users, tokens, roles, RBAC policy, auth middleware; OIDC port for later |
| **knowledge** | Artifacts, bundles, taxonomy, bundle-spec validator, git source-of-truth sync |
| **ingestion** | Submissions state machine, librarian LangGraph pipeline, PR proposal + merge webhook |
| **retrieval** | Chunking, embedding port (TEI/BYO), Qdrant store, search with RBAC filters |
| **agents** | Supervisor graph, cognitive firewall, tool registry, Deep Agents harness, workflows |

Shared: `shared_kernel` (base entity/VO/event types, Result types) and `platform` (config, db, queue, LLM gateway, telemetry).

---

# The 13 rules — LangGraph & agent conventions

Project rules, verified by tests/lint where possible. The `netherbrain-conventions` skill (`.claude/skills/`) carries the loadable version.

1. **Tools**: every tool is `@tool` with a docstring (first line = LLM-facing description) **and an explicit Pydantic `args_schema`**. All tools register in the `agents/tools` registry; a registry lint test fails CI if any tool lacks docstring or schema.
2. **State**: TypedDict schemas; nodes return **partial update dicts**, never mutate state; every list field gets a reducer (`add_messages` / `operator.add`) — no reducer means last-write-wins bugs, especially with `Send` fan-out.
3. **Flow hijacking**: routing via `Command[Literal[...]](update=…, goto=…)` to combine state update + routing in one node; `Send` for parallel fan-out; plain conditional edges for pure routing. Never combine a static edge and a `Command` goto from the same node unintentionally (both fire).
4. **Human gates**: `interrupt(payload)` with JSON-serializable payload; resume with `Command(resume=…)` on the same `thread_id`. All side effects before an `interrupt` must be **idempotent** (upserts, check-before-create) because the node re-runs from the top on resume. The librarian's PR-wait is a durable interrupt resumed by the merge webhook.
5. **Persistence**: `PostgresSaver` (setup at deploy); thread-id conventions: `submission:<id>`, `chat:<user>:<session>`, `workflow:<kind>:<id>`. Subgraph checkpointer scoping: `checkpointer=False` for pure deterministic pipelines, default (`None`) for interrupt-capable workflow subgraphs, `True` only for stateful conversational subagents (never invoked in parallel with itself).
6. **Errors (4-tier)**: transient → `RetryPolicy` on the node; LLM-recoverable → `ToolNode(handle_tool_errors=True)`; user-fixable → `interrupt`; unexpected → raise and let the job runner mark the submission `failed`.
7. **Streaming**: `messages` mode for chat token streaming to the FE; `custom` mode (`get_stream_writer`) for pipeline progress events surfaced to submission status.
8. **Layer rubric** (framework-selection): needs planning/files/subagents/skills → **Deep Agents** (doc-writer, wiki agent); needs owned control flow/loops/HITL → **custom StateGraph** (supervisor, librarian); single-purpose tool loop → **create_agent ReAct** (allowed inside workflows); no agent loop → plain chain/pipeline.

## Deterministic-first workflow philosophy (precision over speed; speed via parallelism)

9. **Deterministic code nodes wherever possible.** Anything expressible as code (validation, parsing, diffing, git ops, indexing, routing on known state) is a plain typed Python node — the LLM is used only to **fill parameters** (extraction, classification, drafting), always via **structured output into a Pydantic model**, never free-text parsing. LLM loops (ReAct) only where absolutely necessary, always with a bounded iteration cap; prefer single-shot structured-output nodes.
10. **Context hygiene — not everything returns to the LLM.** Large tool payloads use `response_format="content_and_artifact"`: a short summary goes to the model as ToolMessage content, the full payload lands in state as the artifact. Tools and nodes may return `Command(update=…, goto=…)` to write results straight into internal state and redirect flow without polluting message history. State carries the real data; messages carry only what the model needs to decide.
11. **Parallel by default.** Heavy `Send` fan-out/fan-in inside workflows (per-file validation, per-chunk embedding, per-artifact dedupe), with reducers aggregating results. Independent graph branches run concurrently.
12. **Async everywhere.** All nodes and tools are `async def`; IO through async clients (httpx, SQLAlchemy async/asyncpg, qdrant async client); independent IO calls gathered with `asyncio.gather`. No sync IO in the request or worker path.
13. **Cognitive firewall at every entry point** (like Claude Code's gates). Before input reaches an expensive agent: (a) deterministic checks — auth/RBAC scope, payload schema validation, size/rate limits, garbage and prompt-injection heuristics; (b) a small/fast LLM classifier with structured output (`verdict: allow | reject | clarify`, typed reason). Rejections short-circuit with `Command(goto=END, update={rejection message})` — the supervisor/pipeline is never invoked. Applied to librarian intake (Phase 1) and chat supervisor entry (Phase 3). Lives in `agents/application/firewall` as a reusable subgraph compiled with `checkpointer=False`.

## Modularity & SRP (rule 14 — CI-enforced)

14. **Single responsibility per file, everywhere.** Enforced by `scripts/check_file_sizes.py` in `make lint`: source files (.py/.ts/.tsx) ≤ 400 lines, tests ≤ 600, markdown ≤ 1000 (migrations exempt). Structure rules:
    - **Workflows/graphs**: each workflow is a package — `state.py` (state + typed contracts between node categories), `graph.py` (composition ONLY — no logic), `nodes/agents/` (LLM parameter-fill nodes, one per file), `nodes/deterministic/` (pure code nodes, one per file), `nodes/routing/` (conditional edges / Command routers, one per file), `prompts/` (one module per LLM node). Node categories interact only through the typed state contracts — no cross-imports between node modules.
    - **Prompts**: never inline in nodes. Prompt modules compose from **XML-tagged sections** (`<role>`, `<instructions>`, `<context>`, `<output_format>`) defined as importable constants in `prompts/sections.py` per workflow (shared sections in `agents/application/prompts_common.py`); builder functions assemble sections + state into messages.
    - **Tools**: one tool per file (`tools/<family>/<tool_name>.py` holding its args model + `@tool` + ToolMeta), family `__init__` re-exports.
    - **Interface layers**: per-resource routers (`interface/routes/{resource}.py`) composed in `routes/__init__.py`.
    - **FE feature libs**: slice folders — `components/` (one component per file + colocated test), `hooks/` (one per file), `api.ts`, `routes.tsx`, `index.ts` barrel.

---

# Typing enforcement (hard CI gates)

- **mypy strict** across the backend — `strict = true` plus `disallow_any_explicit`, `disallow_any_generics`, `warn_return_any`; pydantic mypy plugin enabled. `make typecheck` is part of the test suite; CI fails on any error. No `# type: ignore` without an error code and justification comment (ruff PGH003 enforces).
- **No untyped shapes**: no bare `dict`, `Any`, `dict[str, Any]`, or untyped kwargs in domain/application/interface code. Every boundary-crossing structure (API request/response, MCP tool args/results, job payloads, events, LLM gateway messages, config) is a **Pydantic model** (or fully-typed `TypedDict` where Pydantic is impractical).
- **LangGraph under strict typing**: state schemas are typed `TypedDict`s with `Annotated` reducers; node returns are typed partial-update `TypedDict`s (`total=False`) — never `dict`; routing nodes annotated `Command[Literal[...]]`; interrupt payloads and resume values are Pydantic models serialized to JSON.
- **ruff** lint + format: `ANN` (no untyped defs), `E/F/I/UP/B/SIM/PGH`; config in `pyproject.toml`.
- **Frontend**: TS `strict: true` + `noUncheckedIndexedAccess`; ESLint `@typescript-eslint` strict-type-checked; zod schemas at API boundaries mirroring backend Pydantic models.

# Testing strategy

- **Tools (heavy emphasis)**: per tool — schema validation tests (accepts valid, rejects invalid), behavior tests against fakes, error paths; registry-wide lint test for docstring + schema presence.
- **Graph nodes**: pure unit tests with constructed state; LLM nodes against a **fake gateway** (canned/recorded responses) — no live LLM in unit tests.
- **Compiled graphs**: invoke with `InMemorySaver`; assert routing paths (each `Command` branch), interrupt payload shape, resume behavior, idempotency of pre-interrupt side effects (resume twice, assert no duplicates).
- **Integration**: testcontainers for Postgres + Qdrant; gitops adapter against a Gitea container.
- **E2E (backend)**: compose stack; scripted MCP client runs the full capture loop (submit bundle → librarian PR in Gitea → merge → search finds it → file fetch) + RBAC denial cases.
- **FE**: vitest + Testing Library per lib; Playwright E2E for the review flow.
- **Type checking as testing**: `make check` = ruff + mypy strict + unit tests; runs locally and in CI before anything merges.

# Observability & agent introspection

- **Tracing, dual-backend via one abstraction**: all LLM calls, graph runs, and tool executions traced via LangChain callbacks/OTel. **LangSmith during development**; **Langfuse self-hosted bundled in the customer compose stack**. Backend selected by env config only — `platform/telemetry` owns the wiring; application code never references a specific backend.
- **Debug MCP toolset** (admin-token-gated) so coding agents can look inside the running app: `get_trace`, `search_traces`, `get_submission_state`, `get_thread_checkpoints`, `list_jobs`, `tail_errors`. Same docstring/schema rules as all tools. Lives in `agents/interface`.
- **Internal debugging agent** (custom StateGraph over the debug tools + trace API): answers "why did submission X fail / where did the graph route" — from chat and via MCP (Phase 3).
- Structured logging (structlog, JSON) with `submission_id`/`thread_id` correlation IDs matching trace IDs end-to-end.

# Where things live

See `MASTER_PLAN.md` for phases and the `plan.md` in every folder for that folder's purpose, contracts, tests, and dev workflow. Start any exploration at `backend/src/netherbrain/plan.md` and `frontend/plan.md`.
