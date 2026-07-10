---
name: command-library
description: Router for the project's command & workflow library. Use when the user asks for a multi-step workflow — code review, critique, deep research, diagram generation, plan→implement→verify, root-cause analysis, or "which command do I use for X" — to pick the right commands/agents and chain them. Reads docs/command-library.md and either runs a .claude/workflows script or sequences the matching commands.
---

# Command Library Router

You route a natural-language intent to the right command or chain from
`docs/command-library.md` (read it first — it is the source of truth).

## Step 1 — Classify the intent

Match the user's request to one of these chains. If unclear, ask one question
to disambiguate scope, then proceed.

| Intent | Chain | How to run |
|---|---|---|
| "Diagram / visualize / map the architecture / ERD / sequence of X" | §8A Diagram generation | **Workflow tool** with `scriptPath: ".claude/workflows/diagram-generation.mjs"` and `args` (see below) |
| "Review / critique this code or PR" | §8B Code review / critique loop | `/code-review` → adversarial verify (`santa-loop` after ecc restart) → fix → `/verify` → `/simplify` |
| "Research X / deep research / compare with sources" | §8C Deep research | `/deep-research "<question>"` (built-in) → adversarial verify claims → synthesize to `docs/research/<topic>.md` |
| "Plan and implement / build feature X" | §8D Plan→implement→verify | `/plan` (or `orch-add-feature` after ecc restart) → `/verify` → `/test-coverage` → `/code-review` → `/pr` |
| "Why is X happening / root cause / RCA" | §8F RCA | reproduce + trace (Explore) → ecc `agent-introspection-debugging` + `click-path-audit` + `production-audit` (after restart) → `/orch-fix-defect` → `/verify` |
| "Generate / evaluate competitively" | §8E Adversarial gen | `gan-build` (after restart) or `multi-workflow` → `santa-loop` |
| "Which command for X" / "list commands" | — | Answer from `docs/command-library.md` §2–§5; do not run anything |

## Step 2 — Run the diagram workflow (the implemented one)

When the intent is diagram generation, invoke the **Workflow tool** (not the Agent
tool) with:

```
Workflow({
  scriptPath: ".claude/workflows/diagram-generation.mjs",
  args: {
    target: "./backend",                 // path to analyze
    kinds: ["c4", "erd", "sequence", "component"],  // subset allowed
    out: "docs/diagrams/backend.md",     // output markdown path
    useGraphify: false                   // true → a mapper may call the graphify CLI
  }
})
```

The script fans out 4 parallel `Explore` mappers (structure, data, control-flow,
deps), synthesizes Mermaid diagrams via a `general-purpose` agent, and emits a
self-contained Mermaid-CDN HTML viewer. It returns `{ok, out, html, mapCounts}`.
Tell the user the resulting `.md` and `.html` paths.

For non-diagram chains, sequence the commands/agents listed in the table using
the Agent tool + Skill invocations, following the chaining rules in
`docs/command-library.md` §7 (orchestrator stays clean, context isolation,
verify-before-ship, files as shared memory).

## Step 3 — ecc restart caveat

ecc agents/commands (§2, §3, §4) are only live **after a Claude Code restart**
(the plugin was switched to user-scope on 2026-07-10). Before restart, use the
built-in skills (§5) + `general-purpose`/`Explore` agents. If a chain names an
ecc command/agent that isn't available yet, say so and use the built-in
fallback named in §8.

## Step 4 — Don't over-build

If only one chain matches, run it directly — do not enumerate every option.
If the user just wants the catalog, point them at `docs/command-library.md`.