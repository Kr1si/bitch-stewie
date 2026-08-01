import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    css: false,
    // Only unit tests under src/. The e2e/ specs are Playwright tests and must
    // not be collected here (they import @playwright/test).
    include: ["src/**/*.test.{ts,tsx}"],
    exclude: ["node_modules", "e2e/**"],
  },
});
