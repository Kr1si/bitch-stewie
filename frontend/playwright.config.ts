import { defineConfig } from "@playwright/test";

/**
 * E2E config. These tests run against a RUNNING stack — either the krisiserver
 * deployment reached through the SSH tunnel (default baseURL http://localhost:3000)
 * or a local dev server (E2E_BASE_URL=http://localhost:5173).
 *
 * The stack is not started here: reuseExistingServer is effectively true because
 * we define no `webServer`. Start the stack yourself (see e2e/README.md).
 */
export default defineConfig({
  testDir: "./e2e",
  // A single shared backend/LLM: run serially to avoid hammering it.
  fullyParallel: false,
  workers: 1,
  // Per-test ceiling. Individual tests can raise this with test.setTimeout().
  timeout: 120_000,
  expect: { timeout: 30_000 },
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    actionTimeout: 20_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
});
