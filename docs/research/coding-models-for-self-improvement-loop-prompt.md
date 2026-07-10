# Deep-research prompt: cheap flagship coding models for the self-improvement loop

A reusable, self-contained deep-research brief. Paste into a deep-research tool
(`/deep-research`) or hand to a research agent. Output should answer the two
questions at the end with comparison tables, token math, and a clear pick.

## Objective

Compare **affordable flagship coding models** that can drive **Claude Code** as
the worker in a self-improving coding orchestrator, across two axes:
1. **Per-token API pricing** (and capability / Claude-Code protocol fit).
2. **Flat-rate coding plans/subscriptions** (pricing, quota mechanics, constraints).

Then answer, grounded in our use case:
- **Q1:** What is the best model for coding tasks in Claude Code that doesn't
  cost an arm and a leg?
- **Q2:** Should we pay per token or use a coding plan? Which is better for our
  usage, and what are the constraints (token/prompt quotas, resets, multipliers,
  client-lock-in)?

## Use-case context (the self-improvement loop)

A LangGraph/deepagents orchestrator ("bitch-stewie") that runs **Claude Code
(CC)** as the worker to iteratively improve its own Python/TS codebase. Two LLM
consumers with very different profiles:

1. **CC worker (heavy, capability-critical).** Long-horizon agentic coding on
   the orchestrator's own repo: reads repo context (~50-150K tokens), iterates
   over many tool rounds (20-80 rounds per delegation), edits files, runs tests,
   self-reviews via `/code-review`, opens a PR. CC speaks the **Anthropic
   Messages API**, so a provider must either expose a **native Anthropic
   Messages endpoint** or be reachable via a **translating proxy** (LiteLLM /
   claude-code-proxy) — proxy adds a component to run/debug and can break on
   tool-use/streaming. 1M context is helpful but not mandatory; a large
   **max-output window** helps for big diffs. This is where capability matters
   most: the model must be strong at **long-horizon, repo-scale, multi-step
   agentic engineering**, not just single-shot codegen.
2. **Orchestrator planner + sub-agents (light, high token volume).**
   High-level planning, delegation, tool-routing. Lighter reasoning; benefits
   from prefix caching / cheap or free tier. Can use any OpenAI- or
   Anthropic-compatible endpoint via LangChain (no proxy needed). 200K context
   is plenty.

**Usage cadence: SERIAL and human-gated.** The user triggers ~1-5
self-improvement queries/day when actively iterating, ~0-1/day at steady state.
Each query = one CC delegation session. So volume is **low-to-moderate, bursty,
not 24/7**. One improvement at a time; the user reviews each PR before merge.
This cadence is decisive for the metered-vs-plan question.

## Model universe to investigate

Cover at minimum (and add any similarly-positioned cheap coding flagships you
find, e.g. Qwen3-Coder, DeepSeek V4 Pro/Flash as a reference, Grok coding):
- **GLM-5.2** + lighter GLMs (GLM-4.7-Flash free, GLM-4.5-Air, GLM-4.7) — Z.ai
- **Kimi K2.x** (latest flagship Kimi coding model) — Moonshot AI
- **MiniMax** flagship coding model (e.g. MiniMax-M1/M2) + lighter variant
- **LongCat** (Meituan) coding model(s)
- **Mistral Devstral** (+ Codestral) — Mistral (EU)
- Any other strong-but-affordable coding model you surface

## Dimensions to capture for EACH model

1. **Identity** — provider, exact current model id, release date, params (MoE
   total/active), license, jurisdiction (China / EU / US — flag privacy/data
   processing location).
2. **API pricing (USD per 1M tokens)** — input, **cached-input**, output.
   Explicitly flag **promo vs list** pricing and any **expiry date** (do not
   repeat expired-promo numbers as if current).
3. **Context window + max output tokens.**
4. **Coding power — benchmarks.** Especially the **long-horizon agentic** ones
   that predict our use case: **SWE-bench Pro, FrontierSWE, DeepSWE,
   Terminal-Bench**. Also SWE-bench Verified, LiveCodeBench, Codeforces. Flag
   that numbers are usually **vendor self-reported** and note any independent
   evals (e.g. NIST/CAISI).
