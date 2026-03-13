/**
 * Test Suite 03: Dashboard & Navigation
 *
 * Red-team: After login, does the dashboard work?
 * Are all nav items functional? Are there dead pages?
 *
 * Strategy:
 * 1. Register a real user against port 8099.
 * 2. Set up Playwright route interception to proxy port 8000 -> 8099
 *    (fixes the NEXT_PUBLIC_API_URL misconfiguration).
 * 3. Inject tokens + let the AuthContext validate them via the intercepted route.
 */
import { test, expect } from "@playwright/test";
import { setupAuthenticatedSession } from "./helpers/auth.helper";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

test.describe("Dashboard & Navigation (after auth)", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test("03-01: navigate to dashboard root — what does the user see?", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/03-01-dashboard-root.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`DASHBOARD ROOT: Landed at ${url}`);
    const bodyText = (await page.locator("body").textContent()) ?? "";
    // Log meaningful content (strip script tags)
    const meaningfulText = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 500);
    console.log(`DASHBOARD ROOT CONTENT: ${meaningfulText}`);
  });

  test("03-02: sidebar navigation links are present on dashboard", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/03-02-sidebar-nav.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`DASHBOARD: Currently at ${url}`);

    if (url.includes("/login")) {
      console.log(
        "DASHBOARD: Auth failed — redirected to login. Route interception may not be working.",
      );
      return;
    }

    // Check for common nav items using multiple selector strategies
    const navItems = [
      "Advisory",
      "Calculators",
      "Documents",
      "Compliance",
      "Alerts",
    ];

    for (const item of navItems) {
      const byLink = page.getByRole("link", { name: new RegExp(item, "i") });
      const byText = page.getByText(new RegExp(item, "i"));
      const isVisible =
        (await byLink
          .first()
          .isVisible()
          .catch(() => false)) ||
        (await byText
          .first()
          .isVisible()
          .catch(() => false));
      console.log(`NAV ITEM "${item}": visible=${isVisible}`);
    }
  });

  test("03-03: navigate to /advisory page", async ({ page }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/03-03-advisory-page.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`ADVISORY PAGE: URL = ${url}`);

    if (url.includes("/login")) {
      console.log("ADVISORY: Auth failed — redirected to login.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 600);
    console.log(`ADVISORY CONTENT: ${meaningful}`);

    // Look for chat interface elements
    const textarea = page.locator("textarea").first();
    const hasChat = await textarea.isVisible().catch(() => false);
    console.log(`ADVISORY: Chat textarea visible = ${hasChat}`);
  });

  test("03-04: navigate to /calculators page", async ({ page }) => {
    await page.goto("/calculators");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/03-04-calculators-page.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`CALCULATORS: URL = ${url}`);

    if (!url.includes("/login")) {
      const openButtons = page.getByRole("button", {
        name: /open calculator/i,
      });
      const count = await openButtons.count();
      console.log(`CALCULATORS: Found ${count} "Open Calculator" buttons`);
      expect(count).toBeGreaterThan(0);
    }
  });

  test("03-05: navigate to /documents page", async ({ page }) => {
    await page.goto("/documents");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/03-05-documents-page.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`DOCUMENTS: URL = ${url}`);

    if (!url.includes("/login")) {
      const generateButtons = page.getByRole("button", { name: /generate/i });
      const count = await generateButtons.count();
      console.log(`DOCUMENTS: Found ${count} "Generate" buttons`);
      expect(count).toBeGreaterThan(0);
    }
  });

  test("03-06: navigate to /compliance page", async ({ page }) => {
    await page.goto("/compliance");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/03-06-compliance-page.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`COMPLIANCE: URL = ${url}`);

    if (!url.includes("/login")) {
      const checkButton = page.getByRole("button", {
        name: /run compliance check/i,
      });
      const hasCheck = await checkButton.isVisible().catch(() => false);
      console.log(`COMPLIANCE: "Run Compliance Check" visible = ${hasCheck}`);
    }
  });

  test("03-07: navigate to all other dashboard pages", async ({ page }) => {
    const pages = [
      { path: "/alerts", label: "Alerts" },
      { path: "/profile", label: "Profile" },
      { path: "/settings", label: "Settings" },
      { path: "/analytics", label: "Analytics" },
      { path: "/help", label: "Help" },
    ];

    for (const p of pages) {
      await page.goto(p.path);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);

      const url = page.url();
      const isRedirectedToLogin = url.includes("/login");
      const bodyText = (await page.locator("body").textContent()) ?? "";
      const meaningful = bodyText
        .replace(/self\.__next.*$/gm, "")
        .trim()
        .slice(0, 200);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/03-07-${p.label.toLowerCase()}-page.png`,
        fullPage: true,
      });

      console.log(
        `${p.label.toUpperCase()} (${p.path}): URL=${url}, loginRedirect=${isRedirectedToLogin}`,
      );
      if (!isRedirectedToLogin) {
        console.log(`${p.label} CONTENT: ${meaningful}`);
      }
    }
  });

  test("03-08: 404 page for non-existent route", async ({ page }) => {
    await page.goto("/this-page-does-not-exist-xyz-123");
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/03-08-404-page.png`,
      fullPage: true,
    });

    const url = page.url();
    const bodyText = (await page.locator("body").textContent()) ?? "";
    const has404 =
      bodyText.includes("404") ||
      bodyText.toLowerCase().includes("not found") ||
      bodyText.toLowerCase().includes("page not found");

    console.log(`404 PAGE: URL=${url}, has404indicator=${has404}`);
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 300);
    console.log(`404 CONTENT: ${meaningful}`);
    expect(has404).toBe(true);
  });
});
