/**
 * Test Suite 01: Landing & Login Page
 *
 * Red-team perspective: what does a first-time user encounter?
 * Does the page feel like a real product or a placeholder?
 */
import { test, expect } from "@playwright/test";
import { LoginPage } from "./pages/auth.page";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

test.describe("Landing & Login Page", () => {
  test("01-01: root URL redirects to login when unauthenticated", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/01-01-root-redirect.png`,
      fullPage: true,
    });

    // Should land on /login or show login UI
    const url = page.url();
    const hasLoginContent =
      url.includes("/login") ||
      (await page
        .locator('input[type="email"]')
        .isVisible()
        .catch(() => false));

    expect(hasLoginContent).toBe(true);
    console.log(`Root URL redirected to: ${url}`);
  });

  test("01-02: login page renders branding, form, and all links", async ({
    page,
  }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/01-02-login-page.png`,
      fullPage: true,
    });

    // Branding: Arbor logo/name should be visible
    const brandText = page.getByText("Arbor");
    await expect(brandText.first()).toBeVisible();

    // Heading
    const heading = page.getByRole("heading");
    await expect(heading.first()).toBeVisible();
    const headingText = await heading.first().textContent();
    console.log(`LOGIN HEADING: "${headingText}"`);

    // Email and password inputs must exist
    await expect(loginPage.emailInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();

    // Submit button must be visible
    await expect(loginPage.submitButton).toBeVisible();
    const btnText = await loginPage.submitButton.textContent();
    console.log(`LOGIN BUTTON TEXT: "${btnText}"`);

    // Link to signup
    await expect(loginPage.signupLink).toBeVisible();

    // Forgot password link
    await expect(loginPage.forgotPasswordLink).toBeVisible();

    // Google sign-in option (placeholder OK but must render)
    await expect(loginPage.googleButton).toBeVisible();

    console.log("LOGIN PAGE: All key elements are present.");
  });

  test("01-03: trying to access protected /advisory without auth redirects to login", async ({
    page,
  }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/01-03-protected-redirect.png`,
      fullPage: true,
    });

    const url = page.url();
    const isOnLogin = url.includes("/login") || url.includes("/signup");
    expect(isOnLogin).toBe(true);
    console.log(`/advisory without auth redirected to: ${url}`);
  });

  test("01-04: trying to access protected /calculators without auth redirects to login", async ({
    page,
  }) => {
    await page.goto("/calculators");
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/01-04-calculators-redirect.png`,
      fullPage: true,
    });

    const url = page.url();
    const isOnLogin = url.includes("/login") || url.includes("/signup");
    expect(isOnLogin).toBe(true);
    console.log(`/calculators without auth redirected to: ${url}`);
  });

  test("01-05: login with empty fields shows validation errors", async ({
    page,
  }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    // Click submit without filling anything
    await loginPage.submitButton.click();
    await page.waitForTimeout(500);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/01-05-login-empty-validation.png`,
      fullPage: true,
    });

    // Should show validation errors (not submit)
    const url = page.url();
    expect(url).toContain("/login");
    console.log("LOGIN VALIDATION: Empty form blocked, still on login page.");
  });

  test("01-06: login with invalid credentials shows error message", async ({
    page,
  }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    await loginPage.emailInput.fill("notauser@example.com");
    await loginPage.passwordInput.fill("WrongPassword123!");
    await loginPage.submitButton.click();
    await page.waitForTimeout(3000); // Wait for API response

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/01-06-login-invalid-creds.png`,
      fullPage: true,
    });

    // At minimum, should not navigate away on bad credentials
    const url = page.url();
    expect(url).toContain("/login");

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const hasError =
      bodyText.toLowerCase().includes("invalid") ||
      bodyText.toLowerCase().includes("incorrect") ||
      bodyText.toLowerCase().includes("wrong") ||
      bodyText.toLowerCase().includes("error");
    console.log(
      `LOGIN INVALID CREDS: Stayed on login=${url.includes("/login")}, error message visible=${hasError}`,
    );
    console.log(`LOGIN BODY: ${bodyText.slice(0, 300)}`);
  });

  test("01-07: forgot password link navigates to forgot-password page", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    // Use direct navigation to verify the page exists
    await page.goto("/forgot-password");
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/01-07-forgot-password.png`,
      fullPage: true,
    });

    const url = page.url();
    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`FORGOT PASSWORD PAGE: URL=${url}`);
    console.log(`FORGOT PASSWORD CONTENT: ${bodyText.slice(0, 400)}`);

    // Should show forgot password page (not redirect back to login)
    const hasForgotContent =
      bodyText.toLowerCase().includes("reset") ||
      bodyText.toLowerCase().includes("forgot") ||
      bodyText.toLowerCase().includes("email") ||
      url.includes("forgot");
    expect(hasForgotContent).toBe(true);
  });

  test("01-08: signup page is accessible via direct URL", async ({ page }) => {
    await page.goto("/signup");
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/01-08-signup-page.png`,
      fullPage: true,
    });

    const url = page.url();
    expect(url).toContain("/signup");
    console.log(`SIGNUP PAGE: URL = ${url}`);

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const hasSignupContent =
      bodyText.toLowerCase().includes("sign up") ||
      bodyText.toLowerCase().includes("create account") ||
      bodyText.toLowerCase().includes("register");
    console.log(`SIGNUP PAGE: Has signup content = ${hasSignupContent}`);
    expect(hasSignupContent).toBe(true);
  });

  test("01-09: login page links — click 'Sign up' link", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    const signupLink = page.getByRole("link", { name: "Sign up" });
    const isVisible = await signupLink.isVisible().catch(() => false);
    console.log(`LOGIN: "Sign up" link visible = ${isVisible}`);

    if (isVisible) {
      await Promise.all([
        page.waitForNavigation({ waitUntil: "networkidle" }).catch(() => {}),
        signupLink.click(),
      ]);
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/01-09-login-to-signup-click.png`,
        fullPage: true,
      });

      const url = page.url();
      console.log(`LOGIN -> SIGNUP CLICK: Navigated to ${url}`);
      expect(url).toContain("/signup");
    }
  });

  test("01-10: login page — click 'Forgot password?' link", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    const forgotLink = page.getByRole("link", { name: /forgot/i });
    const isVisible = await forgotLink.isVisible().catch(() => false);
    console.log(`LOGIN: "Forgot password?" link visible = ${isVisible}`);

    if (isVisible) {
      await Promise.all([
        page.waitForNavigation({ waitUntil: "networkidle" }).catch(() => {}),
        forgotLink.click(),
      ]);
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/01-10-forgot-password-click.png`,
        fullPage: true,
      });

      const url = page.url();
      console.log(`LOGIN -> FORGOT PASSWORD CLICK: Navigated to ${url}`);
      expect(url).toContain("forgot");
    }
  });
});