5. **Claude Code protocol fit** — native Anthropic Messages endpoint (give the
   exact base URL)? OpenAI-only (needs proxy — note the proxy + its risks)?
   Any official "X for Claude Code" docs/integration? Known CC feature loss
   through the endpoint (e.g. `/ultrareview`, task budgets, xhigh effort,
   signed skills). Known tool-result-drop issues on long agentic loops.
6. **Coding plan / subscription** — name, monthly + yearly price, **quota
   mechanics** (prompts per window? tokens? requests? the reset window —
   5-hour cycle / daily / weekly), **peak-hour multipliers**, **model-tier
   restrictions** (can each tier use the flagship? does the flagship consume
   quota faster?), **client/tool lock-in** (is the plan usable only through
   supported apps like CC/Cline/Goose, or also for arbitrary programmatic API
   calls — critical because our LangChain planner calls the API directly).
7. **API rate limits** (metered).
8. **Known issues / reliability** — outages, tool-result handling, latency on
   large context (first-token latency for 1M-context calls).

## Cross-cutting analysis required

- A single **API pricing comparison table** (all models, in/out/cached per 1M,
  context, max-output, jurisdiction) sorted by output price.
- A single **coding-plan comparison table** (provider, plan, price, quota
  mechanics, reset, multipliers, model restrictions, client-locked?,
  works-with-CC?).
- A **capability ranking for long-horizon agentic coding** (our use case's
  decisive axis), separate from competitive-programming / single-shot SWE
  scores.
- A **protocol-fit summary**: which models work with CC natively vs need a
  proxy.
- **Token math for our usage.** Estimate tokens per CC delegation (repo context
   ~50-150K warm-up cache-miss + 20-80 rounds, mostly cache-hit prefix
   afterward, + 5-30K output) and per planner query. Then, for ~1-5
   delegations/day active and ~0-1/day steady, compute:
   - expected **metered cost per day/week/month** per candidate model (split
     worker vs planner, and note cache-hit savings where the provider auto-caches),
   - whether each **coding plan's quota** would cover that usage, and at what
     delegation frequency each plan tier breaks even vs metered.
- **Constraints list** per plan: token/prompt caps, reset windows, peak
  multipliers, model restrictions, and especially **client-lock-in** (a plan
  that only works through the CC client can't cover the programmatic planner,
  so the planner must run on metered/free regardless — factor that in).

## Questions to answer (deliverables)

**Q1 — Best model for coding in Claude Code that doesn't cost an arm and a leg.**
Give: a primary pick for the **CC worker** (best long-horizon agentic coding per
dollar, native CC protocol preferred), a pick for the **planner** (cheap/free,
agent-capable), and a one-paragraph rationale each. Include a runner-up and the
trade-off. Note protocol/proxy implications and any CC feature loss.

**Q2 — Pay per token or use a coding plan?** Give: a recommendation for our
LOW-to-MODERATE serial usage (which is cheaper, by how much, at what delegation
frequency the answer flips), the **constraints** of the recommended plan
(quota, reset, multipliers, model/client restrictions), and the gotchas
(client-lock-in for the planner; expired-promo pricing traps; quota drain
multipliers for flagship models). Provide a simple breakeven table: delegations
per day → metered cost vs each plan tier.

## Research rules

- Prefer **official provider docs/pricing pages**; cite URLs for every number.
- Never present **promo pricing** as current without noting the expiry; re-fetch
  to confirm whether a promo is still active as of today.
- Flag **vendor self-reported** benchmarks; prefer independent evals where they
  exist.
- If something can't be confirmed, say "not found" — do not guess prices or
  quotas.
- Keep jurisdiction/privacy explicit (Chinese vs EU vs US providers) since the
  worker reads/edits the orchestrator's own source.
- End with a **Sources** list (markdown links).