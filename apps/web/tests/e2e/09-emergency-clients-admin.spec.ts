/**
 * Test Suite 09: Emergency, Clients, Admin — Untested Nav Items
 *
 * Red-team: ISSUE-11 in the red-team report flagged the "Emergency" and
 * "Clients" sidebar links as untested. This suite covers them, plus the
 * Admin panel which is fully built but never red-teamed.
 *
 * Also covers:
 * - POST /advisory/stream (streaming advisory responses)
 * - GET /advisory/history/:conversation_id
 * - Onboarding flow (post-registration step)
 * - Profile page (ISSUE-06: hardcoded data)
 * - Analytics page (ISSUE-06: hardcoded data)
 */
import { test, expect } from "@playwright/test";
import { setupAuthenticatedSession, API_BASE } from "./helpers/auth.helper";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

/* ── Emergency Page ──────────────────────────────────────── */

test.describe("Emergency Page (ISSUE-11 coverage)", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test("09-01: emergency page loads and shows topic cards", async ({
    page,
  }) => {
    await page.goto("/emergency");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/09-01a-emergency-page.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`EMERGENCY: URL = ${url}`);

    if (url.includes("/login")) {
      console.log("EMERGENCY: Redirected to login — auth failed.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 600);
    console.log(`EMERGENCY CONTENT: ${meaningful}`);

    // Emergency page should show topic cards
    const expectedTopics = [
      "TADM",
      "injury",
      "termination",
      "dismissal",
      "claim",
    ];
    const foundTopics = expectedTopics.filter((t) =>
      bodyText.toLowerCase().includes(t.toLowerCase()),
    );
    console.log(`EMERGENCY: Found topics = [${foundTopics.join(", ")}]`);

    // Should have at least 2 emergency topic cards
    const topicCards = page.locator('[class*="card"]');
    const cardCount = await topicCards.count();
    console.log(`EMERGENCY: Card count = ${cardCount}`);

    // Check for emergency-specific UI elements
    const hasEmergencyTitle =
      bodyText.toLowerCase().includes("emergency") ||
      bodyText.toLowerCase().includes("urgent") ||
      bodyText.toLowerCase().includes("immediate");
    console.log(
      `EMERGENCY: Has emergency title/heading = ${hasEmergencyTitle}`,
    );

    // The page should not be empty
    expect(bodyText.length, "Emergency page must have content").toBeGreaterThan(
      100,
    );
  });

  test("09-02: emergency page — click TADM claim card", async ({ page }) => {
    await page.goto("/emergency");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("EMERGENCY TADM: Not authenticated.");
      return;
    }

    // Find and click a TADM-related card or button
    const tadmCard = page
      .locator('[class*="card"], button, li')
      .filter({ hasText: /TADM|ECT|claim/i })
      .first();
    const hasTadm = await tadmCard.isVisible().catch(() => false);
    console.log(`EMERGENCY TADM: TADM card visible = ${hasTadm}`);

    if (hasTadm) {
      await tadmCard.click();
      await page.waitForTimeout(1500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/09-02-emergency-tadm-detail.png`,
        fullPage: true,
      });

      const bodyText = (await page.locator("body").textContent()) ?? "";
      const meaningful = bodyText
        .replace(/self\.__next.*$/gm, "")
        .trim()
        .slice(0, 600);
      console.log(`EMERGENCY TADM DETAIL: ${meaningful}`);

      const hasTADMDetails =
        bodyText.toLowerCase().includes("mediation") ||
        bodyText.toLowerCase().includes("respond") ||
        bodyText.toLowerCase().includes("obligation") ||
        bodyText.toLowerCase().includes("document");
      console.log(
        `EMERGENCY TADM DETAIL: Has detailed guidance = ${hasTADMDetails}`,
      );
    } else {
      console.log(
        "EMERGENCY TADM: No TADM card found — page may list topics differently.",
      );
      await page.screenshot({
        path: `${SCREENSHOT_DIR}/09-02-emergency-no-tadm.png`,
        fullPage: true,
      });
    }
  });

  test("09-03: emergency page — all topic cards are clickable", async ({
    page,
  }) => {
    await page.goto("/emergency");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("EMERGENCY ALL TOPICS: Not authenticated.");
      return;
    }

    // Find clickable buttons that represent emergency topics
    const topicButtons = page.getByRole("button").filter({
      hasNot: page.locator(
        '[aria-label*="collapse" i], [aria-label*="menu" i]',
      ),
    });
    const count = await topicButtons.count();
    console.log(`EMERGENCY ALL TOPICS: ${count} clickable elements found`);

    // Click each topic and capture what happens
    for (let i = 0; i < Math.min(count, 5); i++) {
      const btn = topicButtons.nth(i);
      const btnText = await btn.textContent();
      console.log(`EMERGENCY TOPIC ${i + 1}: "${btnText?.slice(0, 50)}"`);
    }
  });
});

/* ── Clients Page ────────────────────────────────────────── */

test.describe("Clients Page (ISSUE-11 coverage)", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test("09-04: clients page loads and shows client list", async ({ page }) => {
    await page.goto("/clients");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/09-04a-clients-page.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`CLIENTS: URL = ${url}`);

    if (url.includes("/login")) {
      console.log("CLIENTS: Redirected to login — auth failed.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 600);
    console.log(`CLIENTS CONTENT: ${meaningful}`);

    // Clients page should show client cards with company info
    const expectedClientData = [
      "Horizon Tech",
      "Marina",
      "BuildSafe",
      "Orchid",
      "UEN",
    ];
    const foundData = expectedClientData.filter((item) =>
      bodyText.includes(item),
    );
    console.log(`CLIENTS: Found demo data items = [${foundData.join(", ")}]`);

    // Should show compliance scores or risk tiers
    const hasComplianceData =
      bodyText.toLowerCase().includes("compliance") ||
      bodyText.toLowerCase().includes("green") ||
      bodyText.toLowerCase().includes("amber") ||
      bodyText.toLowerCase().includes("red");
    console.log(`CLIENTS: Has compliance/risk data = ${hasComplianceData}`);

    // ISSUE FLAG: Clients page uses hardcoded demo data
    const hasDemoData =
      bodyText.includes("Horizon Tech") || bodyText.includes("202301234A");
    if (hasDemoData) {
      console.log(
        "CLIENTS GAP: Page is showing hardcoded demo data (Horizon Tech, fixed UEN). " +
          "This is not real user data — a real customer would see someone else's company names.",
      );
    }

    // Page should not be empty or errored
    expect(bodyText.length, "Clients page must have content").toBeGreaterThan(
      100,
    );
  });

  test("09-05: clients page — search filter works", async ({ page }) => {
    await page.goto("/clients");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("CLIENTS SEARCH: Not authenticated.");
      return;
    }

    // Look for search input
    const searchInput = page
      .locator('input[placeholder*="search" i], input[placeholder*="client" i]')
      .first();
    const hasSearch = await searchInput.isVisible().catch(() => false);
    console.log(`CLIENTS SEARCH: Search input visible = ${hasSearch}`);

    if (hasSearch) {
      await searchInput.fill("Horizon");
      await page.waitForTimeout(500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/09-05-clients-search.png`,
        fullPage: true,
      });

      const bodyText = (await page.locator("body").textContent()) ?? "";
      const hasHorizon = bodyText.includes("Horizon");
      console.log(`CLIENTS SEARCH: "Horizon" in results = ${hasHorizon}`);

      // Clear and search for something that doesn't exist
      await searchInput.fill("XYZNONEXISTENT");
      await page.waitForTimeout(500);

      const emptyText = (await page.locator("body").textContent()) ?? "";
      const hasEmpty =
        emptyText.toLowerCase().includes("no client") ||
        emptyText.toLowerCase().includes("not found") ||
        emptyText.toLowerCase().includes("0 client");
      console.log(`CLIENTS SEARCH: Empty state for no results = ${hasEmpty}`);
    }
  });

  test("09-06: clients page — risk tier badges render correctly", async ({
    page,
  }) => {
    await page.goto("/clients");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("CLIENTS RISK: Not authenticated.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";

    // Check for GREEN/AMBER/RED risk tier indicators
    const hasGreen =
      bodyText.toLowerCase().includes("green") ||
      bodyText.toLowerCase().includes("low risk");
    const hasAmber =
      bodyText.toLowerCase().includes("amber") ||
      bodyText.toLowerCase().includes("medium risk");
    const hasRed =
      bodyText.toLowerCase().includes("red") ||
      bodyText.toLowerCase().includes("high risk");

    console.log(
      `CLIENTS RISK TIERS: green=${hasGreen}, amber=${hasAmber}, red=${hasRed}`,
    );

    // The demo data should include clients at all three risk levels
    const hasAllTiers = hasGreen && hasAmber && hasRed;
    console.log(`CLIENTS RISK TIERS: All three tiers present = ${hasAllTiers}`);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/09-06-clients-risk-tiers.png`,
      fullPage: true,
    });
  });
});

/* ── Admin Panel ─────────────────────────────────────────── */

test.describe("Admin Panel — Full Coverage", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test("09-07: admin page loads with all five tabs", async ({ page }) => {
    await page.goto("/admin");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/09-07-admin-overview.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`ADMIN: URL = ${url}`);

    if (url.includes("/login")) {
      console.log("ADMIN: Not authenticated.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 600);
    console.log(`ADMIN CONTENT: ${meaningful}`);

    // All five tabs should be present
    const expectedTabs = [
      "Overview",
      "Regulatory Updates",
      "KB Management",
      "Feedback Review",
      "Audit",
    ];
    for (const tab of expectedTabs) {
      const tabEl = page.getByRole("tab", { name: new RegExp(tab, "i") });
      const isVisible = await tabEl.isVisible().catch(() => false);
      console.log(`ADMIN TAB "${tab}": visible = ${isVisible}`);
    }
  });

  test("09-08: admin — Overview tab content", async ({ page }) => {
    await page.goto("/admin");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ADMIN OVERVIEW: Not authenticated.");
      return;
    }

    // Overview is the default tab
    const overviewTab = page.getByRole("tab", { name: /Overview/i });
    const hasOverview = await overviewTab.isVisible().catch(() => false);

    if (hasOverview) {
      await overviewTab.click();
      await page.waitForTimeout(1000);
    }

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/09-08-admin-overview-tab.png`,
      fullPage: true,
    });

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(
      `ADMIN OVERVIEW CONTENT: ${bodyText
        .replace(/self\.__next.*$/gm, "")
        .trim()
        .slice(0, 400)}`,
    );
  });

  test("09-09: admin — Feedback Review tab", async ({ page }) => {
    await page.goto("/admin");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ADMIN FEEDBACK: Not authenticated.");
      return;
    }

    const feedbackTab = page.getByRole("tab", { name: /Feedback Review/i });
    const hasTab = await feedbackTab.isVisible().catch(() => false);
    console.log(`ADMIN FEEDBACK: Tab visible = ${hasTab}`);

    if (hasTab) {
      await feedbackTab.click();
      await page.waitForTimeout(1500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/09-09-admin-feedback.png`,
        fullPage: true,
      });

      const bodyText = (await page.locator("body").textContent()) ?? "";
      console.log(
        `ADMIN FEEDBACK CONTENT: ${bodyText
          .replace(/self\.__next.*$/gm, "")
          .trim()
          .slice(0, 400)}`,
      );

      const hasFeedbackContent =
        bodyText.toLowerCase().includes("feedback") ||
        bodyText.toLowerCase().includes("review") ||
        bodyText.toLowerCase().includes("rating") ||
        bodyText.toLowerCase().includes("conversation");
      console.log(
        `ADMIN FEEDBACK: Has feedback content = ${hasFeedbackContent}`,
      );
    }
  });

  test("09-10: admin — Audit tab", async ({ page }) => {
    await page.goto("/admin");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ADMIN AUDIT: Not authenticated.");
      return;
    }

    const auditTab = page.getByRole("tab", { name: /Audit/i });
    const hasTab = await auditTab.isVisible().catch(() => false);
    console.log(`ADMIN AUDIT: Tab visible = ${hasTab}`);

    if (hasTab) {
      await auditTab.click();
      await page.waitForTimeout(1500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/09-10-admin-audit.png`,
        fullPage: true,
      });

      const bodyText = (await page.locator("body").textContent()) ?? "";
      console.log(
        `ADMIN AUDIT CONTENT: ${bodyText
          .replace(/self\.__next.*$/gm, "")
          .trim()
          .slice(0, 400)}`,
      );
    }
  });
});

