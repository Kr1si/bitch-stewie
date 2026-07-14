---
name: research-plan
description: Shape a plan for a "figure out X" investigation — scoping local knowledge base vs deep web research, with a clear done-when. Use when the plan's goal is to answer a question or gather information rather than build or design something.
---

# Shaping a research plan

Research plans exist to scope an investigation before it runs, so the
research subagent (or a later planning session) knows exactly what "answered"
looks like and doesn't over- or under-spend on `deep_research`.

## When to use this shape

Use it when the user's goal is "figure out X", "find out whether Y",
"understand how Z works" — an information-gathering task, not code or a
design decision.

## Plan body structure

- **Question**: the precise question(s) to answer, not the topic area.
  "What auth libraries support X" is answerable; "learn about auth" is not.
- **Scope**: what's in vs. out of bounds. Local knowledge base
  (`search_knowledge`) first — is this likely already covered by ingested
  material? Only reach for `deep_research` (expensive, cites live web
  sources) when the question needs current or external information.
- **Sources**: any specific sources, repos, or docs to prioritize, if known.
- **Done when**: the question is answered with citations, or a specific
  negative result is confirmed ("no such library exists" is a valid answer).
  Vague completion criteria ("understand the space") make a research plan
  impossible to close out — tighten them before writing the plan.

## Handoff

Research plans typically don't need Claude Code delegation — the orchestrator
can act on them directly by running research_subagent tools once handed off.
Keep the plan short; the findings belong in a research report, not the plan
file itself.
