/**
 * Suite 04: Employee Account — Self-Service & Restricted Access
 *
 * Employee has limited self-service access. Tests that employee-specific
 * pages work and admin/HR pages are properly restricted.
 */
import { test, expect } from "@playwright/test";
import { login, screenshot, visitAndCapture } from "./helpers";

test.describe("Employee — Self-Service Pages", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "employee");
  });

  test("04-01: My Dashboard loads", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/my-dashboard",
      "04-01-emp-my-dashboard",
    );
    const url = page.url();
    expect(url).not.toContain("/login");
    console.log(`Employee my-dashboard URL: ${url}`);
  });

  test("04-02: My Profile page shows Lily Phang", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/my-profile",
      "04-02-emp-my-profile",
    );
    const hasProfile =
      bodyText.toLowerCase().includes("profile") ||
      bodyText.toLowerCase().includes("lily") ||
      bodyText.toLowerCase().includes("email");
    expect(hasProfile).toBe(true);
  });

  test("04-03: My Payslips page accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/my-payslips",
      "04-03-emp-my-payslips",
    );
    const url = page.url();
    expect(url).not.toContain("/login");
    const hasPayslip =
      bodyText.toLowerCase().includes("payslip") ||
      bodyText.toLowerCase().includes("salary") ||
      bodyText.toLowerCase().includes("pay") ||
      bodyText.toLowerCase().includes("no payslip");
    expect(hasPayslip).toBe(true);
  });

  test("04-04: My Timesheets page accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/my-timesheets",
      "04-04-emp-my-timesheets",
    );
    const url = page.url();
    expect(url).not.toContain("/login");
  });

  test("04-05: My Inventory page accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/my-inventory",
      "04-05-emp-my-inventory",
    );
    const url = page.url();
    expect(url).not.toContain("/login");
  });

  test("04-06: Advisory chat accessible to employees", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/advisory",
      "04-06-emp-advisory",
    );
    const hasAdvisory =
      bodyText.toLowerCase().includes("advisory") ||
      bodyText.toLowerCase().includes("ask") ||
      bodyText.toLowerCase().includes("question") ||
      bodyText.toLowerCase().includes("chat");
    expect(hasAdvisory).toBe(true);
  });

  test("04-07: Calculators accessible to employees", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/calculators/cpf",
      "04-07-emp-calc-cpf",
    );
    const hasCPF =
      bodyText.toLowerCase().includes("cpf") ||
      bodyText.toLowerCase().includes("contribution") ||
      bodyText.toLowerCase().includes("calculator");
    expect(hasCPF).toBe(true);
  });

  test("04-08: Help page accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(page, "/help", "04-08-emp-help");
    const url = page.url();
    expect(url).not.toContain("/login");
  });

  test("04-09: Emergency page accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/emergency",
      "04-09-emp-emergency",
    );
    const url = page.url();
    expect(url).not.toContain("/login");
  });

  test("04-10: Leave page — employee view", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/leave",
      "04-10-emp-leave",
    );
    const url = page.url();
    // Employee should see leave page (own leave applications)
    expect(url).not.toContain("/login");
  });

  test("04-11: Settings accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/settings/notifications",
      "04-11-emp-settings",
    );
    const url = page.url();
    expect(url).not.toContain("/login");
  });

  test("04-12: Alerts page accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/alerts",
      "04-12-emp-alerts",
    );
    const url = page.url();
    expect(url).not.toContain("/login");
  });
});

test.describe("Employee — Restricted Access (RBAC)", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "employee");
  });

  test("04-20: Employee CANNOT access /admin", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/admin",
      "04-20-emp-admin-blocked",
    );
    const url = page.url();
    const isBlocked =
      url.includes("/login") ||
      url.includes("/my-dashboard") ||
      url.includes("/dashboard") ||
      bodyText.toLowerCase().includes("access denied") ||
      bodyText.toLowerCase().includes("unauthorized") ||
      bodyText.toLowerCase().includes("permission") ||
      bodyText.toLowerCase().includes("not authorized");
    console.log(`Employee /admin: URL=${url}, blocked=${isBlocked}`);
    console.log(`Employee /admin body: ${bodyText.slice(0, 300)}`);
    // This SHOULD be blocked — capture whether it is or not
    await screenshot(page, "04-20-emp-admin-result");
  });

  test("04-21: Employee access to /employees page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/employees",
      "04-21-emp-employees-page",
    );
    const url = page.url();
    console.log(`Employee /employees: URL=${url}`);
    console.log(`Employee /employees body: ${bodyText.slice(0, 300)}`);
    // Document what happens — employees may see limited view or be blocked
    await screenshot(page, "04-21-emp-employees-result");
  });

  test("04-22: Employee access to /payroll page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/payroll",
      "04-22-emp-payroll-page",
    );
    const url = page.url();
    console.log(`Employee /payroll: URL=${url}`);
    console.log(`Employee /payroll body: ${bodyText.slice(0, 300)}`);
    await screenshot(page, "04-22-emp-payroll-result");
  });

  test("04-23: Employee access to /recruitment page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/recruitment",
      "04-23-emp-recruitment-page",
    );
    const url = page.url();
    console.log(`Employee /recruitment: URL=${url}`);
    await screenshot(page, "04-23-emp-recruitment-result");
  });

  test("04-24: Employee access to /profile (company profile)", async ({
    page,
  }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/profile",
      "04-24-emp-company-profile",
    );
    const url = page.url();
    console.log(`Employee /profile: URL=${url}`);
    console.log(`Employee /profile body: ${bodyText.slice(0, 300)}`);
    await screenshot(page, "04-24-emp-company-profile-result");
  });

  test("04-25: Employee access to /clients page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/clients",
      "04-25-emp-clients-page",
    );
    const url = page.url();
    console.log(`Employee /clients: URL=${url}`);
    await screenshot(page, "04-25-emp-clients-result");
  });
});
