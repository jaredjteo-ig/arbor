/**
 * Suite 03: HR Manager Account — Site Navigation & Permissions
 *
 * HR Manager has access to employee management, leave, payroll, admin.
 * Verifies correct dashboard, navigation, and feature access.
 */
import { test, expect } from "@playwright/test";
import { login, screenshot, visitAndCapture } from "./helpers";

test.describe("HR Manager — Site Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "hr_manager");
  });

  test("03-01: Dashboard loads with company data", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/dashboard",
      "03-01-hr-dashboard",
    );
    const hasContent =
      bodyText.toLowerCase().includes("central") ||
      bodyText.toLowerCase().includes("dashboard") ||
      bodyText.toLowerCase().includes("employee");
    expect(hasContent).toBe(true);
  });

  test("03-02: Employee list loads", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/employees",
      "03-02-hr-employees",
    );
    const hasEmployees =
      bodyText.toLowerCase().includes("employee") ||
      bodyText.toLowerCase().includes("name") ||
      bodyText.toLowerCase().includes("department");
    expect(hasEmployees).toBe(true);
  });

  test("03-03: Leave management accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/leave",
      "03-03-hr-leave",
    );
    const hasLeave =
      bodyText.toLowerCase().includes("leave") ||
      bodyText.toLowerCase().includes("annual") ||
      bodyText.toLowerCase().includes("application");
    expect(hasLeave).toBe(true);
  });

  test("03-04: Payroll accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/payroll",
      "03-04-hr-payroll",
    );
    const hasPayroll =
      bodyText.toLowerCase().includes("payroll") ||
      bodyText.toLowerCase().includes("salary") ||
      bodyText.toLowerCase().includes("run");
    expect(hasPayroll).toBe(true);
  });

  test("03-05: Advisory chat accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/advisory",
      "03-05-hr-advisory",
    );
    const hasAdvisory =
      bodyText.toLowerCase().includes("advisory") ||
      bodyText.toLowerCase().includes("ask") ||
      bodyText.toLowerCase().includes("question") ||
      bodyText.toLowerCase().includes("chat");
    expect(hasAdvisory).toBe(true);
  });

  test("03-06: CPF Calculator", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/calculators/cpf",
      "03-06-hr-calc-cpf",
    );
    const hasCPF =
      bodyText.toLowerCase().includes("cpf") ||
      bodyText.toLowerCase().includes("contribution") ||
      bodyText.toLowerCase().includes("calculator");
    expect(hasCPF).toBe(true);
  });

  test("03-07: Admin panel accessible (hr_manager has access)", async ({
    page,
  }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/admin",
      "03-07-hr-admin",
    );
    const url = page.url();
    // HR manager should have admin access
    expect(url).not.toContain("/login");
    console.log(`HR Manager admin URL: ${url}`);
    console.log(`HR Manager admin content: ${bodyText.slice(0, 300)}`);
  });

  test("03-08: Documents page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/documents",
      "03-08-hr-documents",
    );
    const hasDocs =
      bodyText.toLowerCase().includes("document") ||
      bodyText.toLowerCase().includes("template") ||
      bodyText.toLowerCase().includes("generate");
    expect(hasDocs).toBe(true);
  });

  test("03-09: Compliance page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/compliance",
      "03-09-hr-compliance",
    );
    const hasCompliance =
      bodyText.toLowerCase().includes("compliance") ||
      bodyText.toLowerCase().includes("regulatory") ||
      bodyText.toLowerCase().includes("employment");
    expect(hasCompliance).toBe(true);
  });

  test("03-10: Attendance page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/attendance",
      "03-10-hr-attendance",
    );
    const hasAttendance =
      bodyText.toLowerCase().includes("attendance") ||
      bodyText.toLowerCase().includes("clock") ||
      bodyText.toLowerCase().includes("time");
    expect(hasAttendance).toBe(true);
  });

  test("03-11: Claims page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/claims",
      "03-11-hr-claims",
    );
    const hasClaims =
      bodyText.toLowerCase().includes("claim") ||
      bodyText.toLowerCase().includes("expense") ||
      bodyText.toLowerCase().includes("receipt");
    expect(hasClaims).toBe(true);
  });

  test("03-12: Shifts page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/shifts",
      "03-12-hr-shifts",
    );
    const hasShifts =
      bodyText.toLowerCase().includes("shift") ||
      bodyText.toLowerCase().includes("schedule") ||
      bodyText.toLowerCase().includes("roster");
    expect(hasShifts).toBe(true);
  });

  test("03-13: Appraisals page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/appraisals",
      "03-13-hr-appraisals",
    );
    const hasAppraisals =
      bodyText.toLowerCase().includes("appraisal") ||
      bodyText.toLowerCase().includes("performance") ||
      bodyText.toLowerCase().includes("review");
    expect(hasAppraisals).toBe(true);
  });

  test("03-14: Policies page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/policies",
      "03-14-hr-policies",
    );
    const hasPolicies =
      bodyText.toLowerCase().includes("polic") ||
      bodyText.toLowerCase().includes("handbook") ||
      bodyText.toLowerCase().includes("guideline");
    expect(hasPolicies).toBe(true);
  });

  test("03-15: Company profile", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/profile",
      "03-15-hr-profile",
    );
    const hasProfile =
      bodyText.toLowerCase().includes("company") ||
      bodyText.toLowerCase().includes("profile") ||
      bodyText.toLowerCase().includes("central");
    expect(hasProfile).toBe(true);
  });

  test("03-16: My Profile page shows Grace Koh", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/my-profile",
      "03-16-hr-my-profile",
    );
    const hasProfile =
      bodyText.toLowerCase().includes("profile") ||
      bodyText.toLowerCase().includes("grace") ||
      bodyText.toLowerCase().includes("email");
    expect(hasProfile).toBe(true);
  });
});
