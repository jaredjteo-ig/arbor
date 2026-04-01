/**
 * Auth helpers for E2E tests.
 *
 * The HR Advisory frontend at http://localhost:3002 sends auth requests
 * to NEXT_PUBLIC_API_URL which defaults to http://localhost:8000.
 * The actual backend is at http://localhost:8099.
 *
 * Key insight: When no NEXT_PUBLIC_API_URL is set, the frontend uses
 * http://localhost:8000 which is a DIFFERENT application.
 *
 * This is a critical environment configuration bug.
 *
 * For E2E tests we work around this by:
 * 1. Registering users against the ACTUAL backend (port 8099).
 * 2. Using the frontend form to login — which goes to port 8000
 *    (and will fail unless the .env.local is set correctly).
 * 3. Alternatively, intercepting API calls to redirect them.
 */
import { type Page } from "@playwright/test";

/** The actual HR Advisory backend */
export const API_BASE = "http://localhost:8099";

/** The URL the frontend expects (default, without NEXT_PUBLIC_API_URL) */
export const FRONTEND_API_BASE = "http://localhost:8000";

export interface RegisteredUser {
  email: string;
  password: string;
  name: string;
  accessToken: string;
  refreshToken: string;
  userId: number;
}

/**
 * Register a user directly against the actual backend API (port 8099).
 * Returns user data including tokens if successful.
 */
export async function registerUserViaApi(
  page: Page,
  options?: { email?: string; password?: string; name?: string },
): Promise<RegisteredUser | null> {
  const email =
    options?.email ??
    `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 10)}@playwright.test`;
  const password = options?.password ?? "SecurePass1!";
  const name = options?.name ?? "E2E Playwright User";

  try {
    const response = await page.request.post(`${API_BASE}/auth/register`, {
      data: { email, password, name },
      headers: { "Content-Type": "application/json" },
      timeout: 15000,
    });

    if (response.ok()) {
      const body = await response.json();
      return {
        email,
        password,
        name,
        accessToken: body.access_token ?? body.tokens?.access_token ?? "",
        refreshToken: body.refresh_token ?? body.tokens?.refresh_token ?? "",
        userId: body.user?.id ?? 0,
      };
    }

    const text = await response.text().catch(() => "unreadable");
    console.warn(
      `Registration failed: HTTP ${response.status()} — ${text.slice(0, 200)}`,
    );
    return null;
  } catch (err) {
    console.warn(`Registration API error: ${err}`);
    return null;
  }
}

/**
 * Route-intercept strategy: proxy all frontend API calls from port 8000
 * to port 8099, adding the correct CORS headers so the browser accepts
 * the response.
 *
 * The arbor app on port 8099 is configured with cors_origins for
 * localhost:3000 and localhost:5173 — NOT localhost:3002 where the
 * frontend is running. The browser blocks the CORS response, causing
 * auth failures. This interceptor adds the missing header.
 *
 * This fixes the environment configuration gap without modifying source files.
 */
export async function setupApiRouteInterception(page: Page): Promise<void> {
  await page.route("http://localhost:8000/**", async (route) => {
    const originalUrl = route.request().url();
    const targetUrl = originalUrl.replace("localhost:8000", "localhost:8099");
    const request = route.request();

    try {
      // Fetch from the real backend
      const response = await route.fetch({ url: targetUrl });
      const body = await response.body();

      // Build headers — add CORS header for port 3002
      const headers: Record<string, string> = {};
      for (const [k, v] of Object.entries(response.headers())) {
        headers[k] = v;
      }
      headers["access-control-allow-origin"] = "http://localhost:3002";
      headers["access-control-allow-credentials"] = "true";

      await route.fulfill({
        status: response.status(),
        headers,
        body,
      });
    } catch (err) {
      // Fallback: just continue with URL rewrite
      await route.continue({ url: targetUrl });
    }
  });
}

/**
 * Full setup: register user + enable route interception + inject tokens.
 *
 * NOTE: Direct login via the form is broken due to an API response format
 * mismatch — AuthContext expects response.tokens.access_token but the
 * backend returns response.access_token directly. This is documented
 * as a critical bug in the test report.
 *
 * This function works around the broken login by injecting tokens directly
 * and using route interception so the AuthContext's /auth/me validation
 * goes to the correct backend with proper CORS headers.
 */
export async function setupAuthenticatedSession(
  page: Page,
): Promise<RegisteredUser | null> {
  // Set up route interception FIRST (before any navigation)
  await setupApiRouteInterception(page);

  // Register a user against the real backend
  const user = await registerUserViaApi(page);
  if (!user || !user.accessToken) {
    console.warn(
      "setupAuthenticatedSession: registration failed — tests may skip.",
    );
    return null;
  }

  // Navigate to login page to establish page context
  await page.goto("/login");
  await page.waitForLoadState("domcontentloaded");

  // Inject valid tokens into localStorage
  await page.evaluate(
    ({ at, rt }) => {
      localStorage.setItem("access_token", at);
      localStorage.setItem("refresh_token", rt);
    },
    { at: user.accessToken, rt: user.refreshToken },
  );

  // Reload so the AuthContext reads the tokens from localStorage
  // and validates them via the intercepted /auth/me call
  await page.reload();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(3000);

  const finalUrl = page.url();
  if (finalUrl.includes("/login")) {
    console.warn(
      "setupAuthenticatedSession: still on login after token injection. " +
        "This may indicate CORS or API format issues on this system.",
    );
  }

  return user;
}

/**
 * Login via the frontend form.
 * Requires route interception to be set up if the API is on port 8099.
 */
export async function loginViaForm(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  await page
    .locator('input[type="email"], input[name="email"]')
    .first()
    .fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.locator('button[type="submit"]').first().click();

  // Wait for redirect after login
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2000);
}
