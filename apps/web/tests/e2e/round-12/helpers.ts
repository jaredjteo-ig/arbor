/**
 * Round-12 E2E Test Helpers
 *
 * Centralises auth, API calls, and session setup for all round-12 tests.
 * The live backend is at http://localhost:8000.
 * The live frontend is at http://localhost:3000.
 *
 * Token caching: the backend rate-limits /auth/login to 5 req/min per IP.
 * We pre-fetch a single token via node-fetch at module init time and reuse
 * it for all tests in the run. The token has a 60-minute TTL which covers
 * the full test suite.
 */

import * as fs from "fs";
import * as path from "path";
import { type Page, type APIRequestContext } from "@playwright/test";

export const API_BASE = "http://localhost:8000";
export const FRONTEND_BASE = "http://localhost:3000";

export const DEMO_EMAIL = "demo@central.kailash.ai";
export const DEMO_PASSWORD = "CentralDemo2026!";

const TOKEN_FILE = path.join(__dirname, ".auth-token.json");

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  userId: number;
  companyId: number;
}

/**
 * Read the access token written by global-setup.ts.
 * Falls back to a fresh login if the file is missing (e.g. running a single
 * file in isolation without the full suite global setup).
 */
export function readCachedToken(): string {
  try {
    const raw = fs.readFileSync(TOKEN_FILE, "utf-8");
    const data = JSON.parse(raw) as { accessToken: string };
    return data.accessToken;
  } catch {
    throw new Error(
      `[helpers] .auth-token.json not found. Run the full round-12 suite so global-setup fires first, or create it manually.`,
    );
  }
}

/**
 * Read the full auth session from the cached token file.
 */
export function readCachedSession(): AuthSession {
  try {
    const raw = fs.readFileSync(TOKEN_FILE, "utf-8");
    return JSON.parse(raw) as AuthSession;
  } catch {
    throw new Error(`[helpers] .auth-token.json not found.`);
  }
}

/**
 * Login via the REST API and return tokens.
 */
export async function loginViaApi(
  request: APIRequestContext,
  email = DEMO_EMAIL,
  password = DEMO_PASSWORD,
): Promise<AuthSession> {
  const resp = await request.post(`${API_BASE}/auth/login`, {
    data: { email, password },
    headers: { "Content-Type": "application/json" },
  });

  if (!resp.ok()) {
    throw new Error(
      `Login failed: HTTP ${resp.status()} — ${await resp.text()}`,
    );
  }

  const body = await resp.json();
  return {
    accessToken: body.access_token,
    refreshToken: body.refresh_token,
    userId: body.user?.id ?? 0,
    companyId: body.user?.company_id ?? 0,
  };
}

/**
 * Inject auth tokens into the page's localStorage and reload.
 * After this call, the frontend AuthContext will pick up the tokens.
 */
export async function injectAuthSession(
  page: Page,
  session: AuthSession,
): Promise<void> {
  await page.goto(`${FRONTEND_BASE}/login`);
  await page.waitForLoadState("domcontentloaded");

  await page.evaluate(
    ({ at, rt }) => {
      localStorage.setItem("access_token", at);
      localStorage.setItem("refresh_token", rt);
    },
    { at: session.accessToken, rt: session.refreshToken },
  );

  await page.reload();
  await page.waitForLoadState("networkidle");
}

/**
 * Full setup: login via API + inject tokens into page session.
 */
export async function setupAuthenticatedPage(page: Page): Promise<AuthSession> {
  const session = await loginViaApi(page.request);
  await injectAuthSession(page, session);
  return session;
}

/**
 * Navigate to a dashboard route and wait for it to settle.
 */
export async function navigateToDashboard(
  page: Page,
  path: string,
): Promise<void> {
  await page.goto(`${FRONTEND_BASE}${path}`);
  await page.waitForLoadState("networkidle");
}

/**
 * Take a screenshot with a given filename in the round-12 screenshots folder.
 */
export async function screenshot(page: Page, name: string): Promise<void> {
  await page.screenshot({
    path: `tests/e2e/round-12/screenshots/${name}.png`,
    fullPage: true,
  });
}
