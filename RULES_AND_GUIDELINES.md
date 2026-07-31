# Python / LangChain / LangGraph — Rules & Guidelines

Portable engineering conventions, distilled from Project Netherbrain. Drop this file into any
Python + LangChain/LangGraph project and adapt the placeholders (`yourpackage`, context names,
paths). Everything here is intentionally opinionated and CI-enforceable — that's the point.

---

## 1. Linting & formatting — ruff

```toml
[tool.ruff]
line-length = 100
target-version = "py313"          # match your interpreter
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM", "PGH", "ANN", "C4", "RUF", "ASYNC"]
ignore = [
    "ANN401",  # explicit Any in annotations — banned, but mypy disallow_any_explicit
               # reports it with better context; keep a single source of truth
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ANN"]  # test fns don't need return annotations; fixtures stay readable

[tool.ruff.lint.isort]
known-first-party = ["yourpackage"]
```

Rule families worth knowing why they're there:
- `ANN` — no untyped defs; forces the typing discipline below at the function-signature level.
- `PGH` — bans bare `# type: ignore`; every suppression needs an error code + reason (see §2).
- `ASYNC` — catches sync-IO-in-async-context mistakes (blocking calls inside `async def`).
- `B`, `SIM` — bug-prone patterns and needless complexity.

## 2. Typing — mypy strict

```toml
[tool.mypy]
python_version = "3.13"
strict = true
disallow_any_explicit = true
disallow_any_generics = true
warn_return_any = true
warn_unused_ignores = true
enable_error_code = ["ignore-without-code", "redundant-expr", "truthy-bool"]
plugins = ["pydantic.mypy"]
mypy_path = "src"
packages = ["yourpackage"]

[[tool.mypy.overrides]]
module = ["some_untyped_dep.*"]
ignore_missing_imports = true

[[tool.mypy.overrides]]
# Tests: strict minus explicit-Any ban (fixtures/parametrize interop needs it).
module = ["tests.*"]
disallow_any_explicit = false

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

Hard rules this buys you:
- **No untyped shapes.** No bare `dict`, no `Any`, no `dict[str, Any]`, no untyped `**kwargs` in
  domain/application/interface code. Every boundary-crossing structure — API request/response,
  tool args/results, job payloads, events, LLM messages, config — is a **Pydantic model** (or a
  fully-typed `TypedDict` where a Pydantic model is impractical, e.g. LangGraph state).
- `# type: ignore` is only ever written as `# type: ignore[error-code]  # reason` — never bare.
  Ruff's `PGH003` enforces the code; the reason is a review-time human requirement.
- `make typecheck` (or equivalent) runs mypy strict as part of the test suite, not a separate
  optional step. CI fails on any error, not just new ones.

## 3. Pydantic boundary models

- Every place data crosses a trust or process boundary gets a Pydantic model: HTTP
  request/response, MCP/tool `args_schema` and results, queue/job payloads, domain events, LLM
  gateway messages, app config (`pydantic-settings`).
- Internal-only data structures that never cross a boundary can be plain dataclasses or
  `TypedDict`s — don't over-apply Pydantic where the validation cost buys nothing.
- Frontend equivalent: zod schemas at API boundaries, mirroring the backend Pydantic models
  field-for-field, with a round-trip test against recorded fixtures.

## 4. LangChain objects & tools

- Every tool is `@tool`, has a **docstring whose first line is the LLM-facing description**, and
  an **explicit Pydantic `args_schema`** — never rely on signature inference alone.
- One tool per file (`tools/<family>/<tool_name>.py`: args model + `@tool` + any tool metadata);
  family `__init__` re-exports. Tools register in a central registry.
- A registry-wide lint test fails CI if any registered tool is missing a docstring or an explicit
  `args_schema`.
- Large tool outputs use `response_format="content_and_artifact"`: a short summary goes back to
  the model as `ToolMessage` content; the full payload is the artifact, stored in graph state —
  don't let large payloads bloat the message history / context window.
- Tools (and nodes) may return `Command(update=…, goto=…)` to write state and redirect control
  flow directly, without needing to round-trip through message history.

## 5. LangGraph workflows & agents

### State & nodes
- State is a typed `TypedDict`, never a bare `dict`. Every list/accumulating field gets an
  `Annotated` reducer (`add_messages`, `operator.add`, or custom) — a missing reducer is a
  last-write-wins bug, and it's fatal once you introduce `Send` fan-out.
- Nodes return **typed partial-update `TypedDict`s** (`total=False`), never mutate state in place
  and never return a bare `dict`.
- Routing nodes are annotated `Command[Literal["node_a", "node_b", ...]]`. Never combine a static
  edge and a `Command(goto=...)` from the same node unintentionally — both fire.

### Flow control
- Use `Command(update=…, goto=…)` to combine a state update with routing in a single node.
- Use `Send` for parallel fan-out (per-item work); pair every fan-out with a reducer on the
  aggregating field.
