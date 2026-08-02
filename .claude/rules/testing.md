# Testing: always verify live — never claim "it works" from unit tests alone

A feature is not done until it has been **observed running** against real
infrastructure. Unit tests that import a model or assert a router returns the
right string do NOT prove the feature works — they prove the code loads.

## The rule

**Every feature must be tested live before you report it working.**

- Backend feature that touches the DB, the LLM, jobs, or the KB? Spin up the
  local stack (`make infra` starts Postgres + Qdrant) and exercise the real
  code path — run the endpoint, trigger the job, ingest a doc, search it.
- Frontend feature? Run it against a live backend and click through the flow.
- A graph / agent / pipeline? Invoke it end-to-end and confirm the output
  (the report exists, the goal row was created, the job ran), not just that it
  compiles.

## When local testing is genuinely blocked

Sometimes a feature can't run locally: it needs a secret only on krisiserver,
a GPU, a remote service, etc. In that case:

1. **Say so explicitly.** "I could not test this locally because X." Name the
   exact blocker, don't vague it.
2. **Do not claim it works.** Say "code written, unverified" — never "done" or
   "working."
3. **Stop and ask the user** how they want to proceed. Do not commit a
   "done" feature you have not run and move on as if it shipped.

## Why

A feature that passes unit tests but fails on first real invocation is worse
than useless — it ships broken and wastes a deploy. The Makefile and
docker-compose exist precisely so the full stack runs locally. Use them.
