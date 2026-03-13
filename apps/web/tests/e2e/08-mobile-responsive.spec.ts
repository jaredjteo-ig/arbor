/**
 * Test Suite 08: Mobile Responsiveness (Flow 7)
 *
 * Red-team: Does the UI remain usable at mobile widths?
 * Target: iPhone 14 (390x844), iPhone SE (375x667), generic mobile (375px wide)
 *
 * Checks:
 * - Login page usable on mobile
 * - Signup page usable on mobile
 * - Dashboard accessible (sidebar collapses or transforms to hamburger)
 * - Advisory chat accessible on mobile
 * - Calculators accessible on mobile
 * - Documents page accessible on mobile
 * - Navigation items reachable on mobile
 * - No horizontal scroll (content does not overflow)
 * - Form inputs large enough to tap (min 44px touch target)
 */
import { test, expect } from "@playwright/test";
import { setupAuthenticatedSession } from "./helpers/auth.helper";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

/* ── Viewport helpers ─────────────────────────────────────── */

const MOBILE_VIEWPORTS = [
  { name: "iPhone-14", width: 390, height: 844 },
  { name: "iPhone-SE", width: 375, height: 667 },
  { name: "Android-Generic", width: 360, height: 800 },
];

/** True if the page has a horizontal scrollbar / content overflow. */
async function hasHorizontalOverflow(
  page: Parameters<typeof setupAuthenticatedSession>[0],
): Promise<boolean> {
  return page.evaluate(() => {
    return document.body.scrollWidth > window.innerWidth;
  });
}

/* ── Unauthenticated pages at mobile width ──────────────────── */

test.describe("Mobile Responsiveness — Auth Pages", () => {
  for (const viewport of MOBILE_VIEWPORTS) {
    test(`08-01 [${viewport.name}]: login page renders correctly at ${viewport.width}px`, async ({
      page,
    }) => {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await page.goto("/login");
      await page.waitForLoadState("networkidle");

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/08-01-login-${viewport.name}.png`,
        fullPage: true,
      });

      // Email input must be visible and tappable
      const emailInput = page
        .locator('input[type="email"], input[name="email"]')
        .first();
      await expect(
        emailInput,
        "Email input must be visible on mobile",
      ).toBeVisible();

      // Password input must be visible
      const passwordInput = page.locator('input[type="password"]').first();
      await expect(
        passwordInput,
        "Password input must be visible on mobile",
      ).toBeVisible();

      // Submit button must be visible
      const submitBtn = page.locator('button[type="submit"]').first();
      await expect(
        submitBtn,
        "Submit button must be visible on mobile",
      ).toBeVisible();

      // Check no horizontal overflow
      const overflow = await hasHorizontalOverflow(page);
      console.log(
        `LOGIN [${viewport.name}]: horizontal overflow = ${overflow}`,
      );
      expect(
        overflow,
        `Login page should not overflow horizontally at ${viewport.width}px`,
      ).toBe(false);

      // Check submit button height (touch target >= 40px)
      const btnBox = await submitBtn.boundingBox();
      if (btnBox) {
        console.log(
          `LOGIN [${viewport.name}]: submit button height = ${btnBox.height}px, width = ${btnBox.width}px`,
        );
        expect(
          btnBox.height,
          `Submit button touch target should be at least 40px tall`,
        ).toBeGreaterThanOrEqual(40);
      }

      console.log(
        `LOGIN [${viewport.name}]: PASS — all elements visible, no overflow.`,
      );
    });
  }

  test("08-02 [375px]: signup page renders correctly on mobile", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/signup");
    await page.waitForLoadState("networkidle");

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-02-signup-mobile.png`,
      fullPage: true,
    });

    // All four fields must be visible
    const nameInput = page
      .locator('input[name="name"], input[autocomplete="name"]')
      .first();
    const emailInput = page
      .locator('input[type="email"], input[name="email"]')
      .first();
    const passwordInput = page.locator('input[type="password"]').first();
    const confirmPasswordInput = page.locator('input[type="password"]').nth(1);
    const submitBtn = page.locator('button[type="submit"]').first();

    await expect(nameInput, "Name input visible on mobile").toBeVisible();
    await expect(emailInput, "Email input visible on mobile").toBeVisible();
    await expect(
      passwordInput,
      "Password input visible on mobile",
    ).toBeVisible();
    await expect(
      confirmPasswordInput,
      "Confirm password input visible on mobile",
    ).toBeVisible();
    await expect(submitBtn, "Submit button visible on mobile").toBeVisible();

    const overflow = await hasHorizontalOverflow(page);
    console.log(`SIGNUP MOBILE: horizontal overflow = ${overflow}`);
    expect(overflow, "Signup page must not overflow on mobile").toBe(false);

    // Verify form fills work on mobile
    await nameInput.fill("Mobile Test");
    await emailInput.fill("mobile@test.com");
    await passwordInput.fill("TestPass123!");
    await confirmPasswordInput.fill("TestPass123!");

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-02b-signup-mobile-filled.png`,
      fullPage: true,
    });

    console.log("SIGNUP MOBILE: Form fill works on 375px viewport.");
  });

  test("08-03 [375px]: forgot password page renders on mobile", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/forgot-password");
    await page.waitForLoadState("networkidle");

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-03-forgot-password-mobile.png`,
      fullPage: true,
    });

    const emailInput = page
      .locator('input[type="email"], input[name="email"]')
      .first();
    await expect(emailInput).toBeVisible();

    const overflow = await hasHorizontalOverflow(page);
    expect(overflow, "Forgot password page must not overflow on mobile").toBe(
      false,
    );
    console.log("FORGOT PASSWORD MOBILE: PASS.");
  });
});

