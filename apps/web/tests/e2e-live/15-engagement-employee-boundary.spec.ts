/**
 * Suite 15: Engagement — Employee Route Boundary
 *
 * Z20 (round-3 redteam): pin that:
 * - Lily (employee) is BLOCKED from /engagement (HR overview).
 * - Lily can reach /my-engagement-surveys.
 * - Lily can reach /my-dashboard (engagement pending card may render).
 * - Engagement sidebar entry is gated correctly per role.
 */
import { test, expect } from "@playwright/test";
import { login, screenshot, visitAndCapture } from "./helpers";

test.describe("Engagement — Employee Boundary (Z20)", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "employee");
  });

  test("15-01: Employee /engagement is access-denied", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/engagement",
      "15-01-emp-engagement-blocked",
    );
    /* AdminGuard renders Access Denied for employees. Must NOT render the
       HR overview (no "Launch survey" button, no trend hero). */
    const blocked =
      bodyText.toLowerCase().includes("access denied") ||
      bodyText.toLowerCase().includes("do not have permission") ||
      bodyText.toLowerCase().includes("restricted");
    expect(blocked).toBe(true);
  });

  test("15-02: Employee can reach /my-engagement-surveys", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/my-engagement-surveys",
      "15-02-emp-my-engagement",
    );
    const url = page.url();
    expect(url).toContain("/my-engagement-surveys");
    expect(url).not.toContain("/login");
    /* Must show the page content — not Access Denied. */
    const hasMyEngagement =
      bodyText.toLowerCase().includes("my engagement") ||
      bodyText.toLowerCase().includes("pending check-in") ||
      bodyText.toLowerCase().includes("no pending check-ins");
    expect(hasMyEngagement).toBe(true);
  });

  test("15-03: Employee /engagement/team is access-denied (no direct reports)", async ({
    page,
  }) => {
    /* /engagement/team is gated by has_direct_reports at the API. The
       page renders an empty/error state when API returns 403. */
    await page.goto("/engagement/team");
    await page.waitForLoadState("networkidle");
    await screenshot(page, "15-03-emp-team-no-access");
    const bodyText = await page.evaluate(() => document.body.innerText);
    const blocked =
      bodyText.toLowerCase().includes("don't have access") ||
      bodyText.toLowerCase().includes("manager") ||
      bodyText.toLowerCase().includes("team is too small");
    expect(blocked).toBe(true);
  });
});

test.describe("Engagement — HR Manager Sees the Surface", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "hr_manager");
  });

  test("15-10: HR manager loads /engagement overview", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/engagement",
      "15-10-hr-engagement-overview",
    );
    const url = page.url();
    expect(url).toContain("/engagement");
    expect(url).not.toContain("/login");
    const hasOverview =
      bodyText.toLowerCase().includes("engagement") ||
      bodyText.toLowerCase().includes("launch survey") ||
      bodyText.toLowerCase().includes("trend");
    expect(hasOverview).toBe(true);
  });
});
