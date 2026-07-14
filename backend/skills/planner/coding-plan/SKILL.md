---
name: coding-plan
description: Shape a plan for implementation work so it maps cleanly onto delegate_coding_task's brief later — goal, constraints, acceptance criteria, repo/project, risks. Use when the plan describes code to be written, changed, or reviewed.
---

# Shaping a coding plan

Coding plans exist to do the thinking up front so that when the plan is
handed to the orchestrator, it can turn it into a `delegate_coding_task`
brief with minimal further back-and-forth with the user. Shape the plan the
same way that brief is shaped (see the orchestrator's `delegate-coding-task`
skill) so the mapping is direct.

## When to use this shape

Use it whenever the plan's outcome is code: a feature, a fix, a refactor, an
API change, infra/config changes tracked in a repo.

## Plan body structure

- **Goal**: one paragraph, outcome-oriented. Describe the result, not the
  implementation — leave *how* to the delegated coding session.
- **Project / repo**: already fixed for this session (resolved automatically
  from the project registry) — no need to look it up or confirm it.
- **Constraints**: hard rules only — frameworks to use, files or areas not to
  touch, style/conventions to follow, things that must NOT change.
- **Acceptance criteria**: verifiable statements. "Tests pass", "endpoint
  `/api/x` returns 201 with the new field", "no change to `Chat.tsx`
  internals" — not vague quality judgments.
- **Risks / open questions**: anything uncertain enough that the delegated
  session (or the user) should be alerted before or during execution.

## Done when

The plan itself is "done" (ready to hand off) once goal, constraints, and
acceptance criteria are concrete enough that they could be pasted directly
into a `delegate_coding_task` brief without further clarification from the
user. If you find yourself still asking "what should happen when..." keep
iterating with the user before marking it `in_progress`.
