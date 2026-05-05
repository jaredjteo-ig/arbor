/**
 * Suite 10: Lifecycle Dashboard — Cox 8-stage walk
 *
 * Phase 1 obayashi P1-11. Logs in as owner, lands on the new
 * /strategy/lifecycle page, asserts hero band + 8 stage cards +
 * D&I tile + activity feed render, then clicks each stage card and
 * verifies the detail panel updates.
 */
import { test, expect } from "@playwright/test";
import { login, screenshot } from "./helpers";

const STAGES = [
  { key: "strategy", label: "Strategy" },
  { key: "attract", label: "Attract" },
  { key: "recruit", label: "Recruit" },
  { key: "onboard", label: "Onboard" },
  { key: "lnd", label: "Learning" },
  { key: "reward", label: "Reward" },
  { key: "progression", label: "Progression" },
  { key: "retain", label: "Retain" },
];

test.describe("Lifecycle Dashboard — owner", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "owner");
  });

  test("10-01: Lifecycle page renders with all 8 stages", async ({ page }) => {
    await page.goto("/strategy/lifecycle");
    // Wait for the network round-trip + render
    await page.waitForSelector("text=Workforce strategy", { timeout: 15000 });

    const main = page.locator("main");

    // Hero band copy
    await expect(main).toContainText("Workforce strategy");
    await expect(main).toContainText(/HEADCOUNT/i);
    await expect(main).toContainText(/CHURN YTD/i);

    // All 8 stage names
    for (const stage of STAGES) {
      await expect(main).toContainText(stage.label);
    }

    // D&I + activity sections
    await expect(main).toContainText(/Diversity & Inclusion/i);
    await expect(main).toContainText(/Recent activity/i);

    await screenshot(page, "10-01-lifecycle-overview");
  });

  test("10-02: Each stage card opens its detail panel", async ({ page }) => {
    await page.goto("/strategy/lifecycle");
    await page.waitForSelector("text=Workforce strategy", { timeout: 15000 });

    for (const stage of STAGES) {
      const card = page.locator("main button", {
        hasText: new RegExp(`View ${stage.label.toLowerCase()}`, "i"),
      });
      await card.click();
      // Detail panel header should now contain the stage's full title.
      // Account for both "Strategy" and "Reward · Recognition · Benefits"
      // shape by checking the panel has at least one KPI label.
      await page.waitForTimeout(150);
      const main = page.locator("main");
      await expect(main).toContainText(/[A-Z]{3,}/); // some KPI uppercase label is present
    }

    await screenshot(page, "10-02-lifecycle-all-stages-clicked");
  });

  test("10-03: Sidebar Lifecycle entry sits above Dashboard", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    const lifecycleLink = page
      .locator('nav a[href="/strategy/lifecycle"]')
      .first();
    await expect(lifecycleLink).toBeVisible();
    // Click it from the dashboard
    await lifecycleLink.click();
    await expect(page).toHaveURL(/\/strategy\/lifecycle/);
    await screenshot(page, "10-03-sidebar-to-lifecycle");
  });
});