- Use plain conditional edges for pure routing with no state update.

### Human-in-the-loop & persistence
- `interrupt(payload)` where `payload` is a JSON-serializable Pydantic model; resume via
  `Command(resume=…)` on the same `thread_id`.
- **All side effects before an `interrupt` must be idempotent** (upsert, check-before-create) —
  the node re-runs from the top on resume, so non-idempotent side effects double-fire.
- `PostgresSaver` (or your durable checkpointer) in production, with `.setup()` run at deploy
  time — never at app startup (avoids races across replicas).
- Thread-id convention: `<domain>:<id>` (e.g. `submission:<id>`, `chat:<user>:<session>`,
  `workflow:<kind>:<id>`) — pick one and apply it everywhere.
- Subgraph checkpointer scoping: `checkpointer=False` for pure deterministic pipelines,
  default (`None`) for interrupt-capable workflow subgraphs, `True` only for stateful
  conversational subagents that are never invoked in parallel with themselves.

### Errors — 4-tier strategy
1. Transient (network blip, rate limit) → `RetryPolicy` on the node.
2. LLM-recoverable (bad tool call) → `ToolNode(handle_tool_errors=True)`.
3. User-fixable (bad input, needs a decision) → `interrupt`.
4. Unexpected → raise, let the job runner / caller mark the unit of work failed. Don't swallow.

### Streaming
- `messages` mode for token-level chat streaming to a UI.
- `custom` mode (`get_stream_writer()`) for pipeline/job progress events surfaced elsewhere
  (status pages, submission state, etc).

### Deterministic-first philosophy (precision over speed; speed via parallelism)
- **Deterministic code node for anything expressible as code** — validation, parsing, diffing,
  git ops, indexing, routing on known state. The LLM's job is narrowly to **fill parameters**
  (extraction, classification, drafting) via **structured output into a Pydantic model** — never
  free-text parsing of an LLM response.
- ReAct-style LLM loops only where genuinely unavoidable, always with a bounded iteration cap;
  prefer single-shot structured-output nodes over a loop when the task allows it.
- **Context hygiene**: not everything needs to round-trip through the LLM. State carries the real
  data; messages carry only what the model needs to decide (see §4 on tool artifacts).
- **Parallel by default**: heavy `Send` fan-out/fan-in inside workflows wherever items are
  independent (per-file, per-chunk, per-record); independent graph branches run concurrently.
- **Async everywhere**: all nodes and tools are `async def`; IO goes through async clients
  (httpx, SQLAlchemy async/asyncpg, async vector-store clients); gather independent IO calls with
  `asyncio.gather`. No sync IO in a request or worker path.

### Cognitive firewall at every agent entry point
Before input reaches an expensive agent:
1. Deterministic checks — auth/RBAC scope, payload schema validation, size/rate limits, garbage
   and prompt-injection heuristics.
2. A small/fast LLM classifier with structured output (`verdict: allow | reject | clarify` +
   typed reason).

Rejections short-circuit with `Command(goto=END, update={...rejection message...})` — the main
agent/supervisor is never invoked on rejected input. Implement as a reusable subgraph, compiled
with `checkpointer=False`.

### Framework-selection rubric
| Need | Use |
|---|---|
| Planning / files / subagents / skills | Deep Agents |
| Owned control flow, loops, human-in-the-loop | Custom `StateGraph` |
| Single-purpose bounded tool loop | `create_agent` ReAct (fine nested inside a workflow) |
| No agent loop at all | Plain chain / deterministic pipeline |

## 6. Modularity & single responsibility (CI-enforced)

- Enforce file-size caps in CI (a small script comparing line counts is enough): source files
  ≤ 400 lines, tests ≤ 600, markdown ≤ 1000 (migrations exempt).
- **Workflows/graphs** are packages, not single files:
  ```
  <workflow>/
    state.py        # TypedDict state + typed partial-update contracts
    graph.py         # composition ONLY: add_node / add_edge / compile — no logic
    nodes/
      agents/        # LLM parameter-fill nodes, one per file
      deterministic/ # pure code nodes, one per file
      routing/       # conditional edges / Command routers, one per file
    prompts/         # one module per LLM node, plus sections.py
  ```
  Node categories interact only through the typed state contract in `state.py` — no cross-imports
  between node modules.
- **Prompts** are never inline in node code. Compose them from XML-tagged section constants
  (`<role>`, `<instructions>`, `<context>`, `<output_format>`) in `prompts/sections.py`; builder
  functions are pure `state -> messages` transforms. Shared sections live in a common prompts
  module.
- **Tools**: one tool per file as in §4; family `__init__` re-exports.
- **Interface/API layers**: one router per resource, composed in a top-level router module.
- **Frontend feature libs**: slice folders — `components/` (one component + colocated test per
  file), `hooks/` (one per file), `api.ts`, `routes.tsx`, `index.ts` barrel.

