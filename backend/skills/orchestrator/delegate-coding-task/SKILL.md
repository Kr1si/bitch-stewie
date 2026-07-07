---
name: delegate-coding-task
description: How to turn user intent into a high-quality brief and delegate it to Claude Code. Use whenever the user wants code written, changed, or reviewed in a repository.
---

# Delegating a coding task

1. Resolve the project: `list_projects` — use its registered `repo_path`. If the
   project is missing, register it first (ask the user for the repo path).
2. Compose the brief before calling the tool:
   - **Goal**: one paragraph, outcome-oriented, no implementation dictation.
   - **Constraints**: hard rules only (frameworks, style, files not to touch).
   - **Acceptance criteria**: verifiable statements (tests pass, endpoint returns X).
3. Call `delegate_coding_task`. Set `parallel=True` ONLY when the work splits into
   independent parts that touch different files.
4. The delegation is milestone-gated: the user approves before it starts. After it
   returns, report the outcome faithfully — branch, commits, tests, review verdict.
   Never claim success when status is failed.
5. If the result matters architecturally, record it with `record_decision`.
