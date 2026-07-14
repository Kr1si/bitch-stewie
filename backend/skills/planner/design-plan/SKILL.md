---
name: design-plan
description: Shape a plan for architecture or diagram work — what's being decided, alternatives considered, tradeoffs, and C4-model impact. Use when the plan's outcome is an architecture decision or a change to the LikeC4 model/diagrams.
---

# Shaping a design plan

Design plans exist to make an architecture decision legible before it's
acted on — either recorded via `record_decision` directly, or delegated as a
coding task that edits the LikeC4 model.

## When to use this shape

Use it when the plan is about *deciding* something architectural: a new
component, a boundary change, a technology choice, a diagram restructure —
not routine implementation of an already-settled design.

## Plan body structure

- **Decision**: the single question being resolved, stated precisely (e.g.
  "sync mechanism between planner and orchestrator sessions").
- **Alternatives**: the options actually considered, even briefly rejected
  ones — this is what makes the decision defensible later.
- **Tradeoffs**: for each alternative, what it costs and what it buys.
  Be concrete about latency, complexity, operational burden, blast radius.
- **C4-model impact**: which level (context/container/component/code) the
  change touches, and whether it requires updating the LikeC4 model and
  regenerating diagrams (`update_diagrams`) once implemented.
- **Done when**: the decision is recorded (`record_decision`) and, if it
  requires a model change, that change has been delegated and diagrams
  regenerated.

## Handoff

If the decision requires editing the LikeC4 model, the resulting coding-plan
work should go through `delegate_coding_task` like any other code change —
don't try to hand-edit the model from the planner.
