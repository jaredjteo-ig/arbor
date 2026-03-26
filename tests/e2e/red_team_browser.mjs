#!/usr/bin/env node
/**
 * Red Team: Browser UI Advisory Tests via Playwright
 *
 * Runs all 7 tests through the actual browser UI at arbor.terrene.foundation,
 * taking screenshots at each step. Test 5 (multi-domain) runs 3 times for
 * intermittency checking.
 *
 * Usage: node tests/e2e/red_team_browser.mjs
 */

import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const BASE_URL = process.env.ARBOR_URL || "https://arbor.terrene.foundation";
const EMAIL = "test@arbor.dev";
const PASSWORD = "TestPass2026";
const SCREENSHOT_DIR = path.resolve("tests/e2e/screenshots/redteam-browser");
const TIMEOUT = 120_000; // 2 min for advisory responses

// Ensure screenshot directory exists
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const results = [];

function addResult(name, passed, quality, notes, responseTime = 0) {
  results.push({ name, passed, quality, notes, responseTime });
  const status = passed ? "PASS" : "FAIL";
  console.log(`  => ${status} | Quality: ${quality} | ${notes}`);
}

async function screenshot(page, name) {
  const filepath = path.join(SCREENSHOT_DIR, `${name}.png`);
  await page.screenshot({ path: filepath, fullPage: true });
  console.log(`  [screenshot] ${filepath}`);
  return filepath;
}

/**
 * Login via API and inject token into browser localStorage,
 * then navigate to dashboard.
 */
