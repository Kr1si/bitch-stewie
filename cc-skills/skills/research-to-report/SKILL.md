---
name: research-to-report
description: Produce a research report for the assistant orchestrator. Use when asked to run /deep-research on a question and return a report.
---

# Research to report

1. Run the native /deep-research flow on the question. Do not ask clarifying
   questions — state assumptions inline.
2. Output a single Markdown report: ## Summary (5 bullets max), ## Findings
   (grouped by sub-question, every claim cited with its URL), ## Implications
   (what this means for the decision at hand), ## Sources.
3. Prefer primary sources; mark anything you could not verify as UNVERIFIED.
   The report is ingested verbatim into a knowledge base — keep it
   self-contained (no "as mentioned above" references to the conversation).