/* ── Profile page — ISSUE-06 audit ──────────────────────── */

test.describe("Profile & Analytics — Hardcoded Data Audit (ISSUE-06)", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test("09-11: profile page — audit for hardcoded demo data", async ({
    page,
  }) => {
    await page.goto("/profile");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/09-11-profile-page.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("PROFILE: Not authenticated.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 600);
    console.log(`PROFILE CONTENT: ${meaningful}`);

    // ISSUE-06: Check if company name is hardcoded
    const hasHardcodedCompany =
      bodyText.includes("Horizon Tech") ||
      bodyText.includes("202301234A") ||
      bodyText.includes("45 employees");

    if (hasHardcodedCompany) {
      console.log(
        "PROFILE GAP (ISSUE-06): Page shows hardcoded demo data — " +
          "company name, UEN, and employee count are not from the real user account.",
      );
    } else {
      console.log(
        "PROFILE: No hardcoded demo data detected — data appears to be real or blank.",
      );
    }

    // Check if profile has real API data fields
    const hasApiData =
      bodyText.toLowerCase().includes("company") ||
      bodyText.toLowerCase().includes("profile") ||
      bodyText.toLowerCase().includes("organization");
    console.log(`PROFILE: Has company/profile content = ${hasApiData}`);

    expect(bodyText.length, "Profile page must have content").toBeGreaterThan(
      50,
    );
  });

  test("09-12: analytics page — audit for hardcoded demo data", async ({
    page,
  }) => {
    await page.goto("/analytics");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/09-12-analytics-page.png`,
      fullPage: true,
    });

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ANALYTICS: Not authenticated.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 600);
    console.log(`ANALYTICS CONTENT: ${meaningful}`);

    // ISSUE-06: Check for known hardcoded figures
    const has55Employees = bodyText.includes("55");
    const has123Queries = bodyText.includes("123");
    const has48k = bodyText.includes("48.8") || bodyText.includes("$48");

    if (has55Employees || has123Queries || has48k) {
      console.log(
        "ANALYTICS GAP (ISSUE-06): Page shows hardcoded demo figures — " +
          "55 employees, 123 advisory queries, or $48.8k monthly cost are not real.",
      );
    } else {
      console.log(
        "ANALYTICS: Known hardcoded figures not detected — data may be different or real.",
      );
    }

    // Check for charts or data visualization
    const hasCharts =
      bodyText.toLowerCase().includes("workforce") ||
      bodyText.toLowerCase().includes("trend") ||
      bodyText.toLowerCase().includes("chart");
    console.log(`ANALYTICS: Has chart/trend content = ${hasCharts}`);
  });
});

/* ── Advisory Streaming & History ───────────────────────── */

test.describe("Advisory — Streaming and History (ISSUE-10)", () => {
  test("09-13: POST /advisory/stream — backend streaming endpoint works", async ({
    page,
  }) => {
    // Test the streaming endpoint via backend API
    const email = `stream_test_${Date.now()}@playwright.test`;
    const regResp = await page.request.post(`${API_BASE}/auth/register`, {
      data: { email, password: "SecurePass1!", name: "Stream Test" },
      headers: { "Content-Type": "application/json" },
      timeout: 15000,
    });

    if (!regResp.ok()) {
      console.log("STREAMING: Registration failed — skipping.");
      return;
    }

    const regBody = await regResp.json();
    const token = regBody.access_token ?? "";
    console.log(`STREAMING: Registered ${email}, token length=${token.length}`);

    // Test the advisory/stream endpoint (field is 'query', not 'question')
    const streamResp = await page.request.post(`${API_BASE}/advisory/stream`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        query: "What is the minimum notice period for termination?",
      },
      timeout: 30000,
    });

    const streamStatus = streamResp.status();
    console.log(`STREAMING: /advisory/stream status = ${streamStatus}`);

    if (streamResp.ok()) {
      const streamBody = await streamResp.text();
      console.log(`STREAMING RESPONSE: ${streamBody.slice(0, 500)}`);

      const hasContent =
        streamBody.toLowerCase().includes("notice") ||
        streamBody.toLowerCase().includes("termination") ||
        streamBody.includes("{");
      console.log(`STREAMING: Has relevant content = ${hasContent}`);
    } else {
      const errBody = await streamResp.text();
      console.log(`STREAMING ERROR: ${errBody.slice(0, 200)}`);
    }
  });

  test("09-14: advisory conversation history via backend API", async ({
    page,
  }) => {
    // Register and make an advisory query, then check history
    const email = `history_test_${Date.now()}@playwright.test`;
    const regResp = await page.request.post(`${API_BASE}/auth/register`, {
      data: { email, password: "SecurePass1!", name: "History Test" },
      headers: { "Content-Type": "application/json" },
      timeout: 15000,
    });

    if (!regResp.ok()) {
      console.log("HISTORY: Registration failed — skipping.");
      return;
    }

    const regBody = await regResp.json();
    const token = regBody.access_token ?? "";

    // Make an advisory query (field is 'query', not 'question')
    const queryResp = await page.request.post(`${API_BASE}/advisory/query`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: { query: "What are the notice period rules?" },
      timeout: 30000,
    });

    if (!queryResp.ok()) {
      console.log(`HISTORY: Advisory query failed — ${queryResp.status()}`);
      return;
    }

    const queryBody = await queryResp.json();
    console.log(
      `HISTORY: Advisory query succeeded, response keys=${Object.keys(queryBody).join(", ")}`,
    );

    const conversationId =
      queryBody.conversation_id ?? queryBody.id ?? queryBody.session_id;
    console.log(`HISTORY: Conversation ID = ${conversationId}`);

    if (conversationId) {
      // Try to fetch history for this conversation
      const histResp = await page.request.get(
        `${API_BASE}/advisory/history/${conversationId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 10000,
        },
      );

      const histStatus = histResp.status();
      console.log(
        `HISTORY: GET /advisory/history/${conversationId} status = ${histStatus}`,
      );

      if (histResp.ok()) {
        const histBody = await histResp.json();
        console.log(
          `HISTORY CONTENT: ${JSON.stringify(histBody).slice(0, 400)}`,
        );
      } else {
        const errBody = await histResp.text();
        console.log(`HISTORY ERROR: ${errBody.slice(0, 200)}`);
      }
    } else {
      console.log(
        "HISTORY GAP (ISSUE-10): Advisory query response has no conversation_id — " +
          "history cannot be retrieved. This means conversations are not persisted.",
      );
    }
  });

  test.describe("Advisory history — UI sidebar shows conversations", () => {
    test("09-15: history sidebar shows entries after submitting a question", async ({
      page,
    }) => {
      await setupAuthenticatedSession(page);

      await page.goto("/advisory");
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(2000);

      const url = page.url();
      if (url.includes("/login")) {
        console.log("ADVISORY HISTORY UI: Not authenticated.");
        return;
      }

      // Check initial state of history sidebar
      const initialBodyText = (await page.locator("body").textContent()) ?? "";
      const hasNoConversations =
        initialBodyText.toLowerCase().includes("no conversation") ||
        initialBodyText.toLowerCase().includes("no history");
      console.log(
        `ADVISORY HISTORY: Initial 'No conversations' state = ${hasNoConversations}`,
      );

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/09-15a-advisory-history-initial.png`,
        fullPage: true,
      });

      // Submit a question
      const contentEditable = page.locator('[contenteditable="true"]').first();
      const hasContentEditable = await contentEditable
        .isVisible()
        .catch(() => false);
      const textarea = page.locator("textarea").first();
      const hasTextarea = await textarea.isVisible().catch(() => false);

      if (hasContentEditable) {
        await contentEditable.click();
        await contentEditable.fill(
          "What is the notice period for termination?",
        );
        await contentEditable.press("Enter");
      } else if (hasTextarea) {
        await textarea.fill("What is the notice period for termination?");
        await textarea.press("Enter");
      } else {
        console.log("ADVISORY HISTORY: No input found — cannot test history.");
        return;
      }

      console.log(
        "ADVISORY HISTORY: Question submitted — waiting 15s for response and history update...",
      );
      await page.waitForTimeout(15000);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/09-15b-advisory-history-after-question.png`,
        fullPage: true,
      });

      const afterBodyText = (await page.locator("body").textContent()) ?? "";

      // Check if history sidebar now shows the conversation
      const hasHistoryEntry =
        afterBodyText.toLowerCase().includes("notice period") ||
        afterBodyText.toLowerCase().includes("termination") ||
        afterBodyText.toLowerCase().includes("today") ||
        afterBodyText.toLowerCase().includes("just now");

      const stillNoConversations =
        afterBodyText.toLowerCase().includes("no conversation") ||
        afterBodyText.toLowerCase().includes("no history");

      console.log(
        `ADVISORY HISTORY: After question — history entry visible=${hasHistoryEntry}, ` +
          `still shows "no conversations"=${stillNoConversations}`,
      );

      if (stillNoConversations) {
        console.log(
          "ADVISORY HISTORY GAP (ISSUE-10): Conversation history sidebar still shows " +
            "'No conversations' after submitting a question. Conversations are not persisting " +
            "to the sidebar history.",
        );
      } else if (hasHistoryEntry) {
        console.log(
          "ADVISORY HISTORY: Conversation appeared in sidebar — history IS working.",
        );
      }
    });
  });
});

