---
name: architecture-decision
description: Capture significant architecture decisions in the ADR log. Use when a technology choice, trade-off resolution, or structural decision is made in conversation.
---

# Recording architecture decisions

Record a decision (`record_decision`) when the conversation settles any of:
- a technology/library/pattern choice between alternatives,
- a trade-off with consequences (perf vs simplicity, build vs buy),
- a structural boundary (service split, ownership, data flow).

Write it ADR-style:
- **title**: short imperative ("Use Qdrant hybrid search for the KB"),
- **context**: the forces — why a decision was needed,
- **decision**: what was chosen (and what was rejected),
- **consequences**: what becomes easier/harder.

Check `list_decisions` first: if this supersedes an earlier decision, say so in
the new entry. Don't log trivia (renames, formatting, obvious defaults).
