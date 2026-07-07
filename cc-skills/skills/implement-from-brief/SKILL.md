---
name: implement-from-brief
description: Execute a delegated coding brief from the assistant orchestrator. Use when the prompt is titled "Delegated coding task".
---

# Implementing a delegated brief

You received a brief with Goal / Constraints / Acceptance criteria / Working
agreement. Non-negotiables:

1. Work on a feature branch named for the goal (`feature/<slug>`); commit with
   clear messages. Never commit to main.
2. Satisfy every acceptance criterion; treat constraints as hard limits.
3. Run the repo's tests (or the ones you add); never finish with failing tests.
4. Consult the `assistant-memory` MCP server: `get_preferences` for the user's
   conventions before writing code; `record_decision` if you make a choice the
   architect should know about.
5. Use native skills for quality: /code-review before declaring done; verify
   behavior by running the code, not just reading it.
6. End with the exact structured result line the brief requests
   (ASSISTANT_RESULT_JSON) — the orchestrator parses it.