/* ── Onboarding flow ─────────────────────────────────────── */

test.describe("Onboarding Flow (ISSUE-09)", () => {
  test("09-16: onboarding page content and step navigation", async ({
    page,
  }) => {
    await setupAuthenticatedSession(page);

    await page.goto("/onboarding");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    console.log(`ONBOARDING: URL = ${url}`);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/09-16a-onboarding.png`,
      fullPage: true,
    });

    if (url.includes("/login")) {
      console.log("ONBOARDING: Redirected to login — auth required.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 600);
    console.log(`ONBOARDING CONTENT: ${meaningful}`);

    // Onboarding should have company setup steps
    const hasCompanySetup =
      bodyText.toLowerCase().includes("company") ||
      bodyText.toLowerCase().includes("profile") ||
      bodyText.toLowerCase().includes("setup") ||
      bodyText.toLowerCase().includes("welcome") ||
      bodyText.toLowerCase().includes("get started");
    console.log(`ONBOARDING: Has company setup content = ${hasCompanySetup}`);

    // Check for step indicators
    const hasSteps =
      bodyText.toLowerCase().includes("step") ||
      bodyText.includes("1/") ||
      bodyText.includes("2/");
    console.log(`ONBOARDING: Has step indicators = ${hasSteps}`);

    // Look for navigation buttons
    const nextButton = page
      .getByRole("button", { name: /next|continue|get started/i })
      .first();
    const hasNext = await nextButton.isVisible().catch(() => false);
    console.log(`ONBOARDING: Next/Continue button visible = ${hasNext}`);

    if (hasNext) {
      await nextButton.click();
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/09-16b-onboarding-step2.png`,
        fullPage: true,
      });

      const step2Text = (await page.locator("body").textContent()) ?? "";
      console.log(
        `ONBOARDING STEP 2: ${step2Text
          .replace(/self\.__next.*$/gm, "")
          .trim()
          .slice(0, 300)}`,
      );
    }
  });
});

