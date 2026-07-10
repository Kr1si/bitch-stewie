# plans/

Dated markdown files recording **future improvements** — work the orchestrator
devises but isn't executing in the current session. This folder is how the
orchestrator builds a backlog for itself and iterates on it over time.

## Convention

Each file is `YYYY-MM-DD-<slug>.md` with frontmatter:

```markdown
---
status: proposed      # proposed | in_progress | done | dropped
created: 2026-07-10
project: bitch-stewie
---

# <title>

**Goal:** the outcome, one paragraph.
**Why:** the force behind it (a gap, a pain, a blocker).
**Approach:** concrete steps / files / tools to touch.
**Done when:** verifiable acceptance criteria.
**Risks / open questions:** what's uncertain.
```

## How plans get here

The orchestrator writes them via its `write_plan` tool (see the
`plan-improvement` skill). It reads them back with `list_plans` at the start of
an improvement session. You can also author one by hand — same format.

## Status lifecycle

`proposed` → `in_progress` → `done` (merged & verified) | `dropped` (decided
not to). Rewriting a plan with a new status on a new date appends history; the
same date+slug overwrites (treat as an in-place update).

## Self-improvement note

Plans that target the orchestrator itself (project `bitch-stewie`,
`repo_path=/projects/bitch-stewie`) only reach the **running** orchestrator
after the plan's resulting PR is merged and CI redeploys — no hot-reload. State
that gate in any self-improvement plan so no one expects a mid-session effect.