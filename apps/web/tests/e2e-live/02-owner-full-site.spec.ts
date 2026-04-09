/**
 * Suite 02: Owner Account — Full Site Navigation
 *
 * Owner has full access. Tests every major section of the site.
 */
import { test, expect } from "@playwright/test";
import { login, screenshot, visitAndCapture } from "./helpers";

test.describe("Owner — Full Site Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "owner");
  });

  test("02-01: Dashboard loads with company data", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/dashboard",
      "02-01-owner-dashboard",
    );
    // Should show company name or dashboard content
    const hasContent =
      bodyText.toLowerCase().includes("central") ||
      bodyText.toLowerCase().includes("dashboard") ||
      bodyText.toLowerCase().includes("employee");
    expect(hasContent).toBe(true);
  });

  test("02-02: Employee list loads", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/employees",
      "02-02-owner-employees",
    );
    const hasEmployees =
      bodyText.toLowerCase().includes("employee") ||
      bodyText.toLowerCase().includes("name") ||
      bodyText.toLowerCase().includes("department");
    expect(hasEmployees).toBe(true);
  });

  test("02-03: Leave management accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/leave",
      "02-03-owner-leave",
    );
    const hasLeave =
      bodyText.toLowerCase().includes("leave") ||
      bodyText.toLowerCase().includes("annual") ||
      bodyText.toLowerCase().includes("application");
    expect(hasLeave).toBe(true);
  });

  test("02-04: Payroll accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/payroll",
      "02-04-owner-payroll",
    );
    const hasPayroll =
      bodyText.toLowerCase().includes("payroll") ||
      bodyText.toLowerCase().includes("salary") ||
      bodyText.toLowerCase().includes("run");
    expect(hasPayroll).toBe(true);
  });

  test("02-05: Advisory chat accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/advisory",
      "02-05-owner-advisory",
    );
    const hasAdvisory =
      bodyText.toLowerCase().includes("advisory") ||
      bodyText.toLowerCase().includes("ask") ||
      bodyText.toLowerCase().includes("question") ||
      bodyText.toLowerCase().includes("chat");
    expect(hasAdvisory).toBe(true);
  });

  test("02-06: Calculators — CPF", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/calculators/cpf",
      "02-06-owner-calc-cpf",
    );
    const hasCPF =
      bodyText.toLowerCase().includes("cpf") ||
      bodyText.toLowerCase().includes("contribution") ||
      bodyText.toLowerCase().includes("calculator");
    expect(hasCPF).toBe(true);
  });

  test("02-07: Calculators — Leave", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/calculators/leave",
      "02-07-owner-calc-leave",
    );
    const hasLeave =
      bodyText.toLowerCase().includes("leave") ||
      bodyText.toLowerCase().includes("entitlement") ||
      bodyText.toLowerCase().includes("calculator");
    expect(hasLeave).toBe(true);
  });

  test("02-08: Calculators — Salary", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/calculators/salary",
      "02-08-owner-calc-salary",
    );
    const hasSalary =
      bodyText.toLowerCase().includes("salary") ||
      bodyText.toLowerCase().includes("breakdown") ||
      bodyText.toLowerCase().includes("calculator");
    expect(hasSalary).toBe(true);
  });

  test("02-09: Documents page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/documents",
      "02-09-owner-documents",
    );
    const hasDocs =
      bodyText.toLowerCase().includes("document") ||
      bodyText.toLowerCase().includes("template") ||
      bodyText.toLowerCase().includes("generate");
    expect(hasDocs).toBe(true);
  });

  test("02-10: Company profile accessible", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/profile",
      "02-10-owner-profile",
    );
    const hasProfile =
      bodyText.toLowerCase().includes("company") ||
      bodyText.toLowerCase().includes("profile") ||
      bodyText.toLowerCase().includes("central");
    expect(hasProfile).toBe(true);
  });

  test("02-11: Admin panel accessible (owner-only)", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/admin",
      "02-11-owner-admin",
    );
    // Should load, not redirect or show access denied
    const url = page.url();
    expect(url).not.toContain("/login");
    const hasAdmin =
      bodyText.toLowerCase().includes("admin") ||
      bodyText.toLowerCase().includes("qa") ||
      bodyText.toLowerCase().includes("regulatory") ||
      bodyText.toLowerCase().includes("knowledge");
    expect(hasAdmin).toBe(true);
  });

  test("02-12: Compliance page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/compliance",
      "02-12-owner-compliance",
    );
    const hasCompliance =
      bodyText.toLowerCase().includes("compliance") ||
      bodyText.toLowerCase().includes("regulatory") ||
      bodyText.toLowerCase().includes("employment");
    expect(hasCompliance).toBe(true);
  });

  test("02-13: Attendance page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/attendance",
      "02-13-owner-attendance",
    );
    const hasAttendance =
      bodyText.toLowerCase().includes("attendance") ||
      bodyText.toLowerCase().includes("clock") ||
      bodyText.toLowerCase().includes("time");
    expect(hasAttendance).toBe(true);
  });

  test("02-14: Claims page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/claims",
      "02-14-owner-claims",
    );
    const hasClaims =
      bodyText.toLowerCase().includes("claim") ||
      bodyText.toLowerCase().includes("expense") ||
      bodyText.toLowerCase().includes("receipt");
    expect(hasClaims).toBe(true);
  });

  test("02-15: Shifts page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/shifts",
      "02-15-owner-shifts",
    );
    const hasShifts =
      bodyText.toLowerCase().includes("shift") ||
      bodyText.toLowerCase().includes("schedule") ||
      bodyText.toLowerCase().includes("roster");
    expect(hasShifts).toBe(true);
  });

  test("02-16: Appraisals page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/appraisals",
      "02-16-owner-appraisals",
    );
    const hasAppraisals =
      bodyText.toLowerCase().includes("appraisal") ||
      bodyText.toLowerCase().includes("performance") ||
      bodyText.toLowerCase().includes("review");
    expect(hasAppraisals).toBe(true);
  });

  test("02-17: Policies page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/policies",
      "02-17-owner-policies",
    );
    const hasPolicies =
      bodyText.toLowerCase().includes("polic") ||
      bodyText.toLowerCase().includes("handbook") ||
      bodyText.toLowerCase().includes("guideline");
    expect(hasPolicies).toBe(true);
  });

  test("02-18: Recruitment page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/recruitment",
      "02-18-owner-recruitment",
    );
    const hasRecruitment =
      bodyText.toLowerCase().includes("recruit") ||
      bodyText.toLowerCase().includes("job") ||
      bodyText.toLowerCase().includes("candidate") ||
      bodyText.toLowerCase().includes("hiring");
    expect(hasRecruitment).toBe(true);
  });

  test("02-19: Inventory page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/inventory",
      "02-19-owner-inventory",
    );
    const hasInventory =
      bodyText.toLowerCase().includes("inventory") ||
      bodyText.toLowerCase().includes("asset") ||
      bodyText.toLowerCase().includes("equipment");
    expect(hasInventory).toBe(true);
  });

  test("02-20: Projects page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/projects",
      "02-20-owner-projects",
    );
    const hasProjects =
      bodyText.toLowerCase().includes("project") ||
      bodyText.toLowerCase().includes("assignment") ||
      bodyText.toLowerCase().includes("costing");
    expect(hasProjects).toBe(true);
  });

  test("02-21: Settings page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/settings/notifications",
      "02-21-owner-settings",
    );
    const hasSettings =
      bodyText.toLowerCase().includes("setting") ||
      bodyText.toLowerCase().includes("notification") ||
      bodyText.toLowerCase().includes("preference");
    expect(hasSettings).toBe(true);
  });

  test("02-22: Alerts page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/alerts",
      "02-22-owner-alerts",
    );
    const url = page.url();
    // Should not redirect to login
    expect(url).not.toContain("/login");
  });

  test("02-23: Emergency page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/emergency",
      "02-23-owner-emergency",
    );
    const hasEmergency =
      bodyText.toLowerCase().includes("emergency") ||
      bodyText.toLowerCase().includes("crisis") ||
      bodyText.toLowerCase().includes("response");
    expect(hasEmergency).toBe(true);
  });

  test("02-24: Help page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/help",
      "02-24-owner-help",
    );
    const hasHelp =
      bodyText.toLowerCase().includes("help") ||
      bodyText.toLowerCase().includes("faq") ||
      bodyText.toLowerCase().includes("getting started") ||
      bodyText.toLowerCase().includes("guide");
    expect(hasHelp).toBe(true);
  });

  test("02-25: My Profile page", async ({ page }) => {
    const { bodyText } = await visitAndCapture(
      page,
      "/my-profile",
      "02-25-owner-my-profile",
    );
    const hasProfile =
      bodyText.toLowerCase().includes("profile") ||
      bodyText.toLowerCase().includes("demo admin") ||
      bodyText.toLowerCase().includes("email");
    expect(hasProfile).toBe(true);
  });
});
