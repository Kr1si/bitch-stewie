import { test, expect } from "@playwright/test";

/**
 * Story 5 — deep research. Typing a goal and clicking Run kicks off a minutes-long
 * Claude Code /deep-research run. We assert the UI reaches the RUNNING state
 * (Abort button + "researching…" indicator), which appears synchronously on click
 * — we do NOT wait for the full report (that needs the LLM and several minutes).
 */
test.describe("deep research", () => {
  test("launching a run reaches the running state", async ({ page }) => {
    await page.goto("/research");
    await expect(page.getByRole("heading", { name: "Deep Research" })).toBeVisible();

    const goal = page.getByPlaceholder(/State the research goal/);
    await goal.fill("Compare vector DB options for a small RAG prototype.");

    await page.getByRole("button", { name: "Run Deep Research" }).click();

    // Running state: Abort button appears, plus the "researching…" indicator.
    await expect(page.getByRole("button", { name: "Abort" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/researching… this can take several minutes/)).toBeVisible();
  });
});
