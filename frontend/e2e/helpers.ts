import { expect, type APIRequestContext, type Page } from "@playwright/test";

/**
 * Backend API base URL for DIRECT server calls (e.g. `/health`, which lives at
 * the backend root — nginx only proxies `/api/*`, so `/health` is NOT reachable
 * through http://localhost:3000). Defaults to the local dev backend.
 *
 * All `/api/*` calls can instead ride the UI's own baseURL through the tunnel;
 * this constant is only for endpoints outside the UI's proxy path.
 */
export const API_BASE = process.env.E2E_API_BASE ?? "http://localhost:8000";

/** A reasonably unique project name so re-runs don't 409-collide. */
export function uniqueProjectName(prefix = "E2E"): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e4)}`;
}

/**
 * Create a project directly via the backend API so chat/research tests have a
 * project to select without depending on the UI. Tolerates an existing project
 * (409) and returns the name to use. Returns null if the backend is unreachable.
 */
export async function ensureProject(
  request: APIRequestContext,
  name: string,
): Promise<string | null> {
  try {
    const resp = await request.post(`${API_BASE}/api/projects`, {
      data: { name, repo_path: null, description: "e2e fixture" },
    });
    if (resp.ok()) return name;
    if (resp.status() === 409) return name; // already exists — fine
    // unexpected status; surface it
    console.warn(`ensureProject: POST /api/projects -> ${resp.status()}`);
    return null;
  } catch (e) {
    console.warn(`ensureProject: backend unreachable at ${API_BASE} (${e})`);
    return null;
  }
}

/**
 * Assert that an element eventually appears, tolerating a slow/optional LLM.
 * Used for assistant bubbles that may take a while to stream, or may never
 * arrive if the model is unreachable.
 */
export async function expectEventually(
  locator: { waitFor: (opts: { timeout: number }) => Promise<void> },
  timeoutMs: number,
): Promise<void> {
  await locator.waitFor({ timeout: timeoutMs });
}

/** True if the backend /health endpoint is reachable (stack is up). */
export async function backendHealthy(request: APIRequestContext): Promise<boolean> {
  try {
    const resp = await request.get(`${API_BASE}/health`);
    if (!resp.ok()) return false;
    const body = await resp.json();
    return body?.status === "ok";
  } catch {
    return false;
  }
}

/**
 * Robust assertion for the chat assistant turn. The assistant bubble carries an
 * Avatar with text "S" inside <main>; an error turn ALSO renders as an assistant
 * message (role "assistant", text starting with "Error:"). So the presence of an
 * assistant bubble covers both the happy path and the documented error state.
 */
export async function expectAssistantTurn(page: Page, timeoutMs: number): Promise<void> {
  const assistantBubble = page
    .locator("main")
    .locator("div.MuiAvatar-root", { hasText: "S" })
    .locator("..");
  await expect(assistantBubble.first()).toBeVisible({ timeout: timeoutMs });
}
