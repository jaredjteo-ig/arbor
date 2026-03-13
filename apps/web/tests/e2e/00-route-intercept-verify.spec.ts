/**
 * Diagnostic test: verify route interception and auth flow
 */
import { test, expect } from "@playwright/test";

const SCREENSHOT_DIR = "tests/e2e/screenshots";

test("00-verify-route-intercept", async ({ page }) => {
  const interceptedUrls: string[] = [];

  // Set up route interception - Playwright uses glob patterns
  await page.route("http://localhost:8000/**", async (route) => {
    const url = route.request().url();
    console.log("INTERCEPTED:", url);
    interceptedUrls.push(url);
    const redirectUrl = url.replace("localhost:8000", "localhost:8099");
    await route.continue({ url: redirectUrl });
  });

  await page.goto("http://localhost:3002/login");
  await page.waitForLoadState("networkidle");

  console.log("Page loaded, intercepted so far:", interceptedUrls.length);

  // Now inject token that's actually valid
  // Register fresh user against port 8099
  const email = `e2e_route_${Date.now()}@test.io`;
  const regResp = await page.request.post(
    "http://localhost:8099/auth/register",
    {
      data: { name: "Route Test", email, password: "SecurePass1!" },
      headers: { "Content-Type": "application/json" },
      timeout: 10000,
    },
  );

  let accessToken = "";
  if (regResp.ok()) {
    const body = await regResp.json();
    accessToken = body.access_token;
    console.log("REGISTERED user:", email, "Token length:", accessToken.length);
  } else {
    console.log("REGISTRATION FAILED:", regResp.status());
  }

  await page.evaluate(
    ({ at }) => {
      localStorage.setItem("access_token", at);
      localStorage.setItem("refresh_token", at);
    },
    { at: accessToken },
  );

  // Navigate to advisory - this should trigger AuthContext to validate token
  await page.goto("http://localhost:3002/advisory");
  await page.waitForTimeout(5000);

  await page.screenshot({
    path: `${SCREENSHOT_DIR}/00-route-intercept-result.png`,
    fullPage: true,
  });

  const finalUrl = page.url();
  console.log("INTERCEPTED URLS:", interceptedUrls);
  console.log("FINAL URL:", finalUrl);

  const bodyText = (await page.locator("body").textContent()) ?? "";
  const meaningful = bodyText
    .replace(/self\.__next.*$/gm, "")
    .trim()
    .slice(0, 500);
  console.log("PAGE CONTENT:", meaningful);
});