async function loginViaAPI(page) {
  console.log("  Logging in via API...");

  // First navigate to the site to set up the origin
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState("domcontentloaded");

  // Call the API directly
  const resp = await page.evaluate(
    async ({ url, email, password }) => {
      const r = await fetch(`${url}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!r.ok) throw new Error(`Login failed: ${r.status}`);
      return r.json();
    },
    { url: BASE_URL, email: EMAIL, password: PASSWORD },
  );

  // Store tokens in localStorage (matching AuthContext patterns)
  await page.evaluate(
    ({ accessToken, refreshToken, user }) => {
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);
      localStorage.setItem("user", JSON.stringify(user));
    },
    {
      accessToken: resp.access_token,
      refreshToken: resp.refresh_token,
      user: resp.user,
    },
  );

  console.log(`  Login successful: ${resp.user.name} (${resp.user.email})`);
  return resp;
}

/**
 * Wait for advisory response to finish streaming.
 * Uses manual polling to avoid Playwright timeout defaults.
 */
async function waitForResponse(page, timeoutMs = TIMEOUT) {
  const start = Date.now();

  // Poll every second until the textarea is re-enabled (streaming done)
  while (Date.now() - start < timeoutMs) {
    const done = await page.evaluate(() => {
      const ta = document.querySelector("textarea");
      if (!ta) return false;
      if (ta.disabled) return false;
      const ph = ta.getAttribute("placeholder") || "";
      if (ph.includes("Waiting") || ph.includes("Listening")) return false;
      // Check that the stop button is gone
      const stopBtn = document.querySelector('[aria-label="Stop generation"]');
      if (stopBtn) return false;
      return true;
    });

    if (done) break;
    await page.waitForTimeout(1000);
  }

  const elapsed = (Date.now() - start) / 1000;
  if (elapsed >= timeoutMs / 1000) {
    console.log(`  [warn] waitForResponse timed out after ${elapsed.toFixed(0)}s`);
  }

  await page.waitForTimeout(1000); // Let DOM settle
  return elapsed;
}

/**
 * Send a message in the advisory chat.
 */
async function sendMessage(page, text) {
  // Find the textarea -- wait for it to be enabled
  const textarea = await page.waitForSelector(
    "textarea:not([disabled])",
    { timeout: 15000 },
  );
  await textarea.click();
  await page.waitForTimeout(300);

  // Clear any existing text and fill
  await textarea.fill("");
  await page.waitForTimeout(100);
  await textarea.fill(text);
  console.log(`  [send] "${text}"`);
  await page.waitForTimeout(300);

  // Press Enter to submit (the ChatInput component handles Enter key)
  await textarea.press("Enter");
  await page.waitForTimeout(500);
}

/**
 * Get the last assistant response text from the chat.
 */
async function getLastResponse(page) {
  const responseText = await page.evaluate(() => {
    // The chat area has class "space-y-4" inside the scrollable area
    const container = document.querySelector(".space-y-4");
    if (!container) {
      return document.body.textContent || "";
    }

    // Chat messages are direct children of the space-y-4 container.
    // User messages use ChatBubble (role="user") and have justify-end.
    // Assistant messages use SystemMessage component with a card-like container.
    const children = Array.from(container.children);

    // Filter to only assistant message divs (non-user, non-empty)
    const assistantDivs = children.filter((child) => {
      const text = (child.textContent || "").trim();
      if (text.length < 5) return false;
      // User messages are wrapped in a div with justify-end
      if (child.classList.contains("justify-end")) return false;
      if (child.querySelector(".justify-end")) {
        // Check if the whole thing is a user bubble
        const userBubble = child.querySelector('[class*="justify-end"]');
        if (userBubble && userBubble === child.firstElementChild) return false;
      }
      return true;
    });

    if (assistantDivs.length === 0) return "";

    // Get the last assistant message
    const lastDiv = assistantDivs[assistantDivs.length - 1];
    return lastDiv.textContent || "";
  });

  return responseText.trim();
}

/**
 * Start a new conversation.
 */
async function newConversation(page) {
  await page.goto(`${BASE_URL}/advisory`);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1500);

  // Try clicking "New" button in sidebar if visible
  try {
    const newBtn = await page.$('button:has-text("New"), [aria-label*="New conversation" i]');
    if (newBtn && await newBtn.isVisible()) {
      await newBtn.click();
      await page.waitForTimeout(500);
    }
  } catch {
    // Already on fresh page
  }
}

// -----------------------------------------------------------------------
// Main test execution
// -----------------------------------------------------------------------

async function main() {
  console.log("=".repeat(70));
  console.log("ARBOR ADVISORY RED TEAM -- Browser UI Tests");
  console.log(`Target: ${BASE_URL}`);
  console.log(`Date: ${new Date().toISOString()}`);
  console.log("=".repeat(70));

  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();
  // No default timeout -- advisory responses can take 60+ seconds
  // Individual operations set their own timeouts

  // Collect console errors
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(msg.text());
    }
  });

  try {
    // ---- LOGIN ----
    console.log("\n" + "=".repeat(70));
    console.log("PHASE 0: Login");
    console.log("=".repeat(70));

    await loginViaAPI(page);

    // Navigate to dashboard to verify auth works
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    await screenshot(page, "00-dashboard");

    // Check if we're actually on the dashboard
    const currentUrl = page.url();
    console.log(`  Current URL: ${currentUrl}`);
    if (currentUrl.includes("login")) {
      console.log("  WARNING: Redirected back to login. Trying form login...");
      // Try filling the form instead
      await page.fill('input[placeholder*="company.com"], input[type="email"]', EMAIL);
      await page.fill('input[type="password"]', PASSWORD);
      await page.click('button:has-text("Log in")');
      await page.waitForTimeout(5000);
      await screenshot(page, "00-form-login-attempt");
      console.log(`  After form login URL: ${page.url()}`);
    }

    // Navigate to Advisory
    console.log("\n  Navigating to Advisory...");
    await page.goto(`${BASE_URL}/advisory`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    await screenshot(page, "00-advisory-landing");

    // Verify we're on the advisory page
    const advisoryUrl = page.url();
    console.log(`  Advisory URL: ${advisoryUrl}`);

    if (advisoryUrl.includes("login")) {
      throw new Error(
        "Cannot access advisory page -- redirected to login. Auth may be broken.",
      );
    }

    // ---- TEST 1: CPF Calculation ----
    console.log("\n" + "=".repeat(70));
    console.log("TEST 1: CPF Calculation");
    console.log("=".repeat(70));

    await newConversation(page);
    await sendMessage(
      page,
      "Calculate CPF for a 45-year-old Singapore citizen earning $7,500/month",
    );
    const t1Elapsed = await waitForResponse(page);
    await screenshot(page, "01-cpf-response");

    const t1Text = await getLastResponse(page);
    console.log(`  Response time: ${t1Elapsed.toFixed(1)}s`);
    console.log(`  Response length: ${t1Text.length} chars`);
    console.log(`  Preview: ${t1Text.substring(0, 300)}...`);

    const t1HasEmployer = t1Text.includes("1,275") || t1Text.includes("1275");
    const t1HasEmployee = t1Text.includes("1,500") || t1Text.includes("1500");
    const t1HasTotal = t1Text.includes("2,775") || t1Text.includes("2775");
    const t1Passed = t1HasEmployer && t1HasEmployee && t1HasTotal;

    const t1Notes = [];
    if (!t1HasEmployer) t1Notes.push("Missing employer $1,275");
    if (!t1HasEmployee) t1Notes.push("Missing employee $1,500");
    if (!t1HasTotal) t1Notes.push("Missing total $2,775");
    const t1Lower = t1Text.toLowerCase();
    const t1HasCitation =
      t1Lower.includes("cpf act") ||
      t1Lower.includes("section") ||
      t1Lower.includes("schedule") ||
      t1Lower.includes("first schedule");
    const t1Quality =
      t1Passed && t1HasCitation ? "EXCELLENT" : t1Passed ? "GOOD" : "POOR";

    addResult(
      "Test 1: CPF Calculation",
      t1Passed,
      t1Quality,
      t1Passed
        ? `All figures correct ($1,275/$1,500/$2,775). Citations: ${t1HasCitation ? "YES" : "NO"}`
        : t1Notes.join("; "),
      t1Elapsed,
    );

    // ---- TEST 2: Maternity Leave ----
    console.log("\n" + "=".repeat(70));
    console.log("TEST 2: Maternity Leave");
    console.log("=".repeat(70));

    await newConversation(page);
    await sendMessage(
      page,
      "How much maternity leave is my employee entitled to?",
    );
    const t2Elapsed = await waitForResponse(page);
    await screenshot(page, "02-maternity-response");

    const t2Text = await getLastResponse(page);
    console.log(`  Response time: ${t2Elapsed.toFixed(1)}s`);
    console.log(`  Preview: ${t2Text.substring(0, 300)}...`);

    const t2Lower = t2Text.toLowerCase();
    const t2Has16Weeks =
      t2Lower.includes("16 week") || t2Lower.includes("16-week");
    const t2HasEA =
      t2Lower.includes("employment act") ||
      t2Lower.includes("part ix") ||
      t2Lower.includes("cdcsa") ||
      t2Lower.includes("child development");
    const t2HasCitizen =
      t2Lower.includes("citizen") ||
      t2Lower.includes("non-citizen") ||
      t2Lower.includes("child");
    const t2Passed = t2Has16Weeks && (t2HasEA || t2HasCitizen);

    const t2Notes = [];
    if (!t2Has16Weeks) t2Notes.push("Missing 16 weeks");
    if (!t2HasEA) t2Notes.push("Missing Employment Act/Part IX/CDCSA");
    if (!t2HasCitizen) t2Notes.push("Missing citizen distinction");
    const t2Quality =
      t2Passed && t2HasEA && t2HasCitizen
        ? "EXCELLENT"
        : t2Passed
          ? "GOOD"
          : "POOR";

    addResult(
      "Test 2: Maternity Leave",
      t2Passed,
      t2Quality,
      t2Passed
        ? `16 weeks confirmed. EA/CDCSA: ${t2HasEA ? "YES" : "NO"}. Citizen: ${t2HasCitizen ? "YES" : "NO"}`
        : t2Notes.join("; "),
      t2Elapsed,
    );

    // ---- TEST 3: S Pass Quota ----
    console.log("\n" + "=".repeat(70));
    console.log("TEST 3: S Pass Quota");
    console.log("=".repeat(70));

    await newConversation(page);
    await sendMessage(
      page,
      "What is the S Pass quota for a services company with 50 local employees?",
    );
    const t3Elapsed = await waitForResponse(page);
    await screenshot(page, "03-spass-response");

    const t3Text = await getLastResponse(page);
    console.log(`  Response time: ${t3Elapsed.toFixed(1)}s`);
    console.log(`  Preview: ${t3Text.substring(0, 300)}...`);

    const t3Lower = t3Text.toLowerCase();
    const t3HasDRC =
      t3Lower.includes("drc") ||
      t3Lower.includes("dependency ratio") ||
      t3Lower.includes("ratio ceiling") ||
      t3Lower.includes("foreign worker");
    const t3Has35 = t3Lower.includes("35%") || t3Lower.includes("35 per");
    const t3HasCalc = ["headroom", "quota", "maximum", "entitled", "cap"].some(
      (w) => t3Lower.includes(w),
    );
    const t3Passed = (t3HasDRC || t3Has35) && t3HasCalc;

    const t3Notes = [];
    if (!t3HasDRC && !t3Has35) t3Notes.push("Missing DRC or 35%");
    if (!t3HasCalc) t3Notes.push("Missing quota calculation");
    const t3Quality =
      t3Passed && t3Has35 ? "EXCELLENT" : t3Passed ? "GOOD" : "POOR";

    addResult(
      "Test 3: S Pass Quota",
      t3Passed,
      t3Quality,
      t3Passed
        ? `DRC/quota info present. 35%: ${t3Has35 ? "YES" : "NO"}`
        : t3Notes.join("; "),
      t3Elapsed,
    );

    // ---- TEST 4: Multi-Turn Context ----
    console.log("\n" + "=".repeat(70));
    console.log("TEST 4: Multi-Turn Context");
    console.log("=".repeat(70));

    await newConversation(page);

    // Turn 1
    await sendMessage(page, "What are the notice period rules?");
    const t4Turn1Elapsed = await waitForResponse(page);
    await screenshot(page, "04-notice-turn1");
    const t4Turn1 = await getLastResponse(page);
    console.log(`  Turn 1 time: ${t4Turn1Elapsed.toFixed(1)}s`);
    console.log(`  Turn 1 preview: ${t4Turn1.substring(0, 200)}...`);

    // Turn 2 -- same conversation (do NOT navigate away)
    await sendMessage(page, "What if they've worked for 6 years?");
    const t4Turn2Elapsed = await waitForResponse(page);
    await screenshot(page, "04-notice-turn2");
    const t4Turn2 = await getLastResponse(page);
    console.log(`  Turn 2 time: ${t4Turn2Elapsed.toFixed(1)}s`);
    console.log(`  Turn 2 preview: ${t4Turn2.substring(0, 300)}...`);

    const t4Lower = t4Turn2.toLowerCase();
    const t4Has4Weeks =
      t4Lower.includes("4 week") || t4Lower.includes("four week") || t4Lower.includes("4-week");
    const t4HasContext = [
      "notice",
      "termination",
      "employment act",
      "section 10",
      "s.10",
      "s 10",
    ].some((w) => t4Lower.includes(w));
    const t4MaintainedContext =
      t4Lower.includes("notice") || t4Lower.includes("terminat");
    const t4Passed = t4Has4Weeks && t4HasContext;

    const t4Notes = [];
    if (!t4Has4Weeks) t4Notes.push("Missing 4 weeks notice");
    if (!t4HasContext) t4Notes.push("Missing notice/EA context");
    if (!t4MaintainedContext) t4Notes.push("LOST CONTEXT");
    const t4Quality =
      t4Passed && t4MaintainedContext ? "EXCELLENT" : t4Passed ? "GOOD" : "POOR";

    addResult(
      "Test 4: Multi-Turn Context",
      t4Passed,
      t4Quality,
      t4Passed
        ? `Context maintained. 4 weeks correct.`
        : t4Notes.join("; "),
      t4Turn1Elapsed + t4Turn2Elapsed,
    );

    // ---- TEST 5: Multi-Domain (CRITICAL -- 3 RUNS) ----
    console.log("\n" + "=".repeat(70));
    console.log("TEST 5: Multi-Domain (CRITICAL -- 3 runs)");
    console.log("=".repeat(70));

    const t5Results = [];
    for (let run = 1; run <= 3; run++) {
      console.log(`\n  --- Run ${run}/3 ---`);
      await newConversation(page);
      await sendMessage(
        page,
        "My foreign worker's EP expires next month and I want to terminate them",
      );
      const t5Elapsed = await waitForResponse(page);
      await screenshot(page, `05-multidomain-run${run}`);

      const t5Text = await getLastResponse(page);
      console.log(`  Response time: ${t5Elapsed.toFixed(1)}s`);
      console.log(`  Response length: ${t5Text.length} chars`);
      console.log(`  Preview: ${t5Text.substring(0, 300)}...`);

      const t5Lower = t5Text.toLowerCase();
      const t5HasWP = [
        "employment pass",
        "work pass",
        "efma",
        "foreign manpower",
        "mom",
        "cancel",
        "repatri",
        "special pass",
        "social visit",
      ].some((w) => t5Lower.includes(w));
      const t5HasTerm = [
        "terminat",
        "notice period",
        "employment act",
        "last day",
        "final salary",
        "notice",
        "dismiss",
      ].some((w) => t5Lower.includes(w));

      const t5Passed = t5HasWP && t5HasTerm;

      const runNotes = [];
      if (!t5HasWP) runNotes.push("Missing work pass/EFMA");
      if (!t5HasTerm) runNotes.push("Missing termination/EA");

      t5Results.push({
        run,
        passed: t5Passed,
        hasWP: t5HasWP,
        hasTerm: t5HasTerm,
        elapsed: t5Elapsed,
        notes: t5Passed ? "Both domains covered" : runNotes.join("; "),
        text: t5Text,
      });

      console.log(
        `  Run ${run}: ${t5Passed ? "PASS" : "FAIL"} | WP: ${t5HasWP} | Term: ${t5HasTerm}`,
      );
    }

    const t5AllPassed = t5Results.every((r) => r.passed);
    const t5PassCount = t5Results.filter((r) => r.passed).length;
    const t5AvgTime =
      t5Results.reduce((s, r) => s + r.elapsed, 0) / t5Results.length;

    const t5FinalQuality = t5AllPassed
      ? "EXCELLENT"
      : t5PassCount >= 2
        ? "GOOD"
        : t5PassCount === 1
          ? "ACCEPTABLE"
          : "POOR";

    addResult(
      "Test 5: Multi-Domain (3 runs)",
      t5AllPassed,
      t5FinalQuality,
      `${t5PassCount}/3 passed. Avg time: ${t5AvgTime.toFixed(1)}s. ${t5Results.map((r) => `Run${r.run}:${r.passed ? "PASS" : "FAIL"}`).join(", ")}`,
      t5AvgTime,
    );

    // ---- TEST 6: Out-of-Scope ----
    console.log("\n" + "=".repeat(70));
    console.log("TEST 6: Out-of-Scope Decline");
    console.log("=".repeat(70));

    await newConversation(page);
    await sendMessage(page, "What is the weather today?");
    const t6Elapsed = await waitForResponse(page);
    await screenshot(page, "06-outofscope-response");

    const t6Text = await getLastResponse(page);
    console.log(`  Response time: ${t6Elapsed.toFixed(1)}s`);
    console.log(`  Response: ${t6Text.substring(0, 400)}`);

    const t6Lower = t6Text.toLowerCase();
    const t6IsError =
      (t6Lower.includes("something went wrong") ||
        t6Lower.includes("failed")) &&
      !t6Lower.includes("hr");
    const t6IsDecline = [
      "hr",
      "employment",
      "payroll",
      "leave",
      "can only help",
      "workplace",
      "rephrase",
      "singapore",
      "not able to help",
      "outside",
      "scope",
      "assist with",
      "speciali",
    ].some((d) => t6Lower.includes(d));

    const t6Passed = t6IsDecline && !t6IsError;
    const t6Quality = t6Passed ? "GOOD" : "POOR";

    addResult(
      "Test 6: Out-of-Scope",
      t6Passed,
      t6Quality,
      t6Passed
        ? "Polite decline (redirects to HR topics)"
        : t6IsError
          ? "Shows error instead of decline"
          : "No polite decline detected",
      t6Elapsed,
    );

    // ---- TEST 7: Conversation Persistence ----
    console.log("\n" + "=".repeat(70));
    console.log("TEST 7: Conversation Persistence");
    console.log("=".repeat(70));

    // Navigate away
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await screenshot(page, "07-navigated-away");

    // Navigate back to advisory
    await page.goto(`${BASE_URL}/advisory`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
    await screenshot(page, "07-back-to-advisory");

    // Check sidebar and page content for conversation titles
    const pageText = await page.evaluate(() => document.body.textContent || "");
    const t7Lower = pageText.toLowerCase();

    const t7HasConversations = [
      "cpf",
      "maternity",
      "leave",
      "notice",
      "weather",
      "foreign",
      "s pass",
      "terminat",
      "ep expire",
      "work pass",
    ].some((kw) => t7Lower.includes(kw));

    // Also try the history page
    let historyWorks = false;
    try {
      await page.goto(`${BASE_URL}/advisory/history`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1500);
      await screenshot(page, "07-history-page");
      const histText = await page.evaluate(
        () => document.body.textContent || "",
      );
      historyWorks = [
        "cpf",
        "maternity",
        "notice",
        "s pass",
        "foreign",
      ].some((kw) => histText.toLowerCase().includes(kw));
      if (historyWorks)
        console.log("  History page shows test conversations");
    } catch (e) {
      console.log("  History page not accessible");
    }

    const t7Passed = t7HasConversations || historyWorks;
    const t7Quality = t7Passed ? "GOOD" : "POOR";

    addResult(
      "Test 7: Conversation Persistence",
      t7Passed,
      t7Quality,
      t7Passed
        ? "Conversations persisted and visible"
        : "No conversation history detected",
      0,
    );

    // ---- FINAL SUMMARY ----
    console.log("\n" + "=".repeat(70));
    console.log("FINAL RESULTS -- Arbor Advisory Red Team (Browser UI)");
    console.log("=".repeat(70));

    const header = `${"Test".padEnd(40)} ${"Pass?".padEnd(7)} ${"Quality".padEnd(12)} ${"Time".padEnd(10)} Notes`;
    console.log(header);
    console.log("-".repeat(120));

    let passCount = 0;
    for (const r of results) {
      const status = r.passed ? "PASS" : "FAIL";
      if (r.passed) passCount++;
      const timeStr =
        r.responseTime > 0 ? `${r.responseTime.toFixed(1)}s` : "n/a";
      console.log(
        `${r.name.padEnd(40)} ${status.padEnd(7)} ${r.quality.padEnd(12)} ${timeStr.padEnd(10)} ${r.notes.substring(0, 80)}`,
      );
    }

    const failCount = results.length - passCount;
    console.log("\n" + "=".repeat(70));
    console.log(
      `TOTAL: ${passCount} PASS, ${failCount} FAIL out of ${results.length} tests`,
    );
    console.log(
      `PASS RATE: ${((passCount / results.length) * 100).toFixed(0)}%`,
    );
    console.log("=".repeat(70));

    // Console errors
    if (consoleErrors.length > 0) {
      console.log(`\nBrowser console errors (${consoleErrors.length}):`);
      for (const err of consoleErrors.slice(0, 15)) {
        console.log(`  [error] ${err.substring(0, 200)}`);
      }
    }

    // Test 5 detailed results
    console.log("\n--- Test 5 Multi-Domain Detail (3 runs) ---");
    for (const r of t5Results) {
      console.log(
        `  Run ${r.run}: ${r.passed ? "PASS" : "FAIL"} | WP: ${r.hasWP} | Term: ${r.hasTerm} | ${r.elapsed.toFixed(1)}s`,
      );
      console.log(`    Response preview: ${r.text.substring(0, 400)}`);
      console.log();
    }

    // Write JSON results
    const jsonPath = path.join(SCREENSHOT_DIR, "results.json");
    fs.writeFileSync(
      jsonPath,
      JSON.stringify(
        {
          timestamp: new Date().toISOString(),
          target: BASE_URL,
          results,
          test5Details: t5Results.map((r) => ({
            run: r.run,
            passed: r.passed,
            hasWP: r.hasWP,
            hasTerm: r.hasTerm,
            elapsed: r.elapsed,
            notes: r.notes,
            responsePreview: r.text.substring(0, 500),
          })),
          consoleErrors: consoleErrors.slice(0, 20),
          passRate: `${passCount}/${results.length}`,
        },
        null,
        2,
      ),
    );
    console.log(`\nResults written to ${jsonPath}`);
    console.log(`Screenshots in ${SCREENSHOT_DIR}/`);

    process.exit(failCount === 0 ? 0 : 1);
  } catch (error) {
    console.error("\nFATAL ERROR:", error.message);
    try {
      await screenshot(page, "fatal-error");
    } catch {}
    console.error(error.stack);
    process.exit(2);
  } finally {
    await browser.close();
  }
}

main();
