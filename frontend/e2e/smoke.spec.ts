import { test, expect } from "@playwright/test";
import { API_BASE, backendHealthy } from "./helpers";

/**
 * Smoke test: the SPA shell renders and the backend is alive.
 *
 * NOTE: `/health` lives at the BACKEND root, not under `/api/`. nginx on krisiserver
 * only proxies `/api/*`, so `request.get("/health")` against the UI baseURL would
 * return the SPA HTML, not JSON. We therefore hit the backend directly via
 * E2E_API_BASE (default http://localhost:8000). If you reach the stack solely
 * through the tunnel, the brand/nav assertions still validate the UI; the health
 * assertion validates the backend.
 */
test.describe("smoke", () => {
  test("app shell renders: brand + sidebar nav", async ({ page }) => {
    await page.goto("/");

    // Brand in the app bar.
    await expect(page.getByRole("heading", { name: /Stewie/ })).toBeVisible();

    // Sidebar navigation links (NavLink renders as <a>).
    for (const label of ["Dashboard", "Chat", "Knowledge", "Deep Research"]) {
      await expect(page.getByRole("link", { name: label })).toBeVisible();
    }
  });

  test("backend /health reports status ok", async ({ request }) => {
    const healthy = await backendHealthy(request);
    expect(healthy, `expected GET ${API_BASE}/health to return {status:"ok"}`).toBeTruthy();

    const body = await request.get(`${API_BASE}/health`).then((r) => r.json());
    expect(body.status).toBe("ok");
    // default model is LongCat (see docs/user-stories.md "Default LLM")
    expect(body.default_model).toContain("LongCat");
  });
});
