# Command & Workflow Library

A catalog of every command, agent, skill, and orchestration primitive available
in this environment — what each does, and how to **chain** them into reusable
workflows (code review, deep research, diagram generation, plan→implement→verify,
adversarial critique).

> **Status of the `ecc` plugin**: on 2026-07-10 the ECC plugin
> (`affaan-m/ECC`, v2.0.0 — "Everything Claude Code") was changed from
> `scope: local` (project `mails`) to **`scope: user`** so its 67 agents,
> 92 commands, and 277 skills load in **every** project. **A Claude Code
> restart is required** for them to appear in-session. Until you restart,
> the built-in skills + `general-purpose`/`Explore` agents + `graphify` CLI
> are the live surface; ecc items are marked **[ecc]** below.

---

## 0. How to read this doc

- **Primitives** (§1) are the Lego bricks — tools you combine.
- **Commands** (§2) are user-invocable slash entry points (`/foo`).
- **Agents** (§3) are specialist subagents you spawn from a workflow.
- **Skills** (§4) are on-demand knowledge/procedures Claude loads by description match.
- **Chaining rules** (§7) + **ready-made workflows** (§8) show how to compose them.
- **Workflow scripts** (§9) + the **orchestrator skill** (§10) are the reusable artifacts.

Types used below: `command-action` (does something, chainable),
`reasoning` (thinks, produces a verdict/analysis), `reference-knowledge`
(docs you consult, not a step), `meta-create` (authors new artifacts).

---

## 1. Orchestration primitives (the bricks)

| Primitive | What it is | When to use |
|---|---|---|
| **Agent tool** | Spawns a subagent in a fresh context. Types available *now*: `general-purpose`, `Explore`, `Plan`, `claude`, `claude-code-guide`, `statusline-setup`. **After ecc restart** add 67 more (§3), invoked as `ecc:<name>` or bare `<name>`. | Fan out independent work; isolate context. |
| **TaskCreate / TaskUpdate** | In-session todo list (the task tracker you see in the UI). | Track multi-step work; claim/complete tasks. |
| **Workflow tool** | Runs a deterministic JS script that orchestrates many agents (`agent()`, `parallel()`, `pipeline()`, `phase()`). Scripts live in `.claude/workflows/`. | Repeatable multi-agent pipelines (diagram, review, research). |
| **graphify CLI** | `graphify` (installed v0.8.40) — builds a knowledge graph from a folder/URL → `graphify-out/graph.json` + `graph.html`. Subcommands: `query`, `path`, `explain`, `merge-graphs`, `diagnose`. | Extract entities/relationships; power ERD & architecture diagrams; GraphRAG. |
| **Docs-by-LangChain MCP** | `search_docs_by_lang_chain` / `query_docs_filesystem_docs_by_lang_chain` — search/read LangChain docs. | Reference for LangChain/LangGraph work only. |
| **Bash / Read / Edit / Write / Grep / Glob** | File & shell primitives. | Everything else. |

**Not available here** (despite mentions in `CLAUDE.md`/orphan skills): `gh` CLI,
`ruflo` MCP (`swarm_init`/`agent_spawn`/`memory_*`), and the `sdd:*`/`sadd:*`/`superpowers:*`
plugin agent types. Workflows must not depend on them; use `general-purpose` fallbacks.

---

## 2. ecc commands (92) [ecc]

Slash commands grouped by purpose. Names are the real command names (invoke as `/<name>`).

**Core orchestration — the `orch-*` family** (research→plan→TDD→review→gated commit):
`orch-add-feature`, `orch-build-mvp`, `orch-change-feature`, `orch-fix-defect`, `orch-refine-code`.
Shared engine: `orch-pipeline` skill (not a command). Each delegates phases to ecc agents.

**Multi-model workflows — `multi-*`**: `multi-plan`, `multi-execute`, `multi-backend`,
`multi-frontend`, `multi-workflow`. Claude stays the only filesystem writer; other models advise.

**Generator/Evaluator loops — `gan-*`**: `gan-build`, `gan-design`. Bounded iterate-until-score loops.

**Adversarial review**: `santa-loop` (two independent reviewers must both approve before ship).

**Plan / PRD**: `plan`, `plan-prd`, `prp-plan`, `prp-prd`, `prp-implement`, `prp-commit`, `prp-pr`, `prp` (PR create).

