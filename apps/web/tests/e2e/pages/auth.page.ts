import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object for Auth flows (Login + Signup).
 *
 * Uses exact button/link names discovered from the live app snapshot:
 * - Login submit: "Log in"
 * - Forgot password link: "Forgot password?"
 * - Sign up link: "Sign up"
 * - Create account button: "Create account"
 * - Back to login link: "Log in" (on signup page)
 */
export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly forgotPasswordLink: Locator;
  readonly signupLink: Locator;
  readonly serverError: Locator;
  readonly googleButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page
      .locator('input[type="email"], input[name="email"]')
      .first();
    this.passwordInput = page.locator('input[type="password"]').first();
    // Exact name from live snapshot: "Log in"
    this.submitButton = page.locator('button[type="submit"]').first();
    // "Forgot password?" link
    this.forgotPasswordLink = page.getByRole("link", { name: /forgot/i });
    // "Sign up" link
    this.signupLink = page.getByRole("link", { name: "Sign up" });
    this.serverError = page.locator('[role="alert"]');
    this.googleButton = page.getByRole("button", { name: /google/i });
  }

  async goto() {
    await this.page.goto("/login");
    await this.page.waitForLoadState("networkidle");
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async expectOnLoginPage() {
    await expect(this.page).toHaveURL(/\/login/);
  }
}

export class SignupPage {
  readonly page: Page;
  readonly nameInput: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly confirmPasswordInput: Locator;
  readonly submitButton: Locator;
  readonly loginLink: Locator;
  readonly serverError: Locator;

  constructor(page: Page) {
    this.page = page;
    this.nameInput = page
      .locator('input[name="name"], input[autocomplete="name"]')
      .first();
    this.emailInput = page
      .locator('input[type="email"], input[name="email"]')
      .first();
    this.passwordInput = page.locator('input[type="password"]').first();
    this.confirmPasswordInput = page.locator('input[type="password"]').nth(1);
    // Exact button name from the live signup form: "Create account"
    this.submitButton = page.locator('button[type="submit"]').first();
    this.loginLink = page.getByRole("link", { name: "Log in" });
    this.serverError = page.locator('[role="alert"]');
  }

  async goto() {
    await this.page.goto("/signup");
    await this.page.waitForLoadState("networkidle");
  }

  async register(name: string, email: string, password: string) {
    await this.nameInput.fill(name);
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.confirmPasswordInput.fill(password);
    await this.submitButton.click();
  }
}
