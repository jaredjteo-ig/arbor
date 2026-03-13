/**
 * Debug test: test login via the frontend form (not token injection)
 * The route intercept ensures the login form call goes to port 8099.
 */
import { test } from "@playwright/test";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

test("debug-login-via-form", async ({ page }) => {
  const networkCalls: { url: string; status: number; body: string }[] = [];

  // Intercept ALL requests to log them and fix CORS
  await page.route("http://localhost:8000/**", async (route) => {
    const originalUrl = route.request().url();
    const targetUrl = originalUrl.replace("localhost:8000", "localhost:8099");

    try {
      const response = await route.fetch({ url: targetUrl });
      const body = await response.body();
      const bodyText = body.toString("utf-8").slice(0, 200);

      networkCalls.push({
        url: originalUrl,
        status: response.status(),
        body: bodyText,
      });

      console.log(`API ${originalUrl} -> ${response.status()}: ${bodyText}`);

      // Add CORS header for port 3002
      const headers: Record<string, string> = {};
      for (const [k, v] of Object.entries(response.headers())) {
        headers[k] = v;
      }
      headers["access-control-allow-origin"] = "http://localhost:3002";
      headers["access-control-allow-credentials"] = "true";

      await route.fulfill({ status: response.status(), headers, body });
    } catch (err) {
      console.log(`ROUTE ERROR: ${err}`);
      await route.continue({ url: targetUrl });
    }
  });

  // Register a user against port 8099 directly
  const email = `login_form_${Date.now()}@test.io`;
  const regResp = await page.request.post(
    "http://localhost:8099/auth/register",
    {
      data: { name: "Form Login", email, password: "SecurePass1!" },
      headers: { "Content-Type": "application/json" },
      timeout: 15000,
    },
  );

  if (!regResp.ok()) {
    console.log("REGISTRATION FAILED:", regResp.status());
    return;
  }
  console.log("User registered:", email);

  // Navigate to login and fill the form
  await page.goto("http://localhost:3002/login");
  await page.waitForLoadState("networkidle");

  // Fill the login form
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill("SecurePass1!");
  await page.locator('button[type="submit"]').click();

  // Wait for navigation
  await page.waitForTimeout(5000);

  console.log("FINAL URL:", page.url());
  console.log(
    "NETWORK CALLS:",
    networkCalls.map((c) => `${c.url} -> ${c.status}`),
  );

  const bodyText = (await page.locator("body").textContent()) ?? "";
  const meaningful = bodyText
    .replace(/self\.__next.*$/gm, "")
    .trim()
    .slice(0, 600);
  console.log("PAGE CONTENT:", meaningful);

  await page.screenshot({
    path: `${SCREENSHOT_DIR}/00-debug-login-form.png`,
    fullPage: true,
  });
});
