# bitch-stewie — project rules

See `.claude/rules/*.md` for standing conventions Claude Code must follow
in this repo. Currently:

- [`git-workflow.md`](.claude/rules/git-workflow.md) — never push directly
  to `main`; always work on a feature branch and let the user merge.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

# Working style — fan out & deep research

- **Default to fan-out.** For any multi-step task (searching, refactoring, reviewing, building), prefer spawning parallel subagents over doing work sequentially in the main thread. Send concurrent `Agent` tool calls in a single message whenever the sub-tasks are independent.
- **Use the `deep-research-review` skill for research.** For any research-shaped task — "research X and review it", a broad topic sweep, competitive analysis, design-decision research, or anything that should end in a cited report — invoke the `deep-research-review` skill instead of ad-hoc web searching. It fans research into parallel sub-questions, adversarially verifies claims, and produces a cited report.
- **Ask before big fan-outs only when ambiguous.** If the task is clear, fan out immediately; don't stop to propose a plan first.