## 7. DDD / layered architecture (adapt if your project uses it)

If the project is structured as bounded contexts with domain/application/infrastructure/interface
layers, enforce these import rules with `import-linter` (or an equivalent static check) — don't
rely on convention alone:

- `domain` → `shared_kernel` only. No framework imports (no FastAPI, SQLAlchemy, LangGraph,
  LangChain) inside domain code.
- `application` → `domain` (+ `shared_kernel`). Never imports `infrastructure` or `interface`.
- `infrastructure` → implements `domain` ports; may import `platform`/shared infra.
- `interface` (routers, MCP tools, CLI) → `application`.
- Cross-context communication only through application services / domain events — never reach
  into another context's internals.
- `platform`/shared infrastructure code may be imported by `infrastructure`/`interface`, never by
  `domain`.

```toml
[tool.importlinter]
root_package = "yourpackage"
include_external_packages = true

[[tool.importlinter.contracts]]
name = "domain layers are pure"
type = "forbidden"
source_modules = ["yourpackage.contexts.<ctx>.domain"]
forbidden_modules = [
    "yourpackage.platform",
    "yourpackage.contexts.<ctx>.infrastructure",
    "yourpackage.contexts.<ctx>.interface",
    "fastapi", "sqlalchemy", "langgraph", "langchain_core",
]

[[tool.importlinter.contracts]]
name = "application does not import infrastructure or interface"
type = "forbidden"
source_modules = ["yourpackage.contexts.<ctx>.application"]
forbidden_modules = [
    "yourpackage.contexts.<ctx>.infrastructure",
    "yourpackage.contexts.<ctx>.interface",
]
```

## 8. TDD workflow

Mandatory red-green-refactor for every feature and bugfix: write the failing test first, then the
minimal implementation, then refactor with the test green as a guardrail. Test layout mirrors
source: `tests/unit/<area>/...`, `tests/integration/...`, `tests/e2e/...`.

## 9. Testing strategy

- **Unit tests never call a live LLM.** Use a fake LLM gateway: queue canned typed responses per
  call; structured-output calls return pre-built Pydantic instances; the fake records all
  requests so tests can assert on prompt content/shape.
- **Tools** — every tool gets: (1) schema tests (valid args accepted, invalid args rejected, one
  test per constraint), (2) behavior tests against fakes for the happy path and each error-tier
  path, (3) coverage by the registry-wide lint test (docstring + `args_schema` present).
- **Graph nodes** — pure unit tests: construct state, call the node, assert the typed partial
  update. LLM nodes are tested against the fake gateway, asserting both the prompt context built
  and the typed-result handling — not the LLM's actual behavior.
- **Compiled graphs** — invoke with `InMemorySaver` + a fixed `thread_id`; drive every `Command`
  branch with tailored state/fake responses; assert `__interrupt__` payload shape (Pydantic
  round-trip); resume with `Command(resume=...)`; **double-resume test** — resume twice and assert
  no duplicated side effects (this is what actually validates the idempotency rule in §5).
- **Firewall / classifier subgraphs** — table-driven allow/reject/clarify cases per rule.
- **Integration** — testcontainers for real Postgres/vector-store/etc; adapter contract tests run
  against the real dependency, not a mock.
- **E2E** — full stack up, scripted client drives the primary user loop end-to-end plus at least
  one authz-denial case and one garbage/malicious-input case (validates the firewall).
- **Type checking as testing**: `make check` = lint + mypy strict + unit tests, run locally and in
  CI before anything merges — not an optional add-on.

## 10. Pre-commit gate sequence

Run in this order, all mandatory, stop-on-first-failure:

1. `make check` (ruff + mypy strict + unit tests)
2. Language-appropriate review pass on touched code (automated reviewer agent or human review)
3. A project-wide quality gate check (size caps, import-linter contracts, docs currency)
4. If auth, tokens, any external-facing surface, or user-input handling was touched: a targeted
   security review pass

## 11. Observability

- Trace all LLM calls, graph runs, and tool executions through one abstraction (LangChain
  callbacks / OTel) so the tracing backend is swappable by config alone — application code never
  references a specific backend directly.
- Structured logging (JSON) with correlation IDs (e.g. `thread_id`, job/submission id) that match
  trace IDs end-to-end, so a log line and a trace can always be cross-referenced.
- Consider a debug/introspection toolset (same docstring + `args_schema` rules as any other tool)
  so agents — and you — can query trace/state/job status directly instead of guessing from logs.

---

### Adapting this file to a new project
Replace: `yourpackage`, context/module names, thread-id prefixes, line-count caps if your team
prefers different numbers. Keep: the *shape* of each rule — typed boundaries, idempotent
pre-interrupt side effects, deterministic-first node design, one-thing-per-file modularity, and
the fake-gateway testing discipline. Those are the parts that actually prevent the bugs this
stack is prone to (silent state clobbering, duplicate side effects on resume, untyped LLM output
leaking into business logic).
