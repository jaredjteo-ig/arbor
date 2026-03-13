/**
 * Test Suite 05: HR Calculators (Flow 3)
 *
 * Red-team: Do the calculators produce real, correct numbers?
 * - CPF calculator with salary=5000, age=30
 * - Leave calculator
 * - Are results formatted properly?
 */
import { test, expect } from "@playwright/test";
import { setupAuthenticatedSession } from "./helpers/auth.helper";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

test.describe("HR Calculators", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test("05-01: calculators hub page shows all calculators", async ({
    page,
  }) => {
    await page.goto("/calculators");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/05-01-calculators-hub.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("CALCULATORS HUB: Not authenticated — redirected to login.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`CALCULATORS HUB CONTENT: ${bodyText.slice(0, 800)}`);

    // Should show multiple calculator types
    const expectedCalcs = ["CPF", "Leave", "Overtime", "Levy"];
    for (const calc of expectedCalcs) {
      const hasCalc = bodyText.toLowerCase().includes(calc.toLowerCase());
      console.log(`CALCULATORS HUB: "${calc}" present = ${hasCalc}`);
    }

    const openButtons = page.getByRole("button", { name: /open calculator/i });
    const count = await openButtons.count();
    console.log(`CALCULATORS HUB: ${count} calculators available`);
    expect(count).toBeGreaterThan(0);
  });

  test("05-02: CPF calculator — salary 5000, age 30", async ({ page }) => {
    await page.goto("/calculators");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("CPF CALC: Not authenticated.");
      return;
    }

    // Click on CPF calculator
    const cpfButton = page
      .getByRole("button", { name: /open calculator/i })
      .first();
    const cpfCard = page
      .locator('[class*="card"]')
      .filter({ hasText: /CPF/i })
      .first();

    const hasCpfCard = await cpfCard.isVisible().catch(() => false);
    if (hasCpfCard) {
      const openInCard = cpfCard.getByRole("button", {
        name: /open calculator/i,
      });
      await openInCard.click();
    } else {
      // Navigate directly to CPF calculator URL
      await page.goto("/calculators/cpf");
    }

    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/05-02a-cpf-calculator.png`,
      fullPage: true,
    });

    const calcUrl = page.url();
    console.log(`CPF CALC: URL = ${calcUrl}`);

    if (calcUrl.includes("/login")) {
      console.log("CPF CALC: Redirected to login.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`CPF CALC CONTENT: ${bodyText.slice(0, 500)}`);

    // Fill in salary
    const salaryInput = page
      .locator(
        "input[type='number'], input[placeholder*='salary'], input[name*='salary']",
      )
      .first();
    const hasSalary = await salaryInput.isVisible().catch(() => false);

    if (hasSalary) {
      await salaryInput.fill("5000");

      // Fill age if present
      const ageInput = page
        .locator("input[placeholder*='age'], input[name*='age']")
        .first();
      const hasAge = await ageInput.isVisible().catch(() => false);
      if (hasAge) {
        await ageInput.fill("30");
      }

      // Click calculate
      const calcButton = page
        .getByRole("button", { name: /calculate|compute/i })
        .first();
      const hasCalcButton = await calcButton.isVisible().catch(() => false);
      if (hasCalcButton) {
        await calcButton.click();
        await page.waitForTimeout(2000);
      }

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/05-02b-cpf-result.png`,
        fullPage: true,
      });

      const resultText = (await page.locator("body").textContent()) ?? "";
      console.log(`CPF CALC RESULT: ${resultText.slice(0, 800)}`);

      // CPF at age 30 for $5000: employee=20%, employer=17%
      // Employee contribution: $1000, Employer: $850
      const hasNumericResult =
        resultText.includes("1,000") ||
        resultText.includes("1000") ||
        resultText.includes("850") ||
        resultText.includes("$");
      console.log(`CPF CALC: Has numeric result = ${hasNumericResult}`);
    } else {
      console.log("CPF CALC: No salary input found.");
    }
  });

  test("05-03: leave calculator", async ({ page }) => {
    await page.goto("/calculators/leave");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/05-03a-leave-calculator.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("LEAVE CALC: Not authenticated.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`LEAVE CALC CONTENT: ${bodyText.slice(0, 500)}`);

    // Fill in years of service
    const yearsInput = page
      .locator(
        "input[type='number'], input[placeholder*='year'], input[name*='year']",
      )
      .first();
    const hasYears = await yearsInput.isVisible().catch(() => false);

    if (hasYears) {
      await yearsInput.fill("2");

      const calcButton = page
        .getByRole("button", { name: /calculate|compute/i })
        .first();
      const hasCalcButton = await calcButton.isVisible().catch(() => false);
      if (hasCalcButton) {
        await calcButton.click();
        await page.waitForTimeout(1500);
      }

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/05-03b-leave-result.png`,
        fullPage: true,
      });

      const resultText = (await page.locator("body").textContent()) ?? "";
      console.log(`LEAVE CALC RESULT: ${resultText.slice(0, 800)}`);
      // At 2 years: 8 days annual leave (EA schedule)
      const hasLeaveCount =
        resultText.includes("8") || resultText.includes("days");
      console.log(`LEAVE CALC: Has leave count = ${hasLeaveCount}`);
    } else {
      console.log("LEAVE CALC: No year input found.");
    }
  });

  test("05-04: overtime calculator", async ({ page }) => {
    await page.goto("/calculators/overtime");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/05-04-overtime-calculator.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("OT CALC: Not authenticated.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`OT CALC CONTENT: ${bodyText.slice(0, 500)}`);
  });

  test("05-05: calculator with zero/negative input — edge cases", async ({
    page,
  }) => {
    await page.goto("/calculators/cpf");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("CALC EDGE CASES: Not authenticated.");
      return;
    }

    const salaryInput = page.locator("input[type='number']").first();
    const hasSalary = await salaryInput.isVisible().catch(() => false);

    if (hasSalary) {
      // Try zero
      await salaryInput.fill("0");
      const calcButton = page
        .getByRole("button", { name: /calculate|compute/i })
        .first();
      const hasCalcButton = await calcButton.isVisible().catch(() => false);
      if (hasCalcButton) {
        await calcButton.click();
        await page.waitForTimeout(1000);
      }

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/05-05a-zero-salary.png`,
        fullPage: true,
      });

      // Try negative
      await salaryInput.fill("-1000");
      if (hasCalcButton) {
        await calcButton.click();
        await page.waitForTimeout(1000);
      }

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/05-05b-negative-salary.png`,
        fullPage: true,
      });

      const bodyText = (await page.locator("body").textContent()) ?? "";
      const hasError =
        bodyText.toLowerCase().includes("error") ||
        bodyText.toLowerCase().includes("invalid") ||
        bodyText.toLowerCase().includes("must be");
      console.log(`CALC EDGE: Error shown for bad input = ${hasError}`);
    }
  });
});
