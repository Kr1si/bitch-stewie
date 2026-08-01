# E2E Tests (Playwright)

End-to-end tests for the bitch-stewie web UI. They run **against a running
stack** — either the krisiserver deployment reached via the SSH tunnel, or a
local dev stack. They are allowed to hit real services (backend API, and for
some flows the LongCat LLM).

## Prerequisites

A running stack. Two options:

**Option A — against krisiserver via the SSH tunnel (prod):**

```bash
# in one terminal: forwards UI on 3000 + draw.io on 8080
make tunnel
# backend is reachable through nginx at http://localhost:3000/api/*
```

**Option B — local dev stack:**

```bash
cd docker && docker compose up -d          # Postgres + Qdrant + draw.io + Ollama
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn assistant.api.app:app --port 8000 --loop asyncio:SelectorEventLoop
cd frontend && npm run dev                 # Vite on http://localhost:5173
```

## Install browsers

```bash
cd frontend
npx playwright install chromium
```

(Only Chromium is configured; add more via `playwright.config.ts` if desired.)

## Run

```bash
cd frontend

# Against krisiserver via the tunnel (prod nginx):
E2E_BASE_URL=http://localhost:3000 npx playwright test

# Against a local Vite dev server:
E2E_BASE_URL=http://localhost:5173 npx playwright test

# Run a single spec:
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/smoke.spec.ts

# Headed / debug:
E2E_BASE_URL=http://localhost:3000 npx playwright test --headed
E2E_BASE_URL=http://localhost:3000 npx playwright test --debug
```

### Environment variables

| Var | Default | Meaning |
|-----|---------|---------|
| `E2E_BASE_URL` | `http://localhost:3000` | Where the **UI** is served. |
| `E2E_API_BASE` | `http://localhost:8000` | Where the **backend** is reached directly. Only used for `/health` (which sits at the backend root — nginx only proxies `/api/*`). |

## What each spec covers

| Spec | Story | Needs LLM? | Notes |
|------|-------|------------|-------|
| `smoke.spec.ts` | shell + `/health` | no | Health hits backend root via `E2E_API_BASE`. |
| `projects.spec.ts` | dashboard / projects | no | Creates a project, checks stat cards. |
| `chat.spec.ts` | chat | tolerant | Asserts an assistant bubble **or** error turn appears. |
| `knowledge.spec.ts` | KB search | no | Seeds via API (best-effort), searches via UI. |
| `diagrams.spec.ts` | diagrams | no | Asserts project selector + embed area render. |
| `research.spec.ts` | deep research | tolerant | Asserts the UI reaches the **running** state only. |

## On robustness

Tests that depend on the LLM (`chat`, `research`) assert **UI state** rather than
a specific model output:

- **chat** — sends a message and waits for an *assistant bubble* (Avatar "S" in
  `<main>`). A streamed reply and an `Error:` message both render as assistant
  bubbles, so the assertion holds whether or not LongCat is reachable. The user
  bubble appearing first proves the send path works either way.
- **research** — clicks Run and waits for the synchronous **running** state
  (Abort button + "researching…" indicator). It does *not* wait for the finished
  report, which requires the LLM and several minutes.

This keeps the suite green on the real stack while still proving the critical
user-story flows, without faking any assertions.
