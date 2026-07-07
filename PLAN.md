# Personal AI Project Assistant — Implementation Plan

## Context

Martin is a System Architect who needs a personal agentic system for his three core activities: drawing architecture diagrams (draw.io), writing documentation, and writing/reviewing code. The system is an **orchestration layer** built with LangChain + LangGraph + Deep Agents that delegates heavy coding work to **Claude Code instances running on GLM 5.2 via Ollama** (`ollama launch claude` / Anthropic-compatible API). It runs in Docker Compose with Postgres (unified memory) and Qdrant (RAG), served by a FastAPI backend with a React web UI and a CLI.

Scope was defined over 3 rounds of discovery (30 questions) + a confirmed recap. **V1 priority: the Claude Code orchestration loop via CLI** — everything else builds on that.

## Research Findings (verified 2026-07-07)

| Claim | Verdict | Notes |
|---|---|---|
| Claude Code on GLM 5.2 via Ollama | ✅ | Ollama v0.15+ `ollama launch claude`; Anthropic-compatible API at `http://localhost:11434`; works with any Ollama model incl. `glm-5.2:cloud`. Set context length ≥64k in Ollama settings. |
| GLM 5.2 on Ollama Cloud | ✅ | 744B MoE (~40B active), 1M context, MIT license, `glm-5.2:cloud` tag routes to Z.ai inference. |
| Programmatic spawn via Agent SDK | ✅ | `claude-agent-sdk` (Python) wraps the CLI; `ClaudeAgentOptions(env={...})` injects `ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`/model per instance; `permission_mode="dontAsk"` + `allowed_tools` for headless; `setting_sources` controls which `.claude/` config loads. Parallel = multiple SDK client sessions in asyncio tasks. |
| deepagents + GLM/Ollama | ✅ | `create_deep_agent(model="ollama:...")` is a documented first-class path (docs even show `z-ai/glm-5.2` variants). Subagents via `SubAgentMiddleware` / `CompiledSubAgent` (custom LangGraph graphs as subagents). |
| LikeC4 → draw.io | ✅ | Official: `likec4 export drawio`, one .drawio per view or `--all-in-one`; round-trip profile preserves layout/style; `--uncompressed` for compatibility. |
| Postgres checkpointer | ✅ | `langgraph-checkpoint-postgres` → `AsyncPostgresSaver` for FastAPI async; call `.setup()` once. |
| Embeddings | ✅ | **bge-m3** via Ollama (1024-dim, 8K ctx, dense+sparse → native Qdrant hybrid search without a second model). |
| draw.io in React UI | ✅ | Self-hosted `jgraph/drawio` Docker image + `react-drawio` component (embed mode, postMessage protocol, `baseUrl` → self-hosted instance). |
| Prior art for orchestrating CC fleets | ✅ | Patterns to borrow: LangGraph supervisor pattern, Claude Code Agent Teams, Multiclaude, Gas Town (supervisor assigns tasks to CC workers via shared task list). |

## Architecture

```
┌─ React UI (chat, dashboard, CC run monitor, diagram editor, knowledge browser)
│        │ REST + SSE/WebSocket
┌────────▼─────────────────────────────────────────────┐
│ FastAPI backend                                      │
│  ├─ Orchestrator (deepagents create_deep_agent)      │
│  │   subagents: architect, doc-writer, researcher,   │
│  │              code-delegate                        │
│  ├─ CC Bridge (claude-agent-sdk sessions → Ollama)   │
│  ├─ Job queue (Procrastinate, Postgres-backed)       │
│  ├─ Scheduler (APScheduler) + Watcher (watchfiles)   │
│  └─ CLI (typer) talks to same API                    │
├─ Postgres: registry, decisions, sessions, prefs,     │
│            LangGraph checkpoints, job queue          │
├─ Qdrant:   per-project collections (bge-m3 hybrid)   │
├─ drawio:   self-hosted jgraph/drawio (embed mode)    │
└─ Host: Ollama (local embeddings + glm-5.2:cloud), CC │
```