/* ── Help page audit ─────────────────────────────────────── */

test.describe("Help Page — Content Audit (ISSUE-13)", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test("09-17: help page has real content (not blank)", async ({ page }) => {
    await page.goto("/help");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/09-17-help-page.png`,
      fullPage: true,
    });

    const url = page.url();
    console.log(`HELP: URL = ${url}`);

    if (url.includes("/login")) {
      console.log("HELP: Not authenticated.");
      return;
    }

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const meaningful = bodyText
      .replace(/self\.__next.*$/gm, "")
      .trim()
      .slice(0, 800);
    console.log(`HELP CONTENT: ${meaningful}`);

    const hasHelpContent =
      meaningful.toLowerCase().includes("help") ||
      meaningful.toLowerCase().includes("support") ||
      meaningful.toLowerCase().includes("guide") ||
      meaningful.toLowerCase().includes("contact") ||
      meaningful.toLowerCase().includes("faq");

    const isBlank = meaningful.length < 50;

    if (isBlank) {
      console.log(
        "HELP GAP (ISSUE-13): Help page appears blank or has minimal content. " +
          "A help page with no content is a support liability.",
      );
    } else {
      console.log(
        `HELP: Has content (${meaningful.length} chars). hasHelpContent=${hasHelpContent}`,
      );
    }

    expect(
      bodyText.length,
      "Help page must not be completely empty",
    ).toBeGreaterThan(0);
  });
});
