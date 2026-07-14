---
name: plan-improvement
description: Record a future improvement as a dated plan file in the project's plans/ folder so later iterations can discover and act on it. Use when you devise an improvement you are NOT executing right now, or when starting an improvement session.
---

# Planning a future improvement

Improvements you devise but don't execute immediately get lost. Write them down
in the project's `plans/` folder so a later session can pick them up and
iterate. This is how the orchestrator improves itself over time.

## When to write a plan

Call `write_plan` whenever:
- you and the user agree on an improvement but aren't executing it in this
  session (e.g. "we'll add cron-triggered workflows later"),
- you finish a session and spot a clear next step worth recording,
- you're asked to "plan X for later" / "put that on the backlog".

Do NOT write a plan for work you are delegating right now — the delegation brief
and `record_decision` cover that. Plans are for *future* work.

## When to read plans

At the start of any improvement session, call `list_plans` first. If relevant
plans exist (status `proposed` or `in_progress`), read them and continue from
there rather than replanning from scratch. Update a plan's status by rewriting
it (`write_plan` with the same date+slug overwrites; a new date appends history).

## Plan file format

`write_plan(slug, markdown, status)` writes
`<repo>/plans/YYYY-MM-DD-<slug>.md` with frontmatter:

```
---
status: proposed      # proposed | in_progress | done | dropped
created: 2026-07-10
project: bitch-stewie
---
```

The `markdown` body should be short and actionable:
- **Goal**: the outcome, one paragraph.
- **Why**: the force behind it (a gap, a pain, a blocker).
- **Approach**: the concrete steps / files / tools to touch.
- **Done when**: verifiable acceptance criteria.
- **Risks / open questions**: what's uncertain.

Keep it to a page. Detail goes in the delegation brief when the plan is
executed, not here.

## Status lifecycle

`proposed` → `in_progress` (when a session starts executing it) → `done` (merged
& verified) or `dropped` (decided not to). Move a plan forward by rewriting it
with the new status; the dated filename keeps the history visible.

## Self-improvement

When the improvement targets this orchestrator itself, the project is
`bitch-stewie` (registered preset, `repo_path=/projects/bitch-stewie`). Plans
land in `/projects/bitch-stewie/plans/`, get committed on a feature branch by
the delegated Claude Code session, and reach the running orchestrator only after
the user merges the PR and CI redeploys — there is no hot-reload. A
self-improvement plan should state that gate explicitly so no one expects the
change to take effect mid-session.