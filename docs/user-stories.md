# bitch-stewie — User Stories

> A personal AI assistant for a System Architect. An orchestrator (LangGraph
> `deepagents`) coordinates architecture work — diagrams, documentation,
> research, and delegated coding — across projects. Coding is delegated to
> Claude Code instances. Every feature below is scoped to a project and tested
> against the acceptance criteria in `## Acceptance criteria & test coverage`.

**Default LLM:** LongCat (`LongCat-2.0` over the Anthropic Messages API) backs
both the orchestrator/planner and the delegated CC worker. This is the default
in `config.py`, `docker-compose.prod.yml`, and `docker/.env.example`. (Ollama
stays in the stack for `bge-m3` embeddings only.)

---

## Story 1 — Ask the orchestrator anything (chat)
**As an** architect, **I want** to chat with the orchestrator about a project
and get answers grounded in that project's decisions, KB, and examples.

**Acceptance criteria**
- `POST /api/chat/stream` streams `token`/`tool`/`interrupt`/`done` SSE events.
- Threads are persisted (`GET /api/chat/sessions`, `.../{id}/messages`).
- A new thread starts with "+ New thread"; history loads on click.
- The orchestrator has `search_knowledge`, `record_decision`, `list_decisions`,
  `update_diagrams`, `export_document`, `write_plan`, `list_plans`,
  `list_examples`, `read_example`, `set_preference`, `delegate_coding_task`.
- **Tests:** `test_chat.py` — SSE event sequence, thread create/load, tool
  dispatch with a mocked model.

## Story 2 — Delegate a coding task (milestone gate)
**As an** architect, **I want** the orchestrator to implement code on a branch,
self-review it, and hand me a structured result — stopping for my approval
before any side effects.

**Acceptance criteria**
- `delegate_coding_task` is the only interrupt-gated tool (`interrupt_on`).
- Approving calls `POST /api/chat/resume/stream`; the graph resumes.
- The CC worker stages skills, drives the prompt, runs `/code-review` (up to
  `cc_max_review_iterations`), parses `REVIEW_VERDICT: clean|issues`, and the
  `ASSISTANT_RESULT_JSON` marker for branch/commits/tests/summary.
- Run status flips `running` → `succeeded`/`failed`; events are persisted.
- **Tests:** `test_delegate.py` — gate→resume flow with mocked CC worker;
  `Brief.to_prompt`, `fallback_working_agreement`, result parsing, review loop.

## Story 3 — Refine a plan, then hand off
**As an** architect, **I want** a dedicated planner conversation that shapes a
rough idea into a precise plan (research / coding / design), then hands the
plan file to the orchestrator as a new session.

**Acceptance criteria**
- `POST /api/plan/stream` streams the planner; focus tag prepended to messages.
- `POST /api/plan/handoff` reads the newest plan file, returns an orchestrator
  thread id; UI shows success/error.
- Plans persisted under `plans/YYYY-MM-DD-<slug>.md` with frontmatter status.
- **Tests:** `test_plan.py` — planner SSE, focus tagging, handoff returns a
  thread id and consumes a real plan file.

## Story 4 — Search and grow the knowledge base
**As an** architect, **I want** to ingest docs into a project-scoped KB and
search them with hybrid (dense + sparse) retrieval.

**Acceptance criteria**
- `POST /api/knowledge/ingest-text` and `/ingest-path`; collections listed via
  `GET /api/knowledge/collections`; per-source counts; `POST /api/knowledge/search`.
- Deterministic chunk ids (sha256) — re-ingesting overwrites, no dupes.
- Deep-research reports auto-ingest; nightly job ingests yesterday's chats.
- **Tests:** `test_knowledge.py` — ingest→search returns the expected hit;
  collection/stats shapes. (Integration: needs Qdrant + Ollama bge-m3.)

## Story 5 — Deep research
**As an** architect, **I want** a long, cited web research report run by Claude
Code, streamed to the UI, then saved to the KB.