- **Model access**: everything through LangChain `init_chat_model` / `ollama:` provider strings — default `glm-5.2:cloud`, swappable per agent via config table. Ollama runs on the **host** (Windows); containers reach it at `host.docker.internal:11434`.
- **Claude Code instances run on the host** too (spawned by the backend via Agent SDK). ⚠ Decision embedded: backend runs CC bridge as a host-side worker process (not inside the container) so it can spawn `claude` CLI processes; it connects to the same Postgres/Qdrant. Design the bridge as its own small service (`cc-worker`) so it can be containerized later.

## Repositories (two, sibling folders under `bitch-stewie/`)

### `backend/` (Python 3.12+, uv)
```
backend/
├─ src/assistant/
│  ├─ api/            # FastAPI routers: chat, projects, jobs, approvals, knowledge, cc-runs
│  ├─ orchestrator/   # deep agent factory, subagent defs, milestone-gate middleware
│  ├─ agents/         # architect.py, doc_writer.py, researcher.py, code_delegate.py
│  ├─ cc_bridge/      # Agent SDK session mgmt, brief format, run registry, streaming
│  ├─ memory/         # Postgres models (SQLAlchemy), decisions log, prefs, registry
│  ├─ rag/            # ingestion pipeline, Qdrant client, bge-m3 hybrid search
│  ├─ jobs/           # Procrastinate tasks, APScheduler crons, watchfiles vault watcher
│  ├─ diagrams/       # LikeC4 CLI wrapper, drawio XML read/write, export pipeline
│  ├─ docs_gen/       # pandoc pipeline (md → docx/pdf with reference templates)
│  └─ cli/            # typer CLI: chat, jobs, approvals, ingest, projects
├─ skills/orchestrator/   # deep-agent skills (SKILL.md files for the harness)
├─ tests/             # pytest + LangSmith eval harness
└─ docker/            # Dockerfile, compose file (postgres, qdrant, drawio, backend, frontend)
```

### `frontend/` (React + TypeScript + Vite)
- Chat (SSE streaming), approvals inbox, project dashboard, CC run monitor (live status/output/approve/abort), knowledge browser (upload → ingest → inspect collections), diagram view (`react-drawio` → self-hosted drawio).

## Leverage map — native CC / plugins / installed skills (build on, don't rebuild)

