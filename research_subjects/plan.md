# / — Plan (repository root)

## Purpose
Root of the Netherbrain monorepo: a self-hosted knowledge platform (MCP server + librarian pipeline + RAG + agents + Nx React frontend). This plan.md is the entry point of the plan tree — every folder below has its own plan.md refining this one.

## Scope & boundaries
Root holds only: cross-cutting docs (ARCHITECTURE.md, MASTER_PLAN.md, CLAUDE.md), the Makefile, and top-level folders. No source code at root. Backend code only under `backend/`, FE only under `frontend/`, deployment only under `deploy/`.

## Contents
- `ARCHITECTURE.md` — system design, DDD contexts, the 13 LangGraph rules, typing + testing strategy
- `MASTER_PLAN.md` — phased roadmap with per-phase definitions of done
- `CLAUDE.md` — dev harness: hard rules, command playbook, pre-commit gates, skillify rule
- `Makefile` — single entry point for all dev/CI targets (placeholder until Phase 0)
- `backend/` `frontend/` `deploy/` `bundle_spec/` `docs/` — see their plan.md files
- `.claude/skills/` — project skills (netherbrain-conventions, netherbrain-workflow-authoring, netherbrain-testing)

## Contracts
The Makefile target names are a public contract used by CI and docs: `up down migrate seed lint typecheck test check test-integration e2e logs`.

## Dependencies
None at root. Tooling: uv (backend), Nx/pnpm (frontend), docker compose (deploy).

## Testing
Root-level: CI wiring runs `make check`, `make test-integration`, `make e2e` (backend) and `nx affected -t lint,typecheck,test` (frontend). See `backend/tests/plan.md`.

## Dev workflow
Any session: read CLAUDE.md first; then the plan.md of the folder being touched. Phase kickoff: `/ecc:plan`. Root docs upkeep: `/ecc:update-docs`.

## Phase
Step A creates this tree; Phase 0 turns the Makefile into real targets and wires CI. See MASTER_PLAN.md.