**Acceptance criteria**
- `POST /api/research/deep/stream` emits `start`→`done`/`error` over SSE.
- AbortController cancels the run; report renders monospace; copy-to-clipboard.
- Report auto-ingests into the KB (kind `research`).
- **Tests:** `test_deep_research.py` — SSE `start`→`done` with mocked worker;
  report content echoed in `done` data.

## Story 6 — View and evolve diagrams
**As an** architect, **I want** to view a project's `.drawio` diagrams (generated
from the LikeC4 model) in an embedded editor, and ask the architect chat to
regenerate them.

**Acceptance criteria**
- `GET /api/projects/{id}/diagrams` lists; `GET /.../{name}` returns raw XML.
- Path-traversal is guarded (no `..` escape out of the diagrams dir).
- Architect chat `update_diagrams` regenerates exports; live refresh on done.
- **Tests:** `test_diagrams.py` — list + fetch XML; traversal attempt returns 400/404.

## Story 7 — Upload reference examples
**As an** architect, **I want** to upload reference diagrams/docs so delegated
sessions mimic their style, and browse/delete them.

**Acceptance criteria**
- `POST /api/examples` (FormData), `GET /api/examples` (filter project/kind),
  `GET /api/examples/{id}/content`, `DELETE /api/examples/{id}`.
- Missing file on disk returns 410.
- **Tests:** `test_examples.py` — upload→list→download→delete roundtrip; 410 path.

## Story 8 — Monitor delegated runs
**As an** architect, **I want** to start a run, watch its status poll, and
inspect per-agent event lanes (main + subagents, tool pairing, narration).

**Acceptance criteria**
- `POST /api/cc-runs` (202), `GET /api/cc-runs`, `GET /api/cc-runs/{id}/events`.
- `groupEvents()` groups raw events into lanes via a subagent scope stack;
  pairs `pre_tool`/`post_tool`; computes `laneDuration`.
- `GET /api/runs/{id}/statusline` exposes telemetry (events/elapsed/verdict).
- **Tests:** `test_runs.py` — start→list→events; `test_events_grouping.py` —
  `groupEvents()` lane stack, pairing, duration (pure unit).

## Story 9 — Projects, decisions, preferences
**As an** architect, **I want** a project registry with an decision log and
stored preferences/conventions that both the orchestrator and CC sessions see.

**Acceptance criteria**
- `GET/POST /api/projects` (409 on dup), `GET /api/projects/{id}/decisions`,
  `GET /api/approvals` (filter `?status=`).
- The `assistant-memory` MCP server surfaces projects/decisions/preferences/
  conventions/examples/KB to CC sessions; decisions also append to
  `.claude/rules/*.md` when `write_project_rules` is on.
- **Tests:** `test_projects.py` — roundtrip + 409; `test_mcp_memory.py` — the 8
  MCP tools are registered and callable.

## Story 10 — Config & observability
**As an** operator, **I want** the default LLM to be LongCat, overridable per
env, with LangSmith tracing toggleable, and a health/dashboard endpoint.

**Acceptance criteria**
- `Settings().default_model == "anthropic:LongCat-2.0"`; compose defaults
  `ASSISTANT_CC_*` and `ANTHROPIC_BASE_URL`/`ANTHROPIC_API_KEY` to LongCat.
- `GET /health` reports liveness + active model + LangSmith status.
- `GET /api/stats` returns dashboard aggregates.
- `langsmith_enabled()` requires key + `tracing=true`; `apply_langsmith_env()`
  pushes into `os.environ` idempotently.
- **Tests:** `test_config.py` — LongCat default, langsmith env push/guard;
  `test_health.py` — already covers `/health`; `test_stats.py` — aggregates shape.

---

## Out of scope (documented gaps, not under test)
Post-impl human review gate, MR/PR creation, test gating, and the self-rewrite
loop are Phase 1 work (see `docs/findings/2026-07-10.md` §4-5) and not yet built.