**Native Claude Code features used at runtime:**
- **`/deep-research`** (first-party skill) — all deep web research; researcher subagent just wraps it.
- **`/code-review`, `verify`, `security-review`** (bundled skills) — the review half of the implement→review→fix loop uses these natively instead of a custom reviewer prompt.
- **Agent Teams** (experimental, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`) — for **intra-job parallelism**: when a delegated job is parallelizable, the bridge starts ONE lead CC session that spawns teammates (shared task list with dependencies, peer messaging, file locking, per-teammate git worktrees). Our backend does **job-level** orchestration only; CC does instance-level. This removes most custom parallel-instance management from Phase 1. Known limits (no cross-session teams, resume issues) are fine since each job = one session.
- **`claude mcp serve`** — CC as an MCP server; optional second integration mode where the orchestrator consumes CC as a LangChain MCP tool (deepagents supports MCP tools natively). Evaluate in Phase 1 vs Agent SDK; SDK remains primary (streaming + session control).
- **Hooks** — CC lifecycle hooks POST events (tool use, stop, subagent stop) to a backend webhook → powers the CC run monitor without parsing the SDK stream alone.
- **MCP client in CC** — our backend exposes an **`assistant-memory` MCP server** (FastMCP: registry queries, Qdrant hybrid search, decisions log read/write). Every spawned CC instance gets it configured → CC pulls project context natively instead of us stuffing everything into briefs. Use the installed `build-mcp` skill to build it.

**Plugins to install/use:**
- **Everything Claude Code** (already installed — source of most current session skills): reuse its agents/commands/rules inside delegated CC sessions (TDD, code-review, bug-fix pipelines) rather than authoring cc-skills from scratch; our cc-skills plugin only adds the brief/result contract + repo conventions on top.
- **drawio-skill** (Agents365-ai) — natural-language → .drawio generation with vision self-check; use for ad-hoc/one-off diagrams; LikeC4 remains source of truth for the architecture model.
- **ruflo MCP** (already configured: memory_store/memory_search/swarm_init/agent_spawn) — overlaps with what we build; not a runtime dependency, but mine it for patterns and optionally use its memory tools inside CC sessions until our MCP server exists.

**Installed skills that guide the BUILD itself** (hand these to the coding agent): `framework-selection` → `deep-agents-core`/`-memory`/`-orchestration`, `langgraph-fundamentals`/`-persistence`/`-human-in-the-loop`, `langchain-rag`, `langchain-middleware`, `langchain-dependencies`, Qdrant pack (`qdrant-deployment-options`, `-performance-optimization`, `-search-quality`), `langsmith-trace`/`-dataset`/`-evaluator`, `build-mcp`, `test-driven-development`, `write-tests`, `subagent-driven-development`, `commit`/`create-pr`.

## Key design decisions

1. **Orchestrator** = `create_deep_agent` with the 4 subagents; custom middleware implements **milestone gates** using LangGraph `interrupt()` → approvals persisted in Postgres → answered from UI or CLI (`Command(resume=...)`).
2. **CC Bridge contract**: orchestrator writes a **brief** (markdown: goal, constraints, acceptance criteria, repo path, skills to use) → `cc-worker` opens an Agent SDK session with `env={ANTHROPIC_BASE_URL: "http://localhost:11434", ...}`, `permission_mode="dontAsk"`, scoped `allowed_tools`, cwd = target repo, `assistant-memory` MCP server configured → events flow to Postgres (`cc_runs`, `cc_run_events`) via SDK stream + CC hooks webhook → returns structured result (diff summary, commits, test output). CC does its own git. **Parallelizable jobs**: bridge enables Agent Teams in the session; the lead teammate decomposes and coordinates (worktrees, task list) — backend stays at job level. **Review loop**: same session or follow-up session runs native `/code-review` + `verify`; verdict → iterate until pass or max-N → milestone gate.
3. **Memory (Postgres)**: `projects`, `tasks`, `decisions` (ADR-style, linked to project + conversation), `preferences`, `sessions`/`messages` (full history), `approvals`, `cc_runs`, plus LangGraph checkpoint tables and Procrastinate queue tables. Everything project-scoped (workspace registry).
4. **RAG (Qdrant)**: collection per project + `global` collection. bge-m3 dense+sparse hybrid. Sources: markdown vault folder (watched → auto-ingest), manual uploads, researcher-fetched URLs/arXiv, distilled conversation summaries (nightly job). **No codebase ingestion** — code questions go to a CC session.
5. **Researcher**: thin subagent that orchestrates rather than reimplements. (a) **Deep web research is delegated to Claude Code's native `/deep-research` skill** (first-party as of June 2026) via the cc_bridge — CC fans out searches, verifies claims, returns a cited report; the researcher ingests that report into Qdrant + decisions log. (b) Local retrieval stays in the backend: Qdrant hybrid search over vault/collections (CC doesn't know Qdrant). (c) Simple URL/arXiv fetchers remain in the backend **ingestion pipeline only** (raw chunks for RAG need content, not a synthesized report). No Tavily/search API dependency.
6. **Diagrams**: LikeC4 files in each project folder are source of truth → `likec4 export drawio` on change (watch mode) → .drawio files stored per project → edited in embedded drawio (round-trip: manual edits parsed back only as annotations; model stays authoritative). Node.js needed in backend image for LikeC4 CLI.
7. **Docs**: doc-writer drafts markdown → pandoc (in backend image) → docx/pdf with reference template.
8. **Jobs**: Procrastinate (Postgres-native async queue, retries) for long task loops + ingestion; APScheduler for crons; watchfiles for vault/model watchers. No Redis needed.
9. **Skills, two separate sets**: 
   - `backend/skills/orchestrator/` — deep-agent skills: `delegate-coding-task`, `review-loop`, `architecture-decision`, `diagram-update`, `doc-deliverable`, `research-brief`.
   - `cc-skills/` (distributed to target repos via a **Claude Code plugin** package) — kept **thin**: `implement-from-brief`, `report-structured-result`, `research-to-report` (wraps native `/deep-research`), repo conventions. Review/TDD/bug-fix workflows come from **native bundled skills + Everything Claude Code**, not reimplemented. Rule: never reimplement a native CC capability or an installed plugin's skill — wrap and orchestrate it.
10. **Observability**: LangSmith tracing on (works with any model via LangChain); pytest for unit/integration; LangSmith datasets + evaluators for agent quality (brief→result fidelity, RAG groundedness, router correctness).

## Implementation phases

**Phase 0 — Foundations (repos + stack)**: scaffold both repos; docker-compose with postgres/qdrant/drawio; SQLAlchemy models + migrations (alembic); `AsyncPostgresSaver.setup()`; config system (pydantic-settings, `.env`); LangSmith wiring; CI-less pytest baseline.

**Phase 1 — CC orchestration loop (V1 milestone)**: cc_bridge with Agent SDK → Ollama GLM 5.2; brief format; single delegated run end-to-end from **CLI** (`assistant delegate "<task>" --repo <path>`); run registry + event flow to Postgres (SDK stream + hooks webhook); review loop using native `/code-review` + `verify` (max-N iterations); milestone approval gate in CLI; minimal `assistant-memory` MCP server (registry read + decisions write) wired into spawned sessions. **Exit criterion: a real coding task on a real repo completes brief→code→review→approval unattended except gates.** Then parallelism via **Agent Teams in the lead session** (not N separate SDK sessions); also evaluate `claude mcp serve` as an alternative integration mode.

**Phase 2 — Memory + orchestrator**: deep agent with 4 subagents (stub tools ok); workspace registry + project scoping; decisions log; sessions persistence; preferences; approvals table + CLI approvals inbox.

**Phase 3 — RAG + researcher**: ingestion pipeline (vault watcher, uploads, URL/arXiv fetch); bge-m3 hybrid Qdrant; researcher subagent = Qdrant retrieval + `/deep-research` delegation through cc_bridge (reuses Phase 1 infrastructure); report ingestion; conversation-summary nightly job.

**Phase 4 — Architect + docs pipeline**: LikeC4 wrapper + drawio export + watch regen; doc-writer + pandoc docx/pdf; decisions → ADR rendering.

**Phase 5 — Web UI**: FastAPI SSE endpoints; chat; approvals inbox; CC run monitor; project dashboard; knowledge browser; embedded drawio editor.

**Phase 6 — Loops, evals, hardening**: scheduled jobs; job queue UI; LangSmith datasets/evaluators; backup notes for volumes; secrets review.

## Verification

- **Phase 1 gate (critical)**: manual smoke — `ollama launch claude` works interactively first; then SDK-spawned headless run against a sandbox repo; verify GLM 5.2 tool-calling quality through CC is acceptable (fallback: keep model string configurable → try `qwen3-coder:cloud` or Anthropic API if GLM underperforms in CC harness).
- Each phase: pytest integration tests against dockerized Postgres/Qdrant; LangSmith traces inspected.
- End-to-end demo script per phase (documented in repo README).

## Risks / open items

- **GLM 5.2 inside Claude Code harness**: functionally supported, but prompt/tool fidelity vs real Claude is the main quality risk — Phase 1 exists to de-risk this first. Model stays swappable.
- **Agent Teams is experimental** (session resume quirks, one team per session, no nested teams) and untested with Ollama-backed models — Phase 1 validates; fallback is the original design (backend manages 2–3 separate SDK sessions itself).
- Ollama Cloud rate limits with 2–3 parallel CC instances — start serial, measure.
- `/deep-research` quality when CC runs on GLM 5.2 + Ollama web search (vs Anthropic models/search) — validate in Phase 3 with a known research question; model stays swappable.
- drawio round-trip: treat draw.io edits as presentation-layer only; don't attempt full reverse-sync to LikeC4 in v1.
- Windows host + Docker: cc-worker runs on host (Python), needs same `.env`; document host/container URL differences (`host.docker.internal`).
