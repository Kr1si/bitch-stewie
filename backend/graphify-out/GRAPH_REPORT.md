# Graph Report - backend  (2026-08-02)

## Corpus Check
- 120 files · ~27,511 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 917 nodes · 1507 edges · 83 communities (67 shown, 16 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 300 edges (avg confidence: 0.67)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7463a92b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]

## God Nodes (most connected - your core abstractions)
1. `make_test_app()` - 38 edges
2. `get_session_factory()` - 35 edges
3. `get_sync_session_factory()` - 31 edges
4. `DelegationRunner` - 28 edges
5. `Brief` - 28 edges
6. `get_settings()` - 22 edges
7. `Base` - 21 edges
8. `CCRunEvent` - 19 edges
9. `CCRun` - 16 edges
10. `Goal` - 14 edges

## Surprising Connections (you probably didn't know these)
- `str` --uses--> `Base`  [INFERRED]
  migrations/env.py → src/assistant/infrastructure/memory/db.py
- `test_project_roundtrip()` --calls--> `get_session_factory()`  [INFERRED]
  tests/test_persistence.py → src/assistant/infrastructure/memory/db.py
- `test_fallback_working_agreement_contains_result_marker()` --calls--> `fallback_working_agreement()`  [INFERRED]
  tests/test_delegate.py → src/assistant/infrastructure/cc_bridge/brief.py
- `test_checkpointer_setup()` --calls--> `get_settings()`  [INFERRED]
  tests/test_persistence.py → src/assistant/shared/config.py
- `test_langsmith_disabled_without_key()` --calls--> `langsmith_enabled()`  [INFERRED]
  tests/test_config.py → src/assistant/shared/config.py

## Communities (83 total, 16 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (40): Brief, fallback_working_agreement(), The brief: the contract between the orchestrator and a Claude Code instance.  Th, DelegationOutcome, DelegationRunner, Delegation runner: brief -> Claude Code session (on GLM 5.2 via Ollama) -> revie, Copy delegate skills into the target repo's .claude/skills; return staged names., Stage the output style into the target repo; return the settings path. (+32 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (66): assistant, assistant.agents, assistant.api, assistant.application, assistant.application.orchestrator, assistant.application.orchestrator.artifact_tools, assistant.application.orchestrator.context, assistant.application.orchestrator.example_tools (+58 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (66): assistant, assistant.agents, assistant.api, assistant.application, assistant.application.orchestrator, assistant.application.orchestrator.artifact_tools, assistant.application.orchestrator.context, assistant.application.orchestrator.example_tools (+58 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (54): Aggregated dashboard statistics: one round-trip for the whole dashboard., stats(), BaseSettings, str, run_migrations_offline(), run_migrations_online(), _sync_url(), QdrantClient (+46 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (22): _connector(), daily_report(), delegate_brief(), _dispatch_goal(), ingest_path_job(), Procrastinate job queue (Postgres-native) for long-running work with retries.  G, Route a goal to its kind's handler, or report an unhandled kind., Load one goal by id and run it through its kind's handler.      Deferred by ``da (+14 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (40): async_sessionmaker, _fake_graph(), make_test_app(), FastAPI, Offline test application factory.  `create_app()` in production wires up a real, Fake deepagents graph: streams nothing, reports a clean non-gated state.      Th, Build an app with in-memory SQLite + fake graphs, mirroring production., Chat SSE endpoint returns text/event-stream and terminates with 'done'.      The (+32 more)