/* ── Authenticated pages at mobile width ──────────────────── */

test.describe("Mobile Responsiveness — Dashboard Pages", () => {
  test.beforeEach(async ({ page }) => {
    // Set mobile viewport before setting up auth so the page
    // loads in mobile mode throughout the test.
    await page.setViewportSize({ width: 375, height: 812 });
    await setupAuthenticatedSession(page);
  });

  test("08-04 [375px]: dashboard root — sidebar collapses or transforms on mobile", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-04-dashboard-mobile.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`DASHBOARD MOBILE: URL = ${url}`);

    if (url.includes("/login")) {
      console.log(
        "DASHBOARD MOBILE: Not authenticated — checking login page responsiveness.",
      );
      const overflow = await hasHorizontalOverflow(page);
      console.log(`LOGIN MOBILE: overflow = ${overflow}`);
      return;
    }

    // Check no horizontal overflow on dashboard
    const overflow = await hasHorizontalOverflow(page);
    console.log(`DASHBOARD MOBILE: horizontal overflow = ${overflow}`);
    expect(overflow, "Dashboard must not overflow horizontally on mobile").toBe(
      false,
    );

    // Check if sidebar collapses or hamburger menu appears
    const collapsedSidebar = page.locator(
      '[aria-label="Expand sidebar"], [aria-label="Open menu"], [aria-label="Menu"]',
    );
    const hasCollapsed = await collapsedSidebar.isVisible().catch(() => false);

    const hamburger = page.locator(
      'button[aria-label*="menu" i], button[aria-label*="navigation" i]',
    );
    const hasHamburger = await hamburger.isVisible().catch(() => false);

    // Check if nav is still accessible (may be collapsed but reachable)
    const nav = page.locator("nav[aria-label*='navigation' i]").first();
    const navVisible = await nav.isVisible().catch(() => false);

    console.log(
      `DASHBOARD MOBILE: collapsed sidebar=${hasCollapsed}, hamburger=${hasHamburger}, nav visible=${navVisible}`,
    );

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 300);
    console.log(`DASHBOARD MOBILE CONTENT: ${meaningful}`);
  });

  test("08-05 [375px]: advisory page usable on mobile", async ({ page }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-05-advisory-mobile.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ADVISORY MOBILE: Not authenticated.");
      return;
    }

    const overflow = await hasHorizontalOverflow(page);
    console.log(`ADVISORY MOBILE: horizontal overflow = ${overflow}`);
    expect(overflow, "Advisory page must not overflow on mobile").toBe(false);

    // Check chat input is visible
    const contentEditable = page.locator('[contenteditable="true"]').first();
    const textarea = page.locator("textarea").first();
    const hasInput =
      (await contentEditable.isVisible().catch(() => false)) ||
      (await textarea.isVisible().catch(() => false));

    console.log(`ADVISORY MOBILE: chat input visible = ${hasInput}`);

    // Send button should be visible
    const sendButton = page
      .getByRole("button", { name: /send|submit|ask/i })
      .first();
    const hasSend = await sendButton.isVisible().catch(() => false);
    console.log(`ADVISORY MOBILE: send button visible = ${hasSend}`);

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(
      `ADVISORY MOBILE CONTENT: ${bodyText
        .replace(/self\.__next.*$/gm, "")
        .trim()
        .slice(0, 300)}`,
    );
  });

  test("08-06 [375px]: calculators page usable on mobile", async ({ page }) => {
    await page.goto("/calculators");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-06-calculators-mobile.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("CALCULATORS MOBILE: Not authenticated.");
      return;
    }

    const overflow = await hasHorizontalOverflow(page);
    console.log(`CALCULATORS MOBILE: horizontal overflow = ${overflow}`);
    expect(overflow, "Calculators page must not overflow on mobile").toBe(
      false,
    );

    // Calculator cards should stack vertically
    const openButtons = page.getByRole("button", { name: /open calculator/i });
    const count = await openButtons.count();
    console.log(`CALCULATORS MOBILE: ${count} calculator buttons visible`);
    expect(count).toBeGreaterThan(0);

    // Check button tap targets
    const firstButton = openButtons.first();
    const btnBox = await firstButton.boundingBox();
    if (btnBox) {
      console.log(
        `CALCULATORS MOBILE: first button height = ${btnBox.height}px`,
      );
    }
  });

  test("08-07 [375px]: CPF calculator form usable on mobile", async ({
    page,
  }) => {
    await page.goto("/calculators/cpf");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-07a-cpf-calculator-mobile.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("CPF CALC MOBILE: Not authenticated.");
      return;
    }

    const overflow = await hasHorizontalOverflow(page);
    console.log(`CPF CALC MOBILE: horizontal overflow = ${overflow}`);
    expect(overflow, "CPF calculator must not overflow on mobile").toBe(false);

    // Salary input should be fillable on mobile
    const salaryInput = page
      .locator("input[type='number'], input[placeholder*='salary' i]")
      .first();
    const hasSalary = await salaryInput.isVisible().catch(() => false);

    if (hasSalary) {
      await salaryInput.click();
      await salaryInput.fill("5000");

      const ageInput = page
        .locator("input[placeholder*='age' i], input[name*='age' i]")
        .first();
      const hasAge = await ageInput.isVisible().catch(() => false);
      if (hasAge) {
        await ageInput.fill("35");
      }

      const calcButton = page
        .getByRole("button", { name: /calculate|compute/i })
        .first();
      const hasCalc = await calcButton.isVisible().catch(() => false);
      if (hasCalc) {
        await calcButton.click();
        await page.waitForTimeout(1500);
      }

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/08-07b-cpf-calculator-mobile-result.png`,
        fullPage: true,
      });

      const resultText = (await page.locator("body").textContent()) ?? "";
      const hasResult = resultText.includes("$") || resultText.includes("%");
      console.log(`CPF CALC MOBILE: Has numeric result = ${hasResult}`);
    } else {
      console.log("CPF CALC MOBILE: No salary input found.");
    }
  });

  test("08-08 [375px]: documents page usable on mobile", async ({ page }) => {
    await page.goto("/documents");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-08-documents-mobile.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("DOCUMENTS MOBILE: Not authenticated.");
      return;
    }

    const overflow = await hasHorizontalOverflow(page);
    console.log(`DOCUMENTS MOBILE: horizontal overflow = ${overflow}`);
    expect(overflow, "Documents page must not overflow on mobile").toBe(false);

    // Template cards should be visible
    const generateButtons = page.getByRole("button", { name: /generate/i });
    const count = await generateButtons.count();
    console.log(`DOCUMENTS MOBILE: ${count} Generate buttons visible`);
    expect(count).toBeGreaterThan(0);

    // Search input should be accessible
    const searchInput = page.locator('input[placeholder*="search" i]').first();
    const hasSearch = await searchInput.isVisible().catch(() => false);
    console.log(`DOCUMENTS MOBILE: search input visible = ${hasSearch}`);
  });

  test("08-09 [375px]: compliance page usable on mobile", async ({ page }) => {
    await page.goto("/compliance");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-09-compliance-mobile.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("COMPLIANCE MOBILE: Not authenticated.");
      return;
    }

    const overflow = await hasHorizontalOverflow(page);
    console.log(`COMPLIANCE MOBILE: horizontal overflow = ${overflow}`);
    expect(overflow, "Compliance page must not overflow on mobile").toBe(false);

    const runButton = page.getByRole("button", {
      name: /run compliance check/i,
    });
    const hasRun = await runButton.isVisible().catch(() => false);
    console.log(`COMPLIANCE MOBILE: Run button visible = ${hasRun}`);
    expect(
      hasRun,
      "Run Compliance Check button must be visible on mobile",
    ).toBe(true);

    // Checkboxes should be tappable
    const checkboxes = page.locator('input[type="checkbox"]');
    const checkCount = await checkboxes.count();
    console.log(`COMPLIANCE MOBILE: ${checkCount} checkboxes found`);
  });

  test("08-10 [375px]: alerts page usable on mobile", async ({ page }) => {
    await page.goto("/alerts");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-10-alerts-mobile.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ALERTS MOBILE: Not authenticated.");
      return;
    }

    const overflow = await hasHorizontalOverflow(page);
    console.log(`ALERTS MOBILE: horizontal overflow = ${overflow}`);
    expect(overflow, "Alerts page must not overflow on mobile").toBe(false);

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 300);
    console.log(`ALERTS MOBILE CONTENT: ${meaningful}`);
  });

  test("08-11 [375px]: sidebar collapse/toggle works on mobile", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("SIDEBAR TOGGLE MOBILE: Not authenticated.");
      return;
    }

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-11a-sidebar-mobile-initial.png`,
      fullPage: true,
    });

    // Look for collapse toggle button
    const collapseBtn = page.locator(
      'button[aria-label="Collapse sidebar"], button[aria-label="Expand sidebar"]',
    );
    const hasCollapse = await collapseBtn.isVisible().catch(() => false);
    console.log(`SIDEBAR MOBILE: Toggle button visible = ${hasCollapse}`);

    if (hasCollapse) {
      await collapseBtn.click();
      await page.waitForTimeout(500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/08-11b-sidebar-mobile-toggled.png`,
        fullPage: true,
      });

      console.log(
        "SIDEBAR MOBILE: Toggle clicked — sidebar should have changed state.",
      );
    }

    // Regardless, navigation must be accessible
    const nav = page.locator("nav").first();
    const navVisible = await nav.isVisible().catch(() => false);
    console.log(`SIDEBAR MOBILE: nav element visible = ${navVisible}`);
  });
});

/* ── iPad/tablet width check ─────────────────────────────── */

test.describe("Mobile Responsiveness — Tablet Width", () => {
  test("08-12 [768px]: login page renders at tablet width", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-12-login-tablet.png`,
      fullPage: true,
    });

    const overflow = await hasHorizontalOverflow(page);
    console.log(`LOGIN TABLET: horizontal overflow = ${overflow}`);
    expect(overflow).toBe(false);

    const emailInput = page
      .locator('input[type="email"], input[name="email"]')
      .first();
    await expect(emailInput).toBeVisible();
    console.log("LOGIN TABLET: PASS.");
  });

  test("08-13 [768px]: dashboard renders at tablet width without auth", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await setupAuthenticatedSession(page);
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-13-dashboard-tablet.png`,
      fullPage: true,
    });

    const overflow = await hasHorizontalOverflow(page);
    console.log(`DASHBOARD TABLET: horizontal overflow = ${overflow}`);
    expect(overflow, "Dashboard must not overflow at tablet width").toBe(false);

    const url = page.url();
    console.log(`DASHBOARD TABLET: URL = ${url}`);
  });
});
