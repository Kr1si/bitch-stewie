---
name: delegate-coding-task
description: How to turn user intent into a high-quality brief and delegate it to Claude Code. Use whenever the user wants code written, changed, or reviewed in a repository.
---

# Delegating a coding task

1. The project (and its `repo_path`) is already fixed for this session and
   resolved automatically — no need to look it up.
2. Compose the brief before calling the tool:
   - **Goal**: one paragraph, outcome-oriented, no implementation dictation.
   - **Constraints**: hard rules only (frameworks, style, files not to touch).
   - **Acceptance criteria**: verifiable statements (tests pass, endpoint returns X).
3. Call `delegate_coding_task`. Set `parallel=True` ONLY when the work splits into
   independent parts that touch different files.
4. The delegation is milestone-gated: the user approves before it starts. The
   delegated session receives its working agreement and delivery format from the
   `delegate-coding-task` skill staged into its repo — do not restate them in the brief.
5. After it returns, report the outcome faithfully — branch, commits, tests,
   review verdict. Never claim success when status is failed.
6. If the result matters architecturally, record it with `record_decision`.