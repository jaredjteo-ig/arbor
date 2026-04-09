import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for testing against the LIVE site at 136.110.51.61
 * Usage: npx playwright test --config=playwright.live.config.ts
 */
export default defineConfig({
  testDir: "./tests/e2e-live",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: [["html", { outputFolder: "playwright-report-live" }], ["list"]],
  timeout: 30000,
  use: {
    baseURL: "http://136.110.51.61",
    screenshot: "on",
    video: "on",
    trace: "on",
    actionTimeout: 10000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
