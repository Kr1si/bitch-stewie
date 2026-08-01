import { test, expect } from "@playwright/test";
import { uniqueProjectName } from "./helpers";

/**
 * Story 9 — Projects registry + Story 10 dashboard aggregates.
 * Creates a project via the Dashboard form and asserts it lands in the table;
 * asserts the stat cards render.
 */
test.describe("dashboard / projects", () => {
  test("create a project via the form; it appears in the table", async ({ page }) => {
    const name = uniqueProjectName();
    await page.goto("/dashboard");

    await page.getByPlaceholder("project name").fill(name);
    await page.getByRole("button", { name: "Create" }).click();

    // The projects table reloads after creation; the new row shows the name.
    const row = page.getByRole("row", { name });
    await expect(row).toBeVisible({ timeout: 20_000 });
  });

  test("stat cards render on the dashboard", async ({ page }) => {
    await page.goto("/dashboard");

    // StatCard labels (uppercased via CSS, but text content is as written).
    for (const label of ["Projects", "CC Runs", "Pending", "Decisions", "KB Chunks", "KB Sources"]) {
      await expect(page.getByText(label).first()).toBeVisible();
    }
  });
});
