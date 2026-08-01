import { test, expect } from "@playwright/test";

/**
 * Story 6 — diagrams. Asserts the project selector and the draw.io embed area
 * render. With no project selected the embed area shows a placeholder; selecting
 * a project swaps in either the editor or a "no diagrams yet" message. We keep
 * the assertion on the controls rendering (no backend diagrams required).
 */
test.describe("diagrams", () => {
  test("project selector + draw.io embed area render", async ({ page }) => {
    await page.goto("/diagrams");
    await expect(page.getByRole("heading", { name: "Diagrams" })).toBeVisible();

    // Project selector (MUI Select renders a combobox button labelled "Project").
    const projectSelect = page.getByRole("combobox", { name: "Project" });
    await expect(projectSelect).toBeVisible();

    // The embed area: with no project selected it shows this placeholder.
    await expect(page.getByText("Select a project to view its diagrams.")).toBeVisible();
  });
});
