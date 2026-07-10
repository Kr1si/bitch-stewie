---
status: proposed
created: 2026-07-10
project: bitch-stewie
---

# Migrate the LLM provider to Z.ai direct (GLM-5.2, 1M context)

**Goal:** Serve **GLM-5.2 (1M context)** to the delegated Claude Code worker and
a **lighter GLM (4.7-Flash, free)** to the orchestrator's planner/sub-agents —
both via Z.ai's API directly, removing the Ollama hop, so the self-improvement
loop runs on one key with the fewest moving parts.

**Why:** Research on 2026-07-10 (see `docs/findings/2026-07-10.md` §3a) compared
Z.ai direct vs Ollama cloud vs NVIDIA NIM for the same model. Z.ai direct is
cheapest per-token, has the largest output window (~128K), and is the
purpose-built Claude Code integration. NVIDIA is OpenAI-only (needs a proxy,
records data, 40 RPM, not for production). Ollama cloud is the zero-code-change
way to get the loop live today but adds a hop and possible margin. Plan: start
on Ollama cloud, migrate to Z.ai direct once stable.

**Approach:**
1. **Unblock (Ollama cloud, interim):** `ollama signin` + `ollama pull
   glm-5.2:cloud` in `assistant-ollama`. Covers CC (via `ollama:11434`
   Anthropic-compat) AND the planner (already `ollama:glm-5.2:cloud`) with no
   code change. Get the loop running end-to-end first.
2. **CC → Z.ai direct:** in `docker/.env` set
   `ASSISTANT_CC_ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic`,
   `ASSISTANT_CC_ANTHROPIC_AUTH_TOKEN=<Z.ai key>`. Add to `runner.py` env the
   model mapping `ANTHROPIC_DEFAULT_SONNET_MODEL=glm-5.2[1m]` (and opus) so CC
   actually gets GLM-5.2 + 1M context — **without this Z.ai silently serves
   GLM-4.7.** Make these mapping vars env-configurable in `config.py`.
3. **Planner → Z.ai OpenAI-compat endpoint on a lighter model:** change
   `ASSISTANT_DEFAULT_MODEL` to a LangChain `ChatOpenAI`-style model string
   pointing at `https://api.z.ai/api/paas/v4` with the Z.ai key. Use a **lighter
   GLM model for the planner/sub-agents** (they plan/delegate, not codegen):
   - **`glm-4.7-flash` (FREE)** — default pick; agent-oriented, 200K context.
   - Fallback if free-tier rate-limits or reasoning is weak: `glm-4.5-air`
     ($0.20/$1.10) or `glm-4.7` ($0.60/$2.20, SWE-Verified 73.8%). Same Z.ai key.
   Using the OpenAI-compat endpoint for the planner avoids the Anthropic-endpoint
   tool-result-drop issue (finding #2). Add `ASSISTANT_DEFAULT_MODEL` +
   `ASSISTANT_OPENAI_BASE_URL`/key to compose `environment:` (literal or
   `${VAR:-default}`). Stay all-Z.ai — do **not** add DeepSeek (its "3-5×
   cheaper" claim was expired promo pricing; Z.ai's free Flash beats it and
   avoids a second key).
4. **Drop Ollama** from the prod stack once neither consumer uses it (remove the
   `ollama` service + `ollama_data` volume + `ASSISTANT_OLLAMA_BASE_URL`).
5. **Verify:** one chat query → plan → delegate to a scratch repo → confirm CC
   logs show `model=glm-5.2[1m]` and 1M context, no tool-result drops over a
   multi-step delegation.

**Done when:**
- Both CC and the planner hit Z.ai on one key; `ollama` container is gone.
- CC sessions report GLM-5.2 (not the auto-mapped GLM-4.7) with 1M context.
- The planner runs on `glm-4.7-flash` (or a paid Z.ai fallback) via the
  OpenAI-compat endpoint.
- A full chat→plan→delegate→PR delegation completes without tool-result loss.

**Risks / open questions:**
- Z.ai Anthropic endpoint may drop nested tool-result blocks on long agentic
  loops (known issue). If it bites CC, consider routing CC through a LiteLLM
  proxy against Z.ai's OpenAI-compat endpoint instead of the Anthropic endpoint
  directly.
- GLM Coding Plan quota drains 2–3× faster for GLM-5.2 (peak 14:00–18:00 UTC+8
  = 3×). Decide metered API vs Coding Plan by expected prompt volume.
- Confirm the `[1m]` 1M-context variant's first-token latency (30–90s) is
  acceptable for the planner; `API_TIMEOUT_MS=3000000` is already set for CC.
- Privacy: confirm Z.ai terms are acceptable for sending the orchestrator's own
  source (self-rewrite) to the provider.