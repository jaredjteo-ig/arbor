import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for testing against LOCAL dev environment
 * Usage: npx playwright test --config=playwright.local.config.ts
 */
export default defineConfig({
  testDir: "./tests/e2e-live",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: [["html", { outputFolder: "playwright-report-local" }], ["list"]],
  timeout: 30000,
  use: {
    baseURL: "http://localhost:3001",
    screenshot: "on",
    video: "off",
    trace: "on-first-retry",
    actionTimeout: 10000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