**Review (per-language)**: `code-review` (local diff or PR), `review-pr` (PR via specialized agents),
`python-review`, `react-review`, `vue-review`, `go-review`, `rust-review`, `cpp-review`,
`kotlin-review`, `fastapi-review`, `flutter-review`.

**Build-fix (per-language)**: `build-fix` (auto-detect), `react-build`, `go-build`, `rust-build`,
`cpp-build`, `kotlin-build`, `gradle-build`, `flutter-build`.

**TDD (per-language)**: `cpp-test`, `go-test`, `kotlin-test`, `react-test`, `rust-test`, `flutter-test`, `test-coverage`.

**Refactor / quality**: `refactor-clean` (dead code), `quality-gate` (formatter gate), `harness-audit`.

**Docs / codemaps**: `update-codemaps`, `update-docs`, `skill-create`, `skill-health`.

**Sessions / loops**: `save-session`, `resume-session`, `sessions`, `loop-start`, `loop-status`.

**Instincts / learning**: `learn`, `learn-eval`, `evolve`, `instinct-status`, `instinct-export`,
`instinct-import`, `promote`, `prune`, `projects`.

**Hooks**: `hookify`, `hookify-list`, `hookify-configure`, `hookify-help`.

**Epic / GitHub / Jira**: `epic-claim`, `epic-decompose`, `epic-publish`, `epic-review`, `epic-sync`,
`epic-unblock`, `epic-validate`, `jira`, `pr`.

**Ops / misc**: `aside` (side question w/o losing context), `auto-update`, `checkpoint`,
`cost-report`, `ecc-guide`, `feature-dev`, `marketing-campaign`, `model-route`, `pm2`,
`project-init`, `security-scan`, `setup-pm`.

---

## 3. ecc agents (67) [ecc]

Spawn via the Agent tool as `ecc:<name>` (after restart). Grouped:

**Architecture / exploration**: `architect`, `code-architect` (feature blueprints + data flow),
`code-explorer` (trace paths, map layers, dependencies), `planner`, `spec-miner` (extract specs),
`type-design-analyzer`, `a11y-architect`.

**Review (cross-cutting)**: `code-reviewer`, `code-simplifier`, `comment-analyzer`,
`silent-failure-hunter`, `pr-test-analyzer`, `agent-evaluator`, `refactor-cleaner`.

**Review (per-language)**: `typescript-reviewer`, `python-reviewer`, `react-reviewer`, `vue-reviewer`,
`go-reviewer`, `rust-reviewer`, `java-reviewer`, `kotlin-reviewer`, `swift-reviewer`, `csharp-reviewer`,
`fsharp-reviewer`, `cpp-reviewer`, `php-reviewer`, `django-reviewer`, `fastapi-reviewer`,
`flutter-reviewer`, `healthcare-reviewer`, `mle-reviewer`, `database-reviewer`.

**Build-fix (per-language)**: `build-error-resolver`, `react-build-resolver`, `go-build-resolver`,
`rust-build-resolver`, `cpp-build-resolver`, `java-build-resolver`, `kotlin-build-resolver`,
`swift-build-resolver`, `dart-build-resolver`, `django-build-resolver`, `pytorch-build-resolver`.

**GAN harness**: `gan-planner`, `gan-generator`, `gan-evaluator`.

**TDD / testing**: `tdd-guide`, `e2e-runner`.

**Security / perf**: `security-reviewer`, `performance-optimizer`.

**Docs**: `doc-updater`, `docs-lookup` (Context7 MCP).

**Loops / ops**: `loop-operator`, `harness-optimizer`, `chief-of-staff`, `marketing-agent`,
`seo-specialist`, `conversation-analyzer`, `network-architect`, `network-config-reviewer`,
`network-troubleshooter`, `homelab-architect`, `harmonyos-app-resolver`.

**Open-source pipeline**: `opensource-forker`, `opensource-sanitizer`, `opensource-packager`.

---

## 4. ecc skills (277) [ecc] — by category

Most are `reference-knowledge` (framework/domain playbooks). The **chainable `command-action`**
ones are called out with ⭐. Full one-liners live in `docs/_ecc_catalog.json` (data dump).

