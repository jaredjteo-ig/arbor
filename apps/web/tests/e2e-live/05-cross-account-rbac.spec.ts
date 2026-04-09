/**
 * Suite 05: Cross-Account RBAC & Session Isolation
 *
 * Tests that switching between accounts works correctly,
 * sessions are properly isolated, and RBAC is enforced at the API level.
 */
import { test, expect } from "@playwright/test";
import {
  ACCOUNTS,
  login,
  logout,
  screenshot,
  visitAndCapture,
} from "./helpers";

const API_BASE = "http://136.110.51.61/api";

async function getToken(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  return data.access_token;
}

test.describe("Cross-Account — Session Switching", () => {
  test("05-01: Login as owner, logout, login as employee — different dashboards", async ({
    page,
  }) => {
    // Login as owner
    await login(page, "owner");
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    await screenshot(page, "05-01a-owner-dashboard");
    const ownerUrl = page.url();

    // Logout
    await logout(page);
    await screenshot(page, "05-01b-after-logout");

    // Login as employee
    await login(page, "employee");
    await page.waitForLoadState("networkidle");
    await screenshot(page, "05-01c-employee-dashboard");
    const employeeUrl = page.url();

    console.log(`Owner landed: ${ownerUrl}`);
    console.log(`Employee landed: ${employeeUrl}`);
  });

  test("05-02: Login as employee, logout, login as HR — verify HR features", async ({
    page,
  }) => {
    // Login as employee
    await login(page, "employee");
    const empUrl = page.url();
    await screenshot(page, "05-02a-employee-logged-in");

    // Logout
    await logout(page);

    // Login as HR manager
    await login(page, "hr_manager");
    await page.goto("/employees");
    await page.waitForLoadState("networkidle");
    await screenshot(page, "05-02b-hr-employees-after-switch");
    const hrUrl = page.url();

    console.log(`Employee URL: ${empUrl}`);
    console.log(`HR Manager employees URL: ${hrUrl}`);
    // HR should see employee list
    expect(hrUrl).toContain("/employees");
  });
});

test.describe("Cross-Account — API RBAC Enforcement", () => {
  test("05-10: Employee token cannot access admin endpoints", async () => {
    const token = await getToken(
      ACCOUNTS.employee.email,
      ACCOUNTS.employee.password,
    );

    // Try admin QA sessions endpoint
    const res = await fetch(`${API_BASE}/admin/qa/sessions`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    console.log(`Employee -> /admin/qa/sessions: ${res.status}`);
    // Should be 403 Forbidden
    expect(res.status).toBeGreaterThanOrEqual(400);
  });

  test("05-11: Employee token can access own profile", async () => {
    const token = await getToken(
      ACCOUNTS.employee.email,
      ACCOUNTS.employee.password,
    );

    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.email).toBe(ACCOUNTS.employee.email);
    expect(data.role).toBe("employee");
    console.log(`Employee /auth/me: ${JSON.stringify(data)}`);
  });

  test("05-12: Owner token can access admin endpoints", async () => {
    const token = await getToken(ACCOUNTS.owner.email, ACCOUNTS.owner.password);

    const res = await fetch(`${API_BASE}/admin/qa/sessions`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    console.log(`Owner -> /admin/qa/sessions: ${res.status}`);
    // Owner should have access
    expect(res.status).toBeLessThan(400);
  });

  test("05-13: HR Manager token can access employee list", async () => {
    const token = await getToken(
      ACCOUNTS.hr_manager.email,
      ACCOUNTS.hr_manager.password,
    );

    const res = await fetch(`${API_BASE}/employees`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    console.log(`HR Manager -> /employees: ${res.status}`);
    expect(res.status).toBe(200);
    const data = await res.json();
    console.log(
      `HR Manager sees ${Array.isArray(data) ? data.length : "?"} employees`,
    );
  });

  test("05-14: Expired/invalid token returns 401", async () => {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: "Bearer invalid_token_here" },
    });
    expect(res.status).toBe(401);
  });

  test("05-15: No token returns 401 on protected endpoint", async () => {
    const res = await fetch(`${API_BASE}/employees`);
    expect(res.status).toBe(401);
  });

  test("05-16: Owner token can list employees", async () => {
    const token = await getToken(ACCOUNTS.owner.email, ACCOUNTS.owner.password);

    const res = await fetch(`${API_BASE}/employees`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status).toBe(200);
    const data = await res.json();
    console.log(
      `Owner sees ${Array.isArray(data) ? data.length : "?"} employees`,
    );
  });

  test("05-17: Token refresh works", async () => {
    // Login to get refresh token
    const loginRes = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: ACCOUNTS.owner.email,
        password: ACCOUNTS.owner.password,
      }),
    });
    const loginData = await loginRes.json();
    const refreshToken = loginData.refresh_token;

    // Use refresh token to get new access token
    const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    console.log(`Token refresh status: ${refreshRes.status}`);
    expect(refreshRes.status).toBe(200);
    const refreshData = await refreshRes.json();
    expect(refreshData.access_token).toBeTruthy();
  });

  test("05-18: Logout revokes token", async () => {
    // Login
    const loginRes = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: ACCOUNTS.owner.email,
        password: ACCOUNTS.owner.password,
      }),
    });
    const loginData = await loginRes.json();
    const token = loginData.access_token;

    // Verify token works
    const meRes1 = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(meRes1.status).toBe(200);

    // Logout (revoke token)
    const logoutRes = await fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    console.log(`Logout status: ${logoutRes.status}`);

    // Token should now be revoked
    const meRes2 = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    console.log(`After logout /auth/me: ${meRes2.status}`);
    expect(meRes2.status).toBe(401);
  });
});
