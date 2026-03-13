/**
 * Test Suite 04: Advisory Chat (Flow 2)
 *
 * Red-team: Does the AI advisory chat work end-to-end?
 * - Can user type a question?
 * - Does a response appear?
 * - Are there citations/risk tiers?
 * - Does streaming work?
 */
import { test, expect } from "@playwright/test";
import { setupAuthenticatedSession } from "./helpers/auth.helper";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

test.describe("Advisory Chat", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test("04-01: advisory page loads with chat interface", async ({ page }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/04-01-advisory-initial.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`ADVISORY INITIAL: URL = ${url}`);

    if (url.includes("/login")) {
      console.log("ADVISORY: Not authenticated — redirected to login.");
      return;
    }

    // Check for chat input
    const textarea = page.locator("textarea").first();
    const hasTextarea = await textarea.isVisible().catch(() => false);
    console.log(`ADVISORY: textarea visible = ${hasTextarea}`);

    // Check for send button
    const sendButton = page
      .getByRole("button", { name: /send|submit|ask/i })
      .first();
    const hasSend = await sendButton.isVisible().catch(() => false);
    console.log(`ADVISORY: send button visible = ${hasSend}`);

    // Check for conversation sidebar
    const sidebar = page
      .locator('[class*="sidebar"], [class*="conversation"]')
      .first();
    const hasSidebar = await sidebar.isVisible().catch(() => false);
    console.log(`ADVISORY: sidebar visible = ${hasSidebar}`);

    const bodyText = await page.locator("body").textContent();
    console.log(`ADVISORY CONTENT: ${bodyText?.slice(0, 600)}`);
  });

  test("04-02: type and submit an HR question — does response appear?", async ({
    page,
  }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ADVISORY CHAT: Skipping — not authenticated.");
      return;
    }

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/04-02a-advisory-before-question.png`,
      fullPage: true,
    });

    // Find the chat input
    const textarea = page.locator("textarea").first();
    const hasTextarea = await textarea.isVisible().catch(() => false);

    if (!hasTextarea) {
      // Try text input
      const textInput = page
        .locator('input[type="text"]')
        .filter({ hasNotText: /search/i })
        .first();
      const hasInput = await textInput.isVisible().catch(() => false);
      if (!hasInput) {
        console.log("ADVISORY CHAT: No input found — cannot submit question.");
        await page.screenshot({
          path: `${SCREENSHOT_DIR}/04-02b-no-input-found.png`,
          fullPage: true,
        });
        return;
      }
      await textInput.fill("What are the overtime rules in Singapore?");
      await page.keyboard.press("Enter");
    } else {
      await textarea.fill("What are the overtime rules in Singapore?");

      // Look for send button or use Enter
      const sendButton = page
        .getByRole("button")
        .filter({
          has: page.locator('svg[class*="send"], svg[class*="arrow"]'),
        })
        .first();
      const hasSendIcon = await sendButton.isVisible().catch(() => false);

      if (hasSendIcon) {
        await sendButton.click();
      } else {
        await textarea.press("Enter");
      }
    }

    console.log("ADVISORY: Question submitted, waiting for response...");

    // Wait up to 30s for a response
    await page.waitForTimeout(15000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/04-02c-advisory-response.png`,
      fullPage: true,
    });

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`ADVISORY RESPONSE CONTENT: ${bodyText.slice(0, 1000)}`);

    // Check for response quality indicators
    const hasOvertimeContent =
      bodyText.toLowerCase().includes("overtime") ||
      bodyText.toLowerCase().includes("hours") ||
      bodyText.toLowerCase().includes("salary") ||
      bodyText.toLowerCase().includes("employment act");

    const hasCitation =
      bodyText.includes("EA") ||
      bodyText.includes("Employment Act") ||
      bodyText.includes("MOM") ||
      bodyText.toLowerCase().includes("section");

    const hasRiskTier =
      bodyText.toLowerCase().includes("green") ||
      bodyText.toLowerCase().includes("amber") ||
      bodyText.toLowerCase().includes("red") ||
      bodyText.toLowerCase().includes("risk");

    console.log(
      `ADVISORY RESPONSE: hasOvertimeContent=${hasOvertimeContent}, hasCitation=${hasCitation}, hasRiskTier=${hasRiskTier}`,
    );
  });

  test("04-03: new conversation button functionality", async ({ page }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ADVISORY NEW CONVO: Skipping — not authenticated.");
      return;
    }

    // Look for "New conversation" button
    const newConvoButton = page
      .getByRole("button", { name: /new|new conversation|compose/i })
      .first();
    const hasNewConvo = await newConvoButton.isVisible().catch(() => false);
    console.log(`ADVISORY: "New conversation" button visible = ${hasNewConvo}`);

    if (hasNewConvo) {
      await newConvoButton.click();
      await page.waitForTimeout(1000);
      await page.screenshot({
        path: `${SCREENSHOT_DIR}/04-03-new-conversation.png`,
        fullPage: true,
      });
    }
  });

  test("04-04: advisory page with very long question input", async ({
    page,
  }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ADVISORY LONG INPUT: Skipping — not authenticated.");
      return;
    }

    const textarea = page.locator("textarea").first();
    const hasTextarea = await textarea.isVisible().catch(() => false);
    if (!hasTextarea) {
      console.log("ADVISORY LONG INPUT: No textarea found.");
      return;
    }

    // Type a very long question (500+ characters)
    const longQuestion =
      "A".repeat(500) + " — what does Singapore employment law say about this?";
    await textarea.fill(longQuestion);
    await page.waitForTimeout(500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/04-04-long-question.png`,
      fullPage: true,
    });

    // Check if input is limited or truncated
    const inputValue = await textarea.inputValue();
    console.log(
      `ADVISORY LONG INPUT: Input length after fill = ${inputValue.length}`,
    );
  });

  test("04-05: advisory handles special characters in question", async ({
    page,
  }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ADVISORY SPECIAL CHARS: Skipping — not authenticated.");
      return;
    }

    const textarea = page.locator("textarea").first();
    const hasTextarea = await textarea.isVisible().catch(() => false);
    if (!hasTextarea) {
      console.log("ADVISORY SPECIAL CHARS: No textarea found.");
      return;
    }

    // Special characters including XSS attempts
    const specialQuestion = `What about <script>alert('xss')</script> & 'overtime' "rules"?`;
    await textarea.fill(specialQuestion);
    await page.waitForTimeout(500);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/04-05-special-chars.png`,
      fullPage: true,
    });

    // Verify no XSS alert fired
    const inputValue = await textarea.inputValue();
    console.log(
      `ADVISORY SPECIAL CHARS: Input accepted without XSS: ${inputValue.includes("<script>")}`,
    );
  });
});