### Community 6 - "Community 6"
Cohesion: 0.17
Nodes (28): _append_project_rule(), build_memory_server(), _example_rows(), get_preferences(), list_decisions(), list_examples(), list_projects(), _project_by_name() (+20 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (30): export_drawio(), find_model_dir(), _needs_shell(), LikeC4 -> draw.io export pipeline. The LikeC4 model is the source of truth., Run `likec4 export drawio` and return the produced files., Locate the directory containing .likec4/.c4 model files in a repo., export_markdown(), _pandoc() (+22 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (45): _chunk_text(), create_goal_route(), delete_goal_route(), _get_or_404(), goal_chat_stream(), GoalChatIn, GoalIn, GoalPatch (+37 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (28): delete_example(), example_content(), _examples_root(), list_examples(), _parse_project_id(), Reference examples library (diagrams + docs).  The architect/doc-writer subagent, Upload a reference example (.drawio/.xml/.png for diagrams; .md/.docx/.pdf for d, _resolve_project_id() (+20 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (65): chat(), chat_stream(), ChatIn, _chunk_text(), _ensure_session(), _extract_text(), _interrupt_payload(), list_sessions() (+57 more)

### Community 11 - "Community 11"
Cohesion: 0.17
Nodes (20): DeclarativeBase, Mapped, Base, Approval, Goal, GoalKind, GoalStatus, Preference (+12 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (31): approvals(), chat(), delegate(), ingest(), assistant CLI - Phase 1 drives delegation directly; later phases go through the, Idempotently seed built-in project + goal presets (run by the backend on boot)., Idempotently seed built-in project + goal presets (run by the backend on boot)., Delegate a coding task to a Claude Code instance (GLM 5.2 via Ollama). (+23 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (27): Watch the vault folder and auto-ingest changed markdown files., Watch the vault folder and auto-ingest changed markdown files., watch(), Nightly: ingest yesterday's conversation messages into the KB., summarize_conversations(), Vault watcher: auto-ingest markdown files when they change., Blocking loop: watch the configured vault and ingest changed files., watch_vault() (+19 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (43): create_app(), lifespan(), FastAPI application factory., BaseCheckpointSaver, _extract_text(), Interactive chat with the orchestrator (Selector loop; delegation runs on the wo, Build the HITL resume payload for however many action requests were raised., _resume_value() (+35 more)

### Community 15 - "Community 15"
Cohesion: 0.26
Nodes (13): collection_sources(), collections(), ingest_path_ep(), ingest_text_ep(), IngestPathIn, IngestTextIn, Knowledge base endpoints: search and ingestion for the web UI., All kb_* collections with point + source counts for the Knowledge overview. (+5 more)

### Community 16 - "Community 16"
Cohesion: 0.31
Nodes (10): get_diagram(), list_diagrams(), _project_repo(), Serve generated .drawio diagrams for a project's repo (Phase 5+ UI)., List generated .drawio files (basename + modified time) under <repo>/diagrams., Return the raw .drawio XML for the embed's `xml` prop., Any, FileResponse (+2 more)

### Community 17 - "Community 17"
Cohesion: 0.17
Nodes (5): Pure unit tests for the Goal domain model (no DB, no app).  Covers enum values,, Enum/scalar column defaults match the intended seed behavior.      Note: like th, Every SEED_GOALS payload must construct a Goal without error., test_goal_column_defaults_are_configured(), test_seed_goals_validate_against_model()

### Community 18 - "Community 18"
Cohesion: 0.29
Nodes (7): pick_folder(), _pick_folder_sync(), Host-side helpers. The backend runs on the user's machine, so it can pop a real, Open the native folder picker and block until the user chooses (or cancels)., Return the chosen absolute path, or null if the user cancelled., Any, str

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (6): Plan file format, Planning a future improvement, Self-improvement, Status lifecycle, When to read plans, When to write a plan

### Community 20 - "Community 20"
Cohesion: 0.29
Nodes (6): AgentDefinition, build_subagents(), Native Claude Code subagents handed to every delegated CC session.  These are *C, Return the CC subagent registry passed as `agents=` to ClaudeAgentOptions., Return the CC subagent registry passed as `agents=` to ClaudeAgentOptions., str

### Community 21 - "Community 21"
Cohesion: 0.40
Nodes (5): main(), int, Path, str, _rel()

### Community 22 - "Community 22"
Cohesion: 0.53
Nodes (5): main(), move_files(), str, rewrite_imports(), run()

### Community 24 - "Community 24"
Cohesion: 0.40
Nodes (4): Done when, Plan body structure, Shaping a coding plan, When to use this shape

### Community 25 - "Community 25"
Cohesion: 0.40
Nodes (4): Handoff, Plan body structure, Shaping a design plan, When to use this shape

### Community 26 - "Community 26"
Cohesion: 0.40
Nodes (4): Handoff, Plan body structure, Shaping a research plan, When to use this shape

### Community 27 - "Community 27"
Cohesion: 0.50
Nodes (3): Assistant Backend, Development, Stack services

### Community 28 - "Community 28"
Cohesion: 0.50
Nodes (3): Format, Keep, Tone

### Community 29 - "Community 29"
Cohesion: 0.50
Nodes (3): Delegated coding task — working agreement, Delivery format, How to work

### Community 78 - "Community 78"
Cohesion: 0.15
Nodes (20): Decision, ADR-style decision log entry, linkable to the session that produced it., delegate_coding_task(), list_decisions(), list_preferences(), list_projects(), LangChain tools for the orchestrator and its subagents.  All tools are sync (Lan, Register a new project in the workspace registry (or report if it exists). (+12 more)

### Community 79 - "Community 79"
Cohesion: 0.19
Nodes (14): deep_research(), Researcher tools: local knowledge base + native /deep-research via Claude Code., Run deep web research with citations via Claude Code's native /deep-research ski, Search the ingested knowledge base (vault docs, standards, past research)     sc, Search the ingested knowledge base (vault docs, standards, past research)     sc, Run deep web research via Claude Code's native /deep-research skill.      Synchr, Stage the global deep-research-review skill into the scratch workdir.      The S, Run deep web research with citations via Claude Code's native /deep-research ski (+6 more)

### Community 80 - "Community 80"
Cohesion: 0.29
Nodes (11): Example, A reference example the architect/doc-writer load when creating a new     diagra, list_examples(), Tools that expose the reference examples library to the architect and doc-writer, List reference examples for the current project (kind: 'diagram', 'doc', or '' f, Read one reference example into context.      Text examples (.md/.txt/.drawio/.x, read_example(), _rows() (+3 more)

### Community 81 - "Community 81"
Cohesion: 0.36
Nodes (8): build_lifecycle_hooks(), _persist_event(), Native CC lifecycle hooks -> CCRunEvent rows (+ PermissionRequest -> Approval)., Hooks dict for ClaudeAgentOptions; closures bind this run's id., HookMatcher, ApprovalStatus, str, UUID

### Community 82 - "Community 82"
Cohesion: 0.33
Nodes (6): Project, current_project(), Shared helper for resolving the session's fixed project from RunnableConfig.  Th, Resolve the ``Project`` row for this session from ``config``.      Raises ``Valu, Project, RunnableConfig

## Knowledge Gaps
- **200 isolated node(s):** `assistant.interface`, `assistant.application.services.jobs_service`, `assistant.memory`, `assistant.orchestrator`, `assistant.infrastructure.memory.sync_db` (+195 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_session_factory()` connect `Community 10` to `Community 3`, `Community 5`, `Community 8`, `Community 9`, `Community 16`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `Community 3` to `Community 0`, `Community 4`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `get_sync_session_factory()` connect `Community 6` to `Community 0`, `Community 4`, `Community 12`, `Community 13`, `Community 14`, `Community 78`, `Community 80`, `Community 81`, `Community 82`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `get_session_factory()` (e.g. with `_ensure_session()` and `list_sessions()`) actually correct?**
  _`get_session_factory()` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `get_sync_session_factory()` (e.g. with `_persist_event()` and `.__init__()`) actually correct?**
  _`get_sync_session_factory()` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `DelegationRunner` (e.g. with `Brief` and `CCRun`) actually correct?**
  _`DelegationRunner` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `Brief` (e.g. with `DelegationOutcome` and `DelegationRunner`) actually correct?**
  _`Brief` has 25 INFERRED edges - model-reasoned connections that need verification._