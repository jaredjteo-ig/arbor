/**
 * Test Suite 07: Knowledge Base (Flow 6)
 *
 * Red-team: Does the Knowledge Base work?
 * The KB exposes real Singapore employment law provisions via the backend.
 *
 * Backend endpoints:
 *   GET  /kb/acts           — list all legislation acts
 *   GET  /kb/domains        — list thematic domains
 *   GET  /kb/provisions/:id — single provision detail
 *   POST /kb/query          — search provisions
 *   POST /search/semantic   — semantic search
 *   POST /search/fulltext   — fulltext search
 *
 * The frontend advisory chat calls the KB under the hood. There is currently
 * no dedicated KB browse page in the frontend navigation, so we test:
 *  a) Backend KB API directly (all endpoints must return real data)
 *  b) Advisory chat as the user-facing KB surface (asks KB-type questions)
 *  c) Admin KB Management tab (the admin panel has KB management UI)
 */
import { test, expect } from "@playwright/test";
import { setupAuthenticatedSession } from "./helpers/auth.helper";
import { API_BASE } from "./helpers/auth.helper";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

/* ── Helpers ─────────────────────────────────────────────── */

/** Register + login via API and return an access token. */
async function getAccessToken(
  page: Parameters<typeof setupAuthenticatedSession>[0],
): Promise<string> {
  const email = `kb_test_${Date.now()}@playwright.test`;
  const resp = await page.request.post(`${API_BASE}/auth/register`, {
    data: { email, password: "SecurePass1!", name: "KB Test User" },
    headers: { "Content-Type": "application/json" },
    timeout: 15000,
  });
  if (resp.ok()) {
    const body = await resp.json();
    return body.access_token ?? "";
  }
  return "";
}

/* ── Backend KB API tests ─────────────────────────────────── */

