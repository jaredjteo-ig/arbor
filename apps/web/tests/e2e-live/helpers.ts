import { type Page, expect } from "@playwright/test";

const SCREENSHOT_DIR = "tests/e2e-live/screenshots";

export const ACCOUNTS = {
  owner: {
    email: "demo@central.kailash.ai",
    password: "CentralDemo2026!",
    role: "owner",
    name: "Demo Admin",
  },
  hr_manager: {
    email: "grace.koh@central-solutions.sg",
    password: "Employee2026!",
    role: "hr_manager",
    name: "Grace Koh",
  },
  employee: {
    email: "lily.phang@central-solutions.sg",
    password: "Employee2026!",
    role: "employee",
    name: "Lily Phang",
  },
} as const;

export type AccountKey = keyof typeof ACCOUNTS;

export async function login(page: Page, account: AccountKey): Promise<void> {
  const { email, password } = ACCOUNTS[account];
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  await page
    .locator('input[type="email"], input[name="email"]')
    .first()
    .fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.locator('button[type="submit"]').first().click();
  // Wait for redirect away from login
  await page.waitForURL((url) => !url.pathname.includes("/login"), {
    timeout: 15000,
  });
  await page.waitForLoadState("networkidle");
}

export async function logout(page: Page): Promise<void> {
  // Look for user menu / profile dropdown
  const avatar = page
    .locator(
      '[data-testid="user-menu"], [data-testid="profile-dropdown"], button:has(svg[class*="user"]), button:has(img[alt*="avatar"]), button:has(img[alt*="profile"])',
    )
    .first();

  if (await avatar.isVisible({ timeout: 3000 }).catch(() => false)) {
    await avatar.click();
    await page.waitForTimeout(500);
  }

  const logoutBtn = page
    .getByRole("button", { name: /log\s*out|sign\s*out/i })
    .first();
  if (await logoutBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await logoutBtn.click();
    await page.waitForURL(/\/login/, { timeout: 10000 });
    return;
  }

  // Fallback: try link
  const logoutLink = page
    .getByRole("link", { name: /log\s*out|sign\s*out/i })
    .first();
  if (await logoutLink.isVisible({ timeout: 2000 }).catch(() => false)) {
    await logoutLink.click();
    await page.waitForURL(/\/login/, { timeout: 10000 });
    return;
  }

  // Last resort: navigate to login and clear storage
  await page.evaluate(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  });
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
}

export function screenshot(page: Page, name: string) {
  return page.screenshot({
    path: `${SCREENSHOT_DIR}/${name}.png`,
    fullPage: true,
  });
}

export async function getPageTitle(page: Page): Promise<string> {
  return (
    (await page.locator("h1, h2, [role='heading']").first().textContent()) ?? ""
  );
}

/**
 * Navigate to a page and capture a screenshot.
 * Returns the visible body text for assertions.
 */
export async function visitAndCapture(
  page: Page,
  path: string,
  screenshotName: string,
): Promise<{ url: string; bodyText: string; status: number }> {
  const response = await page.goto(path);
  await page.waitForLoadState("networkidle");
  await screenshot(page, screenshotName);
  const bodyText = (await page.locator("body").textContent()) ?? "";
  return {
    url: page.url(),
    bodyText,
    status: response?.status() ?? 0,
  };
}
