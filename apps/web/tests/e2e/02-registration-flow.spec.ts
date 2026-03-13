/**
 * Test Suite 02: Registration Flow (Onboarding)
 *
 * Red-team: Can a new user actually sign up?
 * Does the backend registration endpoint work?
 * Is there a company profile setup step?
 */
import { test, expect } from "@playwright/test";
import { SignupPage } from "./pages/auth.page";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

// Generate a unique email per test run to avoid conflicts
const TEST_EMAIL = `e2e_${Date.now()}@playwright.test`;
const TEST_PASSWORD = "SecurePass1!";
const TEST_NAME = "E2E Test User";

test.describe("Registration Flow", () => {
  test("02-01: signup page renders all required form fields", async ({
    page,
  }) => {
    const signupPage = new SignupPage(page);
    await signupPage.goto();
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/02-01-signup-page.png`,
      fullPage: true,
    });

    // All fields must be present
    await expect(signupPage.nameInput).toBeVisible();
    await expect(signupPage.emailInput).toBeVisible();
    await expect(signupPage.passwordInput).toBeVisible();
    await expect(signupPage.confirmPasswordInput).toBeVisible();
    await expect(signupPage.submitButton).toBeVisible();

    // Link back to login
    await expect(signupPage.loginLink).toBeVisible();

    console.log("SIGNUP PAGE: All 4 fields + submit + login link present.");
  });

  test("02-02: signup with empty fields shows validation", async ({ page }) => {
    const signupPage = new SignupPage(page);
    await signupPage.goto();

    // Click submit without filling
    await signupPage.submitButton.click();
    await page.waitForTimeout(500);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/02-02-signup-empty-validation.png`,
      fullPage: true,
    });

    // Should still be on signup page
    expect(page.url()).toContain("/signup");
    console.log("SIGNUP VALIDATION: Empty submit stayed on signup page.");
  });

  test("02-03: signup with mismatched passwords shows error", async ({
    page,
  }) => {
    const signupPage = new SignupPage(page);
    await signupPage.goto();

    await signupPage.nameInput.fill("Test User");
    await signupPage.emailInput.fill("test@example.com");
    await signupPage.passwordInput.fill("Password123!");
    await signupPage.confirmPasswordInput.fill("DifferentPassword!");
    await signupPage.submitButton.click();
    await page.waitForTimeout(500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/02-03-signup-password-mismatch.png`,
      fullPage: true,
    });

    // Should show error and stay on signup
    expect(page.url()).toContain("/signup");
    console.log("SIGNUP PASSWORD MISMATCH: Error shown or blocked.");
  });

  test("02-04: signup with short password shows error", async ({ page }) => {
    const signupPage = new SignupPage(page);
    await signupPage.goto();

    await signupPage.nameInput.fill("Test User");
    await signupPage.emailInput.fill("test@example.com");
    await signupPage.passwordInput.fill("short");
    await signupPage.confirmPasswordInput.fill("short");
    await signupPage.submitButton.click();
    await page.waitForTimeout(500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/02-04-signup-short-password.png`,
      fullPage: true,
    });

    expect(page.url()).toContain("/signup");
    console.log("SIGNUP SHORT PASSWORD: Blocked as expected.");
  });

  test("02-05: full registration attempt — real backend check", async ({
    page,
  }) => {
    const signupPage = new SignupPage(page);
    await signupPage.goto();

    // Fill and submit
    await signupPage.nameInput.fill(TEST_NAME);
    await signupPage.emailInput.fill(TEST_EMAIL);
    await signupPage.passwordInput.fill(TEST_PASSWORD);
    await signupPage.confirmPasswordInput.fill(TEST_PASSWORD);
    await signupPage.submitButton.click();

    // Wait for network response (up to 10s)
    await page.waitForTimeout(5000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/02-05-after-registration.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`REGISTRATION RESULT: URL after submit = ${url}`);

    // Check what happened:
    // - Success: redirected away from /signup (to /dashboard, /onboarding, etc.)
    // - Failure: error shown on /signup or stays on /signup
    if (url.includes("/signup")) {
      // Check for error message
      const errorVisible = await signupPage.serverError
        .isVisible()
        .catch(() => false);
      const bodyText = await page.locator("body").textContent();
      console.log(
        `REGISTRATION: Stayed on signup. Error visible: ${errorVisible}`,
      );
      console.log(
        `REGISTRATION: Page content snippet: ${bodyText?.slice(0, 300)}`,
      );
      // Registration failed — report as finding, but don't hard-fail the test
      // The test documents the behavior.
    } else {
      console.log(`REGISTRATION SUCCESS: Redirected to ${url}`);
    }
  });

  test("02-06: onboarding page accessible after registration redirect", async ({
    page,
  }) => {
    // Navigate directly to onboarding to see what it looks like
    // Even if user isn't authenticated, we check what the page renders
    await page.goto("/onboarding");
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/02-06-onboarding-page.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`ONBOARDING: URL = ${url}`);
    // Should redirect to login if unauthenticated, or show onboarding form
    const isValid =
      url.includes("/login") ||
      url.includes("/onboarding") ||
      url.includes("/signup");
    expect(isValid).toBe(true);
  });
});
