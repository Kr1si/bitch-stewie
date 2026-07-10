---
name: delegate-coding-task
description: Working agreement and delivery format for a delegated coding session. Use for every delegated coding task in this repository.
---

# Delegated coding task — working agreement

You are working directly in this repository as a delegated Claude Code session.
The brief gives you the goal, constraints, acceptance criteria, and reference
examples; this skill is the contract that does not change per task.

## How to work

1. Work directly in this repository; create a feature branch and commit your
   work there.
2. Run the project's tests if present; do **not** finish with failing tests.
3. Record any architecture-significant choice via the `record_decision` tool
   (assistant-memory MCP server).

## Delivery format

When the task is complete, output exactly one final line of the form:

```
ASSISTANT_RESULT_JSON: {"branch": "...", "commits": ["..."], "summary": "...", "tests": "passed|failed|none"}
```

That JSON line is parsed by the orchestrator to record the run outcome, so keep
it valid JSON on a single line. Nothing after that line is read as a result.