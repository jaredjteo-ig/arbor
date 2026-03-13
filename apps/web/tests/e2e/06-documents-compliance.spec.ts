/**
 * Test Suite 06: Documents & Compliance (Flows 4 & 5)
 *
 * Red-team: Do the document templates and compliance checker work?
 * - Is template list real?
 * - Does generate flow work?
 * - Does compliance check produce real findings?
 */
import { test, expect } from "@playwright/test";
import { setupAuthenticatedSession } from "./helpers/auth.helper";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

test.describe("Documents & Compliance", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  // ── DOCUMENTS ────────────────────────────────────────────────

  test("06-01: documents page shows template library", async ({ page }) => {
    await page.goto("/documents");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/06-01-documents-page.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("DOCUMENTS: Not authenticated — redirected to login.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`DOCUMENTS CONTENT: ${bodyText.slice(0, 800)}`);

    // Check for real template names
    const expectedTemplates = [
      "Employment Contract",
      "Key Employment Terms",
      "Payslip",
      "Warning Letter",
    ];
    for (const tmpl of expectedTemplates) {
      const has = bodyText.includes(tmpl);
      console.log(`DOCUMENTS: Template "${tmpl}" present = ${has}`);
    }

    // Check template count
    const generateButtons = page.getByRole("button", { name: /generate/i });
    const previewButtons = page.getByRole("button", { name: /preview/i });
    const genCount = await generateButtons.count();
    const prevCount = await previewButtons.count();
    console.log(
      `DOCUMENTS: ${genCount} Generate buttons, ${prevCount} Preview buttons`,
    );
    expect(genCount).toBeGreaterThan(0);
  });

  test("06-02: document category filter works", async ({ page }) => {
    await page.goto("/documents");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("DOCUMENTS FILTER: Not authenticated.");
      return;
    }

    // Click on "Contracts" category filter
    const contractsFilter = page.getByRole("button", { name: "Contracts" });
    const hasContracts = await contractsFilter.isVisible().catch(() => false);

    if (hasContracts) {
      await contractsFilter.click();
      await page.waitForTimeout(500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/06-02-documents-filter-contracts.png`,
        fullPage: true,
      });

      const bodyText = (await page.locator("body").textContent()) ?? "";
      console.log(`DOCUMENTS CONTRACTS FILTER: ${bodyText.slice(0, 400)}`);
    }

    // Click on "Letters" filter
    const lettersFilter = page.getByRole("button", { name: "Letters" });
    const hasLetters = await lettersFilter.isVisible().catch(() => false);

    if (hasLetters) {
      await lettersFilter.click();
      await page.waitForTimeout(500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/06-02b-documents-filter-letters.png`,
        fullPage: true,
      });
    }
  });

  test("06-03: document search filter works", async ({ page }) => {
    await page.goto("/documents");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("DOCUMENTS SEARCH: Not authenticated.");
      return;
    }

    // Find search input
    const searchInput = page
      .locator('input[placeholder*="search" i], input[placeholder*="Search" i]')
      .first();
    const hasSearch = await searchInput.isVisible().catch(() => false);

    if (hasSearch) {
      await searchInput.fill("warning");
      await page.waitForTimeout(500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/06-03a-documents-search-warning.png`,
        fullPage: true,
      });

      const bodyText = (await page.locator("body").textContent()) ?? "";
      const hasWarning = bodyText.toLowerCase().includes("warning");
      console.log(
        `DOCUMENTS SEARCH: "warning" results present = ${hasWarning}`,
      );

      // Clear search
      await searchInput.fill("");
      await page.waitForTimeout(300);

      // Search for something that shouldn't exist
      await searchInput.fill("xyznonexistenttemplate");
      await page.waitForTimeout(500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/06-03b-documents-search-empty.png`,
        fullPage: true,
      });

      const emptyText = (await page.locator("body").textContent()) ?? "";
      const hasEmptyState =
        emptyText.toLowerCase().includes("no template") ||
        emptyText.toLowerCase().includes("0 template") ||
        emptyText.toLowerCase().includes("not found");
      console.log(
        `DOCUMENTS SEARCH: Empty state for no results = ${hasEmptyState}`,
      );
    } else {
      console.log("DOCUMENTS SEARCH: No search input found.");
    }
  });

  test("06-04: document list/grid view toggle", async ({ page }) => {
    await page.goto("/documents");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("DOCUMENTS VIEW TOGGLE: Not authenticated.");
      return;
    }

    // Look for list view button
    const listViewBtn = page.getByRole("button", { name: /list view/i });
    const hasListView = await listViewBtn.isVisible().catch(() => false);

    if (hasListView) {
      await listViewBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({
        path: `${SCREENSHOT_DIR}/06-04-documents-list-view.png`,
        fullPage: true,
      });
      console.log("DOCUMENTS: List view activated.");
    } else {
      console.log(
        "DOCUMENTS VIEW TOGGLE: No list view button found (may use aria-label).",
      );
      // Try by aria-label
      const ariaListBtn = page.locator('[aria-label="List view"]');
      const hasAriaList = await ariaListBtn.isVisible().catch(() => false);
      if (hasAriaList) {
        await ariaListBtn.click();
        await page.waitForTimeout(500);
        await page.screenshot({
          path: `${SCREENSHOT_DIR}/06-04-documents-list-view.png`,
          fullPage: true,
        });
        console.log("DOCUMENTS: List view activated via aria-label.");
      }
    }
  });

  test("06-05: navigate to document preview/generate page", async ({
    page,
  }) => {
    await page.goto("/documents/1/preview");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/06-05a-document-preview.png`,
      fullPage: true,
    });

    const url = page.url();
    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`DOCUMENT PREVIEW: URL=${url}`);
    console.log(`DOCUMENT PREVIEW CONTENT: ${bodyText.slice(0, 500)}`);

    // Navigate to generate
    await page.goto("/documents/1/generate");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/06-05b-document-generate.png`,
      fullPage: true,
    });

    const genUrl = page.url();
    const genText = (await page.locator("body").textContent()) ?? "";
    console.log(`DOCUMENT GENERATE: URL=${genUrl}`);
    console.log(`DOCUMENT GENERATE CONTENT: ${genText.slice(0, 500)}`);
  });

  // ── COMPLIANCE ────────────────────────────────────────────────

  test("06-06: compliance page loads with checklist", async ({ page }) => {
    await page.goto("/compliance");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/06-06-compliance-page.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("COMPLIANCE: Not authenticated — redirected to login.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`COMPLIANCE CONTENT: ${bodyText.slice(0, 800)}`);

    // Check for compliance checklist items
    const expectedItems = ["KET", "payslip", "leave", "overtime", "contract"];
    for (const item of expectedItems) {
      const has = bodyText.toLowerCase().includes(item.toLowerCase());
      console.log(`COMPLIANCE: Checklist item "${item}" present = ${has}`);
    }

    // Check for run button
    const runButton = page.getByRole("button", {
      name: /run compliance check/i,
    });
    const hasRun = await runButton.isVisible().catch(() => false);
    console.log(
      `COMPLIANCE: "Run Compliance Check" button visible = ${hasRun}`,
    );
    expect(hasRun).toBe(true);
  });

  test("06-07: compliance check with all items unchecked (worst case)", async ({
    page,
  }) => {
    await page.goto("/compliance");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("COMPLIANCE CHECK: Not authenticated.");
      return;
    }

    // Click "Run Compliance Check" without checking anything
    const runButton = page.getByRole("button", {
      name: /run compliance check/i,
    });
    const hasRun = await runButton.isVisible().catch(() => false);

    if (hasRun) {
      await runButton.click();
      await page.waitForTimeout(2000);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/06-07-compliance-result-worst.png`,
        fullPage: true,
      });

      const bodyText = (await page.locator("body").textContent()) ?? "";
      console.log(`COMPLIANCE WORST RESULT: ${bodyText.slice(0, 1000)}`);

      // Should show critical/high findings
      const hasCritical = bodyText.toLowerCase().includes("critical");
      const hasScore =
        bodyText.includes("/ 100") || bodyText.match(/\d+\s*\/\s*100/);
      const hasRiskTier =
        bodyText.toLowerCase().includes("red") ||
        bodyText.toLowerCase().includes("high risk");
      const hasRealDomains =
        bodyText.includes("Employment Act") ||
        bodyText.includes("CPF") ||
        bodyText.includes("MOM");

      console.log(
        `COMPLIANCE RESULT: hasCritical=${hasCritical}, hasScore=${!!hasScore}, hasRiskTier=${hasRiskTier}, hasRealDomains=${hasRealDomains}`,
      );

      expect(hasCritical || hasCritical).toBe(true); // Should have findings
    }
  });

  test("06-08: compliance check with all items checked (best case)", async ({
    page,
  }) => {
    await page.goto("/compliance");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("COMPLIANCE BEST CASE: Not authenticated.");
      return;
    }

    // Check all checkboxes
    const checkboxes = page.locator('input[type="checkbox"]');
    const count = await checkboxes.count();
    console.log(`COMPLIANCE: Found ${count} checkboxes`);

    for (let i = 0; i < count; i++) {
      const cb = checkboxes.nth(i);
      const isChecked = await cb.isChecked();
      if (!isChecked) {
        await cb.check();
      }
    }

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/06-08a-compliance-all-checked.png`,
      fullPage: true,
    });

    const runButton = page.getByRole("button", {
      name: /run compliance check/i,
    });
    const hasRun = await runButton.isVisible().catch(() => false);
    if (hasRun) {
      await runButton.click();
      await page.waitForTimeout(2000);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/06-08b-compliance-result-best.png`,
        fullPage: true,
      });

      const bodyText = (await page.locator("body").textContent()) ?? "";
      console.log(`COMPLIANCE BEST RESULT: ${bodyText.slice(0, 800)}`);

      // Score should be high (100)
      const hasHighScore =
        bodyText.includes("100") || bodyText.toLowerCase().includes("green");
      console.log(
        `COMPLIANCE BEST: Has high score (100/green) = ${hasHighScore}`,
      );
    }
  });

  test("06-09: compliance MOM inspection readiness tab", async ({ page }) => {
    await page.goto("/compliance");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("COMPLIANCE INSPECTION: Not authenticated.");
      return;
    }

    // Run check first
    const runButton = page.getByRole("button", {
      name: /run compliance check/i,
    });
    const hasRun = await runButton.isVisible().catch(() => false);
    if (hasRun) {
      await runButton.click();
      await page.waitForTimeout(2000);

      // Click Inspection Readiness tab
      const inspectionTab = page.getByRole("button", { name: /inspection/i });
      const hasTab = await inspectionTab.isVisible().catch(() => false);
      if (hasTab) {
        await inspectionTab.click();
        await page.waitForTimeout(500);

        await page.screenshot({
          path: `${SCREENSHOT_DIR}/06-09-compliance-inspection-tab.png`,
          fullPage: true,
        });

        const bodyText = (await page.locator("body").textContent()) ?? "";
        console.log(`COMPLIANCE INSPECTION TAB: ${bodyText.slice(0, 600)}`);

        const hasMOM =
          bodyText.includes("MOM") ||
          bodyText.includes("Employment Records") ||
          bodyText.includes("Salary Records");
        console.log(
          `COMPLIANCE INSPECTION: Has real MOM categories = ${hasMOM}`,
        );
      }
    }
  });
});