**⭐ Orchestration / loops**: `orch-add-feature`, `orch-build-mvp`, `orch-change-feature`,
`orch-fix-defect`, `orch-refine-code`, `orch-pipeline`, `plan-orchestrate`, `autonomous-loops`,
`continuous-agent-loop`, `loop-design-check`, `autonomous-agent-harness`, `agentic-os`,
`claude-devfleet`, `dmux-workflows`, `team-agent-orchestration`, `team-builder`,
`parallel-execution-optimizer`, `gan-style-harness`, `ralphinho-rfc-pipeline`.

**⭐ Research**: `deep-research` (firecrawl+exa MCPs, cited reports), `research-ops`,
`exa-search`, `market-research`, `scientific-thinking-literature-review`,
`scientific-db-pubmed-database`, `scientific-db-uspto-database`, `scientific-pkg-gget`,
`data-scraper-agent`, `skill-scout`, `search-first`, `repo-scan`, `codebase-onboarding`.

**⭐ Review / quality / verification**: `santa-method` (adversarial dual-review),
`agent-self-evaluation`, `agent-eval`, `eval-harness`, `skill-comply`, `skill-stocktake`,
`production-audit`, `verification-loop`, `tdd-workflow`, `ai-regression-testing`,
`codehealth-mcp`, `plankton-code-quality`, `gateguard`, `delivery-gate`, `safety-guard`,
`click-path-audit`, `agent-architecture-audit`, `agent-introspection-debugging`.

**⭐ Diagram / visualization / media**: `manim-video` (animated system diagrams),
`code-tour` (step-by-step walkthroughs w/ file:line anchors), `frontend-slides` (HTML presentations),
`dashboard-builder` (Grafana/SigNoz), `ui-demo` (Playwright demo videos), `video-editing`,
`remotion-video-creation`, `fal-ai-media`, `videodb`, `taste`, `design-system`,
`make-interfaces-feel-better`, `frontend-design-direction`, `liquid-glass-design`.

