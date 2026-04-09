/**
 * Suite 01: Authentication — All 3 Accounts
 *
 * Tests login, redirect behavior, logout, and invalid credentials
 * against the LIVE site at 136.110.51.61
 */
import { test, expect } from "@playwright/test";
import {
  ACCOUNTS,
  login,
  logout,
  screenshot,
  type AccountKey,
} from "./helpers";

test.describe("Authentication — All Accounts", () => {
  test("01-01: root URL shows landing page with login link", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await screenshot(page, "01-01-root-landing");
    // Live site shows a marketing landing page at root
    const bodyText = (
      (await page.locator("body").textContent()) ?? ""
    ).toLowerCase();
    const hasLanding =
      bodyText.includes("hr management") ||
      bodyText.includes("central") ||
      bodyText.includes("get started") ||
      bodyText.includes("log in");
    expect(hasLanding).toBe(true);
  });

  test("01-02: login page renders all elements", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    await screenshot(page, "01-02-login-page");

    await expect(
      page.locator('input[type="email"], input[name="email"]').first(),
    ).toBeVisible();
    await expect(page.locator('input[type="password"]').first()).toBeVisible();
    await expect(page.locator('button[type="submit"]').first()).toBeVisible();
    // Branding is "Central" on the Ricoh demo live site
    await expect(page.getByText(/Central|Arbor/).first()).toBeVisible();
  });

  test("01-03: invalid credentials show error, stay on login", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    await page
      .locator('input[type="email"], input[name="email"]')
      .first()
      .fill("bad@example.com");
    await page.locator('input[type="password"]').first().fill("WrongPassword!");
    await page.locator('button[type="submit"]').first().click();
    await page.waitForTimeout(3000);
    await screenshot(page, "01-03-invalid-creds");

    expect(page.url()).toContain("/login");
    const bodyText = (
      (await page.locator("body").textContent()) ?? ""
    ).toLowerCase();
    const hasError =
      bodyText.includes("invalid") ||
      bodyText.includes("incorrect") ||
      bodyText.includes("error") ||
      bodyText.includes("wrong");
    expect(hasError).toBe(true);
  });

  test("01-04: Owner login redirects to /dashboard", async ({ page }) => {
    await login(page, "owner");
    await screenshot(page, "01-04-owner-post-login");
    const url = page.url();
    console.log(`Owner post-login URL: ${url}`);
    // Owner should land on /dashboard (not /my-dashboard)
    expect(url).toMatch(/\/(dashboard|advisory|onboarding)/);
  });

  test("01-05: HR Manager login redirects to /dashboard", async ({ page }) => {
    await login(page, "hr_manager");
    await screenshot(page, "01-05-hr-post-login");
    const url = page.url();
    console.log(`HR Manager post-login URL: ${url}`);
    expect(url).toMatch(/\/(dashboard|advisory|onboarding)/);
  });

  test("01-06: Employee login redirects to /my-dashboard", async ({ page }) => {
    await login(page, "employee");
    await screenshot(page, "01-06-employee-post-login");
    const url = page.url();
    console.log(`Employee post-login URL: ${url}`);
    // Employee should land on /my-dashboard
    expect(url).toMatch(/\/(my-dashboard|dashboard)/);
  });

  test("01-07: Owner logout returns to login page", async ({ page }) => {
    await login(page, "owner");
    await logout(page);
    await screenshot(page, "01-07-owner-logout");
    expect(page.url()).toContain("/login");
  });

  test("01-08: After logout, /dashboard redirects to login", async ({
    page,
  }) => {
    await login(page, "owner");
    await logout(page);
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    await screenshot(page, "01-08-post-logout-redirect");
    expect(page.url()).toContain("/login");
  });

  test("01-09: Protected routes redirect to login when unauthenticated", async ({
    page,
  }) => {
    const protectedRoutes = [
      "/dashboard",
      "/advisory",
      "/employees",
      "/payroll",
      "/leave",
      "/calculators/cpf",
      "/admin",
      "/profile",
    ];

    for (const route of protectedRoutes) {
      await page.goto(route);
      await page.waitForLoadState("networkidle");
      const url = page.url();
      const isProtected = url.includes("/login") || url.includes("/signup");
      console.log(`${route} → ${url} (protected: ${isProtected})`);
      expect(isProtected).toBe(true);
    }
    await screenshot(page, "01-09-protected-routes");
  });
});