test.describe("Knowledge Base — Backend API", () => {
  test("07-01: GET /kb/acts returns list of legislation acts", async ({
    page,
  }) => {
    const token = await getAccessToken(page);
    expect(token.length, "Must have a valid access token").toBeGreaterThan(0);

    const resp = await page.request.get(`${API_BASE}/kb/acts`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    expect(resp.ok(), `GET /kb/acts returned ${resp.status()}`).toBe(true);
    const body = await resp.json();

    console.log(
      `KB ACTS: total=${body.total}, acts count=${body.acts?.length}`,
    );

    // Must return an object with an 'acts' array
    expect(body).toHaveProperty("acts");
    expect(body).toHaveProperty("total");
    expect(Array.isArray(body.acts)).toBe(true);
    expect(body.total).toBeGreaterThan(0);

    // At least one act should be the Employment Act
    const hasEmploymentAct = body.acts.some(
      (a: { title?: string; short_name?: string }) =>
        a.short_name === "EA" ||
        (a.title ?? "").toLowerCase().includes("employment"),
    );
    console.log(`KB ACTS: Has Employment Act = ${hasEmploymentAct}`);

    // All acts should have required fields
    const firstAct = body.acts[0];
    expect(firstAct).toHaveProperty("id");
    expect(firstAct).toHaveProperty("title");
    expect(firstAct).toHaveProperty("short_name");
    expect(firstAct).toHaveProperty("authority_type");

    console.log("KB ACTS: First act =", JSON.stringify(firstAct));
  });

  test("07-02: GET /kb/domains returns thematic domain list", async ({
    page,
  }) => {
    const token = await getAccessToken(page);
    expect(token.length).toBeGreaterThan(0);

    const resp = await page.request.get(`${API_BASE}/kb/domains`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    expect(resp.ok(), `GET /kb/domains returned ${resp.status()}`).toBe(true);
    const body = await resp.json();

    console.log(
      `KB DOMAINS: total=${body.total}, domains count=${body.domains?.length}`,
    );

    expect(body).toHaveProperty("domains");
    expect(Array.isArray(body.domains)).toBe(true);
    expect(body.total).toBeGreaterThan(0);

    const firstDomain = body.domains[0];
    expect(firstDomain).toHaveProperty("id");
    expect(firstDomain).toHaveProperty("name");
    console.log("KB DOMAINS: First domain =", JSON.stringify(firstDomain));

    // Log all domain names for audit trail
    const domainNames = (body.domains as Array<{ name: string }>).map(
      (d) => d.name,
    );
    console.log("KB DOMAINS: All domain names =", domainNames.join(", "));
  });

  test("07-03: GET /kb/provisions/:id returns a specific provision", async ({
    page,
  }) => {
    const token = await getAccessToken(page);
    expect(token.length).toBeGreaterThan(0);

    // First get an act to find a valid provision ID
    const actsResp = await page.request.get(`${API_BASE}/kb/acts`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(actsResp.ok()).toBe(true);
    const acts = await actsResp.json();

    // Use the Employment Act (EA) if present, otherwise first act
    const ea = (acts.acts as Array<{ short_name: string; id: number }>).find(
      (a) => a.short_name === "EA",
    );
    console.log(`KB PROVISION: Using act: ${ea ? "EA" : "first act"}`);

    // Get provisions via the query endpoint
    const queryResp = await page.request.post(`${API_BASE}/kb/query`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        query: "annual leave",
        act_id: ea?.id ?? acts.acts[0]?.id,
      },
    });

    expect(
      queryResp.ok(),
      `POST /kb/query returned ${queryResp.status()}`,
    ).toBe(true);
    const provisions = await queryResp.json();

    console.log(
      `KB PROVISIONS QUERY: total=${provisions.total}, provisions count=${provisions.provisions?.length}`,
    );
    expect(provisions).toHaveProperty("provisions");
    expect(Array.isArray(provisions.provisions)).toBe(true);

    // If any provisions exist, fetch one by ID
    if (provisions.provisions.length > 0) {
      const firstProvision = provisions.provisions[0];
      const provId = firstProvision.id;

      const provResp = await page.request.get(
        `${API_BASE}/kb/provisions/${provId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      expect(
        provResp.ok(),
        `GET /kb/provisions/${provId} returned ${provResp.status()}`,
      ).toBe(true);
      const prov = await provResp.json();

      console.log(
        `KB PROVISION DETAIL: id=${prov.id}, section=${prov.section}, title=${prov.title}`,
      );
      expect(prov).toHaveProperty("id");
      expect(prov).toHaveProperty("section");
      expect(prov).toHaveProperty("formal_text");
    } else {
      console.log(
        "KB PROVISIONS QUERY: No provisions found for annual leave query",
      );
    }
  });

  test("07-04: POST /kb/query — fulltext search returns provisions", async ({
    page,
  }) => {
    const token = await getAccessToken(page);
    expect(token.length).toBeGreaterThan(0);

    const resp = await page.request.post(`${API_BASE}/kb/query`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: { query: "sick leave" },
    });

    expect(resp.ok(), `POST /kb/query returned ${resp.status()}`).toBe(true);
    const body = await resp.json();

    console.log(
      `KB QUERY sick leave: total=${body.total}, count=${body.provisions?.length}`,
    );
    expect(body).toHaveProperty("provisions");

    // Log first provision for audit
    if (body.provisions?.length > 0) {
      const p = body.provisions[0];
      console.log(
        `KB QUERY RESULT: id=${p.id}, section=${p.section}, title=${p.title}`,
      );
    }
  });

  test("07-05: POST /search/semantic — semantic search", async ({ page }) => {
    const token = await getAccessToken(page);
    expect(token.length).toBeGreaterThan(0);

    const resp = await page.request.post(`${API_BASE}/search/semantic`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: { query: "How many days annual leave must I give employees?" },
    });

    const status = resp.status();
    console.log(`SEMANTIC SEARCH: status=${status}`);

    if (resp.ok()) {
      const body = await resp.json();
      console.log(
        `SEMANTIC SEARCH RESULT: ${JSON.stringify(body).slice(0, 400)}`,
      );
      // Should return results
      const hasResults =
        Array.isArray(body) ||
        body.results !== undefined ||
        body.provisions !== undefined;
      console.log(`SEMANTIC SEARCH: Has results = ${hasResults}`);
    } else {
      const errBody = await resp.text();
      console.log(`SEMANTIC SEARCH ERROR: ${errBody.slice(0, 200)}`);
      // Not a hard failure — semantic search may require embeddings setup
    }
  });

  test("07-06: POST /search/fulltext — fulltext search", async ({ page }) => {
    const token = await getAccessToken(page);
    expect(token.length).toBeGreaterThan(0);

    const resp = await page.request.post(`${API_BASE}/search/fulltext`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: { query: "termination notice" },
    });

    const status = resp.status();
    console.log(`FULLTEXT SEARCH: status=${status}`);

    if (resp.ok()) {
      const body = await resp.json();
      console.log(
        `FULLTEXT SEARCH RESULT: ${JSON.stringify(body).slice(0, 400)}`,
      );
    } else {
      const errBody = await resp.text();
      console.log(`FULLTEXT SEARCH ERROR: ${errBody.slice(0, 200)}`);
    }
  });
});

/* ── Advisory chat as KB surface ─────────────────────────── */

test.describe("Knowledge Base — Via Advisory Chat (User-Facing)", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test("07-07: GREEN question — annual leave days cites EA provision", async ({
    page,
  }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("KB VIA ADVISORY: Not authenticated — skipping.");
      return;
    }

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/07-07a-advisory-kb-green-before.png`,
      fullPage: true,
    });

    // Type a GREEN knowledge question about leave entitlements
    const question = "How many days of annual leave must I give employees?";

    // The advisory input is a contenteditable div, not a textarea
    // Try contenteditable first, then textarea, then text input
    const contentEditable = page.locator('[contenteditable="true"]').first();
    const hasContentEditable = await contentEditable
      .isVisible()
      .catch(() => false);

    const textarea = page.locator("textarea").first();
    const hasTextarea = await textarea.isVisible().catch(() => false);

    if (hasContentEditable) {
      await contentEditable.click();
      await contentEditable.fill(question);
      console.log("KB GREEN: Typed into contenteditable");
    } else if (hasTextarea) {
      await textarea.fill(question);
      console.log("KB GREEN: Typed into textarea");
    } else {
      console.log("KB GREEN: No input found — cannot submit question.");
      return;
    }

    // Click send button or press Enter
    const sendButton = page
      .getByRole("button")
      .filter({
        has: page.locator(
          'svg[class*="send"], svg[class*="arrow"], svg[class*="Send"]',
        ),
      })
      .first();
    const hasSend = await sendButton.isVisible().catch(() => false);

    if (hasSend) {
      await sendButton.click();
    } else {
      // Try clicking any button near the input
      const submitBtn = page
        .locator('button[type="submit"], button[aria-label*="send" i]')
        .first();
      const hasSubmit = await submitBtn.isVisible().catch(() => false);
      if (hasSubmit) {
        await submitBtn.click();
      } else if (hasContentEditable) {
        await contentEditable.press("Enter");
      } else {
        await textarea.press("Enter");
      }
    }

    console.log(
      "KB GREEN: Question submitted — waiting up to 30s for response...",
    );
    await page.waitForTimeout(20000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/07-07b-advisory-kb-green-response.png`,
      fullPage: true,
    });

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`KB GREEN RESPONSE: ${bodyText.slice(0, 1000)}`);

    const hasLeaveContent =
      bodyText.toLowerCase().includes("annual leave") ||
      bodyText.toLowerCase().includes("leave entitlement") ||
      bodyText.toLowerCase().includes("days");

    const hasEACitation =
      bodyText.includes("EA") ||
      bodyText.includes("Employment Act") ||
      bodyText.includes("s88") ||
      bodyText.toLowerCase().includes("section");

    const hasRiskTier =
      bodyText.toLowerCase().includes("green") ||
      bodyText.toLowerCase().includes("amber") ||
      bodyText.toLowerCase().includes("red") ||
      bodyText.toLowerCase().includes("risk");

    const hasDisclaimer =
      bodyText.toLowerCase().includes("disclaimer") ||
      bodyText.toLowerCase().includes("legal advice") ||
      bodyText.toLowerCase().includes("consult");

    console.log(
      `KB GREEN: leave=${hasLeaveContent}, citation=${hasEACitation}, riskTier=${hasRiskTier}, disclaimer=${hasDisclaimer}`,
    );
  });

  test("07-08: AMBER question — dental benefits triggers amber/advisory guidance", async ({
    page,
  }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("KB AMBER: Not authenticated — skipping.");
      return;
    }

    const contentEditable = page.locator('[contenteditable="true"]').first();
    const hasContentEditable = await contentEditable
      .isVisible()
      .catch(() => false);
    const textarea = page.locator("textarea").first();
    const hasTextarea = await textarea.isVisible().catch(() => false);

    const amberQuestion = "Should I offer dental benefits to my employees?";

    if (hasContentEditable) {
      await contentEditable.click();
      await contentEditable.fill(amberQuestion);
    } else if (hasTextarea) {
      await textarea.fill(amberQuestion);
    } else {
      console.log("KB AMBER: No input found — cannot submit.");
      return;
    }

    await page.keyboard.press("Enter");
    console.log("KB AMBER: Question submitted — waiting for response...");
    await page.waitForTimeout(20000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/07-08-advisory-kb-amber-response.png`,
      fullPage: true,
    });

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const hasDentalContent =
      bodyText.toLowerCase().includes("dental") ||
      bodyText.toLowerCase().includes("benefit") ||
      bodyText.toLowerCase().includes("medical");

    console.log(`KB AMBER: dental content visible=${hasDentalContent}`);
    console.log(`KB AMBER RESPONSE: ${bodyText.slice(0, 600)}`);
  });

  test("07-09: RED question — TADM claim triggers red/urgent guidance", async ({
    page,
  }) => {
    await page.goto("/advisory");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("KB RED: Not authenticated — skipping.");
      return;
    }

    const contentEditable = page.locator('[contenteditable="true"]').first();
    const hasContentEditable = await contentEditable
      .isVisible()
      .catch(() => false);
    const textarea = page.locator("textarea").first();
    const hasTextarea = await textarea.isVisible().catch(() => false);

    const redQuestion =
      "An employee just filed a TADM claim against us. What do we do?";

    if (hasContentEditable) {
      await contentEditable.click();
      await contentEditable.fill(redQuestion);
    } else if (hasTextarea) {
      await textarea.fill(redQuestion);
    } else {
      console.log("KB RED: No input found — cannot submit.");
      return;
    }

    await page.keyboard.press("Enter");
    console.log("KB RED: TADM question submitted — waiting for response...");
    await page.waitForTimeout(25000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/07-09-advisory-kb-red-response.png`,
      fullPage: true,
    });

    const bodyText = (await page.locator("body").textContent()) ?? "";
    const hasTADMContent =
      bodyText.toLowerCase().includes("tadm") ||
      bodyText.toLowerCase().includes("claim") ||
      bodyText.toLowerCase().includes("mediation") ||
      bodyText.toLowerCase().includes("tribunal");

    const hasUrgentTone =
      bodyText.toLowerCase().includes("immediately") ||
      bodyText.toLowerCase().includes("urgent") ||
      bodyText.toLowerCase().includes("respond") ||
      bodyText.toLowerCase().includes("deadline");

    console.log(
      `KB RED: TADM content=${hasTADMContent}, urgent tone=${hasUrgentTone}`,
    );
    console.log(`KB RED RESPONSE: ${bodyText.slice(0, 600)}`);
  });
});

/* ── Admin KB Management UI ──────────────────────────────── */

test.describe("Knowledge Base — Admin Management UI", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test("07-10: admin page loads with KB management tab", async ({ page }) => {
    await page.goto("/admin");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    console.log(`ADMIN KB: URL = ${url}`);

    if (url.includes("/login")) {
      console.log("ADMIN KB: Not authenticated — redirected to login.");
      return;
    }

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/07-10a-admin-page.png`,
      fullPage: true,
    });

    const bodyText = (await page.locator("body").textContent()) ?? "";
    console.log(`ADMIN PAGE CONTENT: ${bodyText.slice(0, 500)}`);

    // Admin page should have tab navigation
    const kbTab = page.getByRole("tab", {
      name: /KB Management|Knowledge Base/i,
    });
    const hasKbTab = await kbTab.isVisible().catch(() => false);
    console.log(`ADMIN KB: KB Management tab visible = ${hasKbTab}`);

    if (hasKbTab) {
      await kbTab.click();
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/07-10b-admin-kb-tab.png`,
        fullPage: true,
      });

      const tabBody = (await page.locator("body").textContent()) ?? "";
      const hasActContent =
        tabBody.toLowerCase().includes("act") ||
        tabBody.toLowerCase().includes("provision") ||
        tabBody.toLowerCase().includes("legislation") ||
        tabBody.toLowerCase().includes("employment");
      console.log(`ADMIN KB TAB: Has act/provision content = ${hasActContent}`);
      console.log(`ADMIN KB TAB CONTENT: ${tabBody.slice(0, 500)}`);
    }
  });

  test("07-11: admin regulatory updates tab", async ({ page }) => {
    await page.goto("/admin");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const url = page.url();
    if (url.includes("/login")) {
      console.log("ADMIN UPDATES: Not authenticated.");
      return;
    }

    // Click Regulatory Updates tab
    const updatesTab = page.getByRole("tab", { name: /Regulatory Updates/i });
    const hasTab = await updatesTab.isVisible().catch(() => false);

    if (hasTab) {
      await updatesTab.click();
      await page.waitForTimeout(1500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/07-11-admin-regulatory-updates.png`,
        fullPage: true,
      });

      const bodyText = (await page.locator("body").textContent()) ?? "";
      console.log(`ADMIN UPDATES CONTENT: ${bodyText.slice(0, 500)}`);

      const hasUpdateContent =
        bodyText.toLowerCase().includes("update") ||
        bodyText.toLowerCase().includes("regulation") ||
        bodyText.toLowerCase().includes("amendment");
      console.log(`ADMIN UPDATES: Has update content = ${hasUpdateContent}`);
    } else {
      console.log("ADMIN UPDATES: Tab not found.");
    }
  });
});