**⭐ Meta / authoring / config**: `configure-ecc`, `agent-sort` (trim ECC to a repo's needs),
`workspace-surface-audit`, `config-gc`, `context-budget`, `cost-tracking`, `cost-aware-llm-pipeline`,
`continuous-learning-v2`, `growth-log`, `rules-distill`, `hookify-rules`, `dynamic-workflow-mode`,
`architecture-decision-records`, `intent-driven-development`, `product-capability`, `product-lens`,
`council` (four-voice decision), `recursive-decision-ledger`, `strategic-compact`,
`nanoclaw-repl`, `claude-devfleet`.

**⭐ Security**: `security-review`, `security-scan`, `security-bounty-hunter`,
`defi-amm-security`, `llm-trading-agent-security`, `nodejs-keccak256`, `evm-token-decimals`,
`prediction-market-risk-review`, `hipaa-compliance`, `healthcare-phi-compliance`.

**Framework / language patterns** (reference, ~90 skills): `react-patterns`, `react-performance`,
`react-native-patterns`, `vue-patterns`, `nuxt4-patterns`, `nextjs-turbopack`, `vite-patterns`,
`angular-developer`, `svelte`-family, `swiftui-patterns`, `swift-concurrency-6-2`,
`swift-actor-persistence`, `swift-protocol-di-testing`, `foundation-models-on-device`,
`android-clean-architecture`, `compose-multiplatform-patterns`, `dart-flutter-patterns`,
`kotlin-patterns`/`coroutines-flows`/`exposed`/`ktor`/`testing`, `java-coding-standards`,
`springboot-patterns`/`security`/`tdd`/`verification`, `quarkus-patterns`/`security`/`tdd`/`verification`,
`jpa-patterns`, `dotnet-patterns`, `csharp-testing`, `fsharp-testing`, `tinystruct-patterns`,
`golang-patterns`/`testing`, `rust-patterns`/`testing`, `python-patterns`/`testing`,
`perl-patterns`/`security`/`testing`, `django-patterns`/`celery`/`security`/`tdd`/`verification`,
`fastapi-patterns`, `nestjs-patterns`, `laravel-patterns`/`security`/`tdd`/`verification`,
`bun-runtime`, `cpp-coding-standards`/`testing`, `flutter-dart-code-review`.

**Backend / data / infra** (reference, ~40): `backend-patterns`, `api-design`, `api-connector-builder`,
`error-handling`, `database-migrations`, `postgres-patterns`, `mysql-patterns`, `clickhouse-io`,
`redis-patterns`, `prisma-patterns`, `kubernetes-patterns`, `docker-patterns`, `deployment-patterns`,
`latency-critical-systems`, `data-throughput-accelerator`, `content-hash-cache-pattern`,
`hexagonal-architecture`, `recsys-pipeline-architect`, `mcp-server-patterns`, `regex-vs-llm-structured-text`,
`ml-adoption-playbook`, `mle-workflow`, `pytorch-patterns`, `benchmark`/`methodology`/`optimization-loop`.

**Network / homelab** (reference, ~15): `cisco-ios-patterns`, `netmiko-ssh-automation`,
`network-bgp-diagnostics`, `network-config-validation`, `network-interface-health`,
`homelab-network-setup`/`readiness`/`vlan-segmentation`/`pihole-dns`/`wireguard-vpn`, `uncloud`.

**Marketing / sales / content / finance** (reference, ~40): `marketing-campaign`, `content-engine`,
`brand-voice`/`brand-discovery`, `crosspost`, `social-publisher`, `social-graph-ranker`,
`connections-optimizer`, `lead-intelligence`, `x-api`, `seo`, `article-writing`,
`investor-materials`/`outreach`, `competitive-platform-analysis`/`report-structure`,
`customer-billing-ops`, `finance-billing-ops`, `mailtrap-email-integration`, `google-workspace-ops`,
`jira-integration`, `project-flow-ops`, `unified-notifications-ops`, `email-ops`, `messages-ops`,
`automation-audit-ops`, `terminal-ops`, `github-ops`, `git-workflow`.

**Prediction-market / trading** (reference): `ito-basket-compare`, `ito-data-atlas-agent`,
`ito-market-intelligence`, `ito-trade-planner`, `prediction-market-oracle-research`.

**Healthcare** (reference): `healthcare-cdss-patterns`, `healthcare-emr-patterns`,
`healthcare-eval-harness`, `hipaa-compliance`, `healthcare-phi-compliance`.

**Supply-chain / logistics / misc** (reference): `carrier-relationship-management`,
`customs-trade-compliance`, `energy-procurement`, `inventory-demand-planning`,
`logistics-exception-management`, `production-scheduling`, `quality-nonconformance`,
`returns-reverse-logistics`, `visa-doc-translate`, `ios-icon-gen`, `nutrient-document-processing`,
`blender-motion-state-inspection`, `openclaw-persona-forge`, `generating-python-installer`,
`hermes-imports`, `opensource-pipeline`, `iterative-retrieval`, `ck` (per-project memory),
`flox-environments`, `coding-standards`, `inherit-legacy-style`, `prompt-optimizer`,
`token-budget-advisor`, `blueprint`, `agent-payment-x402`, `agent-harness-construction`,
`agentic-engineering`, `ai-first-engineering`, `enterprise-agent-ops`, `browser-qa`,
`canary-watch`, `accessibility`, `frontend-a11y`, `frontend-patterns`, `motion-foundations`/`patterns`/`advanced`/`ui`,
`ui-to-vue`, `windows-desktop-e2e`, `e2e-testing`, `browser-qa`.

---

## 5. Built-in skills (no plugin needed, live now)

| Skill | Purpose |
|---|---|
| `deep-research` | Fan-out web research → fetch → adversarially verify → cited report. (Ecc also ships a `deep-research` skill using firecrawl+exa; built-in uses WebSearch/WebFetch.) |
| `code-review` | Review the current diff for bugs + cleanups at a given effort. `--comment` posts PR comments, `--fix` applies. |
| `simplify` | Review changed code for reuse/simplification/efficiency and apply fixes. |
| `verify` | Exercise a change end-to-end against the real runtime before committing. |
| `security-review` | Security review of the diff. |
| `review` | General review entry. |
| `dataviz` | Design-system-consistent charts/dashboards (read before any chart code). |
| `run` | Launch & drive this project's app to confirm a change works. |
| `loop` | Run a prompt/command on a recurring interval. |
| `claude-api` | Reference for Claude API/SDK (model ids, pricing, caching, tool use). |
| `init` | Initialize CLAUDE.md for a project. |
| `update-config` / `keybindings-help` / `fewer-permission-prompts` | Harness config helpers. |
| `frontend-design` | Frontend design plugin skill. |
| `claude-code-setup:claude-automation-recommender` | Recommends automation setup. |

---

## 6. Removed legacy skills (formerly in `~/.claude/skills/`)

On 2026-07-10 the ~90 user-level skills that shipped here were **deleted** (backed up to
`~/.claude/_skills_backup_2026-07-10`). They referenced agent types `sdd:*`, `sadd:*`,
`superpowers:*` from plugins that were never installed, so they broke at subagent spawn.
The library now builds on ecc + built-ins instead. `~/.claude/skills/` is empty.

Affected (partial list): `critique`, `judge`, `judge-with-debate`, `do-and-judge`, `do-competitively`,
`do-in-parallel`, `do-in-steps`, `plan-task`, `implement-task`, `add-task`, `subagent-driven-development`,
`launch-sub-agent`, `tree-of-thoughts`, `propose-hypotheses`, `write-tests`, `fix-tests`, `test-prompt`,
`test-skill`, `update-docs`, `create-agent`/`command`/`hook`/`skill`/`workflow-command`/`pr`/`rule`/`ideas`,
`graphify` (user copy — use the installed `graphify` CLI instead), `deep-agents-*`, `multi-agent-patterns`,
`framework-selection`, `kaizen`, `analyse`/`analyse-problem`/`analyze-issue`, `why`, `cause-and-effect`,
`root-cause-tracing`, `reflect`, `plan-do-check-act`, `brainstorm`, `query`, `memorize`, `decay`/`reset`/`status`/`actualize`,
`commit`, `git-notes`, `git-worktrees`, `load-issues`, `review-local-changes`, `review-pr`, `attach-review-to-pr`,
`agent-evaluation`, `thought-based-reasoning`, `prompt-engineering`, `context-engineering`, `write-concisely`,
`apply-anthropic-skill-best-practices`, `build-mcp`, `setup-*`, `web-design-guidelines`,
`vercel-react-*`, `langchain-*`, `langgraph-*`, `langsmith-*`, `langfuse`, `qdrant-*`.

> To revive: restore from the backup, then install the `superpowers` / `sdd` / `sadd` plugins
> (marketplaces not currently cached) so the agent types resolve — or rewrite spawn calls to
> `general-purpose`. Not planned; we start fresh on ecc + built-ins.

---

## 7. Chaining rules

1. **Orchestrator stays clean.** A workflow script / orchestrator command must not read artifacts
   it spawns agents to produce (avoids context overflow). It dispatches, collects structured
   results, and synthesizes. (Pattern enforced by `orch-pipeline`, `do-in-steps`, `judge-with-debate`.)

2. **Context isolation = the primitive.** Spawn a fresh subagent per independent unit of work.
   Use `Explore` for read-only mapping, `general-purpose` for work that writes, `Plan` for design.
   After ecc restart, prefer the ecc specialist (`ecc:code-explorer`, `ecc:architect`, `ecc:<lang>-reviewer`).

3. **Pipeline, not barrier, by default.** In Workflow scripts use `pipeline(items, stage1, stage2, …)`
   so item A can be in stage 3 while B is still in stage 1. Use `parallel()` (barrier) only when a
   stage genuinely needs *all* prior results (dedup, cross-item comparison, early-exit on zero).

4. **Verify before ship.** Every "do" chain ends in a judge/verify step:
   `santa-method` / `agent-evaluator` / `verify` / `code-review` / `santa-loop`.
   Adversarial verify = spawn N skeptics told to *refute*; kill if majority refute.

5. **Files as shared memory.** Multi-agent coordination passes via files
   (`.specs/`, `graphify-out/graph.json`, `docs/diagrams/*.md`), not in-memory state.

6. **Model routing.** Haiku for mechanical/format work, Sonnet for review, Opus for hard
   judge/architect steps. `model-route` [ecc] recommends per-task.

7. **Loop safety.** Any autonomous loop needs a machine-decidable stop condition + budget cap +
   judge independent of the generator. Use `loop-design-check` [ecc] before running one.

---

## 8. Ready-made workflow chains

### A. Diagram generation ⭐ (priority — implemented as a script, §9)
```
[Explore x4, parallel]  map: (structure+entrypoints) (data models) (control-flow paths) (external deps)
        │  optional: graphify CLI → graph.json (nodes/edges/communities)
        ▼
[general-purpose]  synthesize Mermaid from the 4 maps + graph.json summary
        │  → docs/diagrams/<topic>.md  (C4 context+container, ERD, sequence, component)
        ▼
[Bash]  render: emit .mmd files + self-contained Mermaid-CDN HTML viewer; optional npx mmdc → SVG/PNG
```
 ecc upgrade path: swap the 4 Explore agents for `ecc:code-explorer` + `ecc:architect` + `ecc:code-architect`.

### B. Code review / critique loop
```
/code-review  (or ecc:code-reviewer / <lang>-reviewer)   → findings
        │
        ▼
[santa-method / santa-loop]  adversarial dual-review → must both pass
        │  (or judge-with-debate style: 3 judges, majority)
        ▼
[general-purpose]  apply fixes  →  /verify  (drive the real runtime)  →  /simplify
```
 ecc: `orch-fix-defect` wraps reproduce→fix→review→commit in one command.

### C. Deep research
```
/deep-research "<question>"   → fan-out WebSearch → fetch sources → adversarially verify → cited report
        │  (ecc variant uses firecrawl+exa MCPs: skill `deep-research` + `exa-search`)
        ▼
[general-purpose, adversarial]  refute each cited claim; drop unverified
        ▼
[general-purpose]  synthesize final cited markdown report → docs/research/<topic>.md
```

### D. Plan → implement → verify (the orch pipeline)
```
/intent-driven-development  (acceptance criteria)  →  /plan  (or ecc:planner / plan-orchestrate)
        │
        ▼
/orch-add-feature   research → plan → TDD → review → gated commit
        │  (delegates each phase to ecc agents; two human gates)
        ▼
/verify  +  /test-coverage  →  /code-review  →  /prp-pr (or /pr)
```
 Variants: `orch-build-mvp` (from spec doc), `orch-change-feature`, `orch-refine-code` (behavior-preserving).

### E. Adversarial / competitive generation
```
/gan-build  (or gan-style-harness)   generator ⇄ evaluator iterate until score threshold
        │  alternatives: /multi-workflow (multi-model), do-competitively-style 3 candidates
        ▼
/santa-loop   two independent reviewers must both approve
```

### F. Continuous improvement / RCA
```
[Explore / general-purpose]  reproduce the symptom, trace the call chain (logs + stack)
        │
        ▼  [ecc, after restart]
agent-introspection-debugging  +  click-path-audit  +  production-audit   →  root cause + A3-style writeup
        │
        ▼
/orch-fix-defect  (reproduce→fix→review→commit)  →  /verify  →  /learn  (capture the lesson)
```

---

## 9. Reusable workflow scripts — `.claude/workflows/`

| Script | Invoke | Chain |
|---|---|---|
| `diagram-generation.mjs` | `Workflow({scriptPath:".claude/workflows/diagram-generation.mjs", args:{target:"./backend", kinds:["c4","erd","sequence"], out:"docs/diagrams/backend.md"}})` | §8A |
| _(more to come: `code-review.mjs`, `deep-research.mjs` — say the word)_ | | §8B, §8C |

Scripts are plain JS (no TS), use `agent()`/`parallel()`/`pipeline()`/`phase()`, and persist
themselves to the session dir on first run. Re-invoke with `scriptPath` to iterate.

---

## 10. The orchestrator skill — `command-library`

A skill at `.claude/skills/command-library/SKILL.md` that routes a natural-language intent to the
right command or chain from this library. Invoke with `/command-library <intent>` (after restart)
or just describe what you want and Claude loads it by description match. It reads this doc, picks
the chain, and either runs the matching workflow script or sequences the commands.

---

## Appendix: environment ground-truth (2026-07-10)

- ecc plugin: user-scoped (universal) — **restart required** to activate.
- `~/.claude/skills/`: emptied 2026-07-10 — ~90 legacy skills removed (backup at `~/.claude/_skills_backup_2026-07-10`); ecc skills remain in the plugin cache.
- `gh` CLI: absent. `uv`: 0.10.8. `graphifyy`: v0.8.40 (`graphify` + `graphify-mcp`). `node`: v24.
- `mmdc`: absent (diagram render falls back to Mermaid-CDN HTML; optional `npx -y @mermaid-js/mermaid-cli`).
- MCP servers configured: `Docs_by_LangChain` only. Ruflo MCP: **not connected**.
- Available Agent types now: `general-purpose`, `Explore`, `Plan`, `claude`, `claude-code-guide`, `statusline-setup`. +67 ecc agents after restart.
- Data dumps: `docs/_ecc_catalog.json` (277 skills), `docs/_ecc_cmd_agents.json` (92 cmds + 67 agents).