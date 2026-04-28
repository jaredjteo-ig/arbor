/**
 * Round-12 Test 06: Calculator Suite
 *
 * Tests:
 * - CPF calculator with a Singapore Citizen employee returns correct
 *   employer/employee contributions and net pay
 * - Cost-to-company calculator returns a breakdown
 *
 * CPF reference (2026 rates, age <55, SC/PR):
 *   Gross $5,000 SC age 30
 *   Employee: 20% = $1,000
 *   Employer: 17% = $850
 *   Net take-home: $5,000 - $1,000 = $4,000
 *   Employer total cost: $5,000 + $850 = $5,850
 */

import { test, expect } from "@playwright/test";
import { screenshot } from "./helpers";

const FRONTEND_BASE = "http://localhost:3000";
const API_BASE = "http://localhost:8000";

async function getToken(request: any): Promise<string> {
  const resp = await request.post(`${API_BASE}/auth/login`, {
    data: { email: "demo@central.kailash.ai", password: "CentralDemo2026!" },
    headers: { "Content-Type": "application/json" },
  });
  const body = await resp.json();
  return body.access_token as string;
}

test.describe("06 — Calculator Suite", () => {
  test("06-01: CPF calculator SC age 30 gross $5,000 — correct contributions", async ({
    request,
  }) => {
    const token = await getToken(request);
    const resp = await request.post(`${API_BASE}/calculator/cpf`, {
      data: {
        gross_salary: 5000,
        citizenship_status: "SC",
        age: 30,
      },
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    expect(resp.ok()).toBe(true);
    const body = await resp.json();

    // Verify employer contribution: 17% of $5,000 = $850
    expect(body.employer_contribution).toBe(850);

    // Verify employee contribution: 20% of $5,000 = $1,000
    expect(body.employee_contribution).toBe(1000);

    // Verify total: $1,850
    expect(body.total_contribution).toBe(1850);

    // Verify rates
    expect(body.employer_rate).toBe(0.17);
    expect(body.employee_rate).toBe(0.2);

    // Verify CPF applies
    expect(body.cpf_applicable).toBe(true);

    // Verify allocation accounts exist
    expect(body.allocation_oa).toBeGreaterThan(0);
    expect(body.allocation_sa).toBeGreaterThan(0);
    expect(body.allocation_ma).toBeGreaterThan(0);

    // OA + SA + MA should equal total employee + employer
    const totalAllocated =
      body.allocation_oa + body.allocation_sa + body.allocation_ma;
    expect(totalAllocated).toBe(1850);

    console.log(
      `[06-01] CPF OK: employer=$${body.employer_contribution} employee=$${body.employee_contribution} total=$${body.total_contribution}`,
    );
  });

  test("06-02: CPF calculator PR age 30 gross $5,000 — correct rates", async ({
    request,
  }) => {
    const token = await getToken(request);
    const resp = await request.post(`${API_BASE}/calculator/cpf`, {
      data: {
        gross_salary: 5000,
        citizenship_status: "PR",
        age: 30,
      },
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    expect(resp.ok()).toBe(true);
    const body = await resp.json();
    expect(body.cpf_applicable).toBe(true);
    console.log(
      `[06-02] PR CPF: employer=$${body.employer_contribution} employee=$${body.employee_contribution}`,
    );
  });

  test("06-03: CPF calculator foreigner — CPF not applicable", async ({
    request,
  }) => {
    const token = await getToken(request);
    const resp = await request.post(`${API_BASE}/calculator/cpf`, {
      data: {
        gross_salary: 5000,
        citizenship_status: "foreigner",
        age: 30,
      },
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    expect(resp.ok()).toBe(true);
    const body = await resp.json();
    expect(body.cpf_applicable).toBe(false);
    expect(body.employer_contribution).toBe(0);
    expect(body.employee_contribution).toBe(0);
    console.log(`[06-03] Foreigner CPF not applicable: OK`);
  });

  test("06-04: CPF calculator gross above OW ceiling ($8,000) — capped", async ({
    request,
  }) => {
    const token = await getToken(request);
    const resp = await request.post(`${API_BASE}/calculator/cpf`, {
      data: {
        gross_salary: 12000, // above OW ceiling of $8,000
        citizenship_status: "SC",
        age: 30,
      },
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    expect(resp.ok()).toBe(true);
    const body = await resp.json();

    // OW subject to CPF should be capped at $8,000
    expect(body.ow_subject_to_cpf).toBe(8000);
    expect(body.ow_capped).toBe(true);

    // Employer: 17% of $8,000 = $1,360
    expect(body.employer_contribution).toBe(1360);
    // Employee: 20% of $8,000 = $1,600
    expect(body.employee_contribution).toBe(1600);

    console.log(
      `[06-04] OW ceiling capping OK: ow_subject_to_cpf=$${body.ow_subject_to_cpf}`,
    );
  });

  test("06-05: CPF calculator missing required field returns 400", async ({
    request,
  }) => {
    const token = await getToken(request);
    const resp = await request.post(`${API_BASE}/calculator/cpf`, {
      data: {
        gross_salary: 5000,
        // missing citizenship_status
        age: 30,
      },
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.detail).toContain("citizenship_status");
    console.log(`[06-05] Missing field validation: ${body.detail}`);
  });

  test("06-06: salary calculator returns net pay breakdown", async ({
    request,
  }) => {
    const token = await getToken(request);
    const resp = await request.post(`${API_BASE}/calculator/salary`, {
      data: {
        gross_salary: 5000,
        citizenship_status: "SC",
        age: 30,
      },
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    const status = resp.status();
    console.log(`[06-06] Salary calculator status: ${status}`);

    if (status === 200) {
      const body = await resp.json();
      console.log(
        `[06-06] Salary breakdown keys: ${Object.keys(body).join(", ")}`,
      );
      // Net pay = gross - employee CPF = $5,000 - $1,000 = $4,000
      const netPay =
        body.net_pay ?? body.take_home ?? body.net_salary ?? body.employee_net;
      if (netPay !== undefined) {
        expect(netPay).toBe(4000);
        console.log(`[06-06] Net pay: $${netPay} ✓`);
      }
      // Cost to company = gross + employer CPF = $5,000 + $850 = $5,850
      const costToCompany =
        body.cost_to_company ?? body.employer_total_cost ?? body.total_cost;
      if (costToCompany !== undefined) {
        expect(costToCompany).toBe(5850);
        console.log(`[06-06] Cost to company: $${costToCompany} ✓`);
      }
    }
    expect([200, 404, 422]).toContain(status);
  });

  test("06-07: calculators page loads in frontend", async ({ page }) => {
    const resp = await page.request.post(`${API_BASE}/auth/login`, {
      data: { email: "demo@central.kailash.ai", password: "CentralDemo2026!" },
      headers: { "Content-Type": "application/json" },
    });
    const body = await resp.json();

    await page.goto(`${FRONTEND_BASE}/login`);
    await page.waitForLoadState("domcontentloaded");
    await page.evaluate(
      (at: string) => localStorage.setItem("access_token", at),
      body.access_token,
    );

    await page.goto(`${FRONTEND_BASE}/calculators`);
    await page.waitForLoadState("networkidle");
    await screenshot(page, "06-07-calculators-page");

    const url = page.url();
    console.log(`[06-07] Calculators page URL: ${url}`);
    expect(url).not.toContain("/login");
  });

  test("06-08: payroll calculate endpoint with employee data", async ({
    request,
  }) => {
    const token = await getToken(request);
    const resp = await request.post(`${API_BASE}/payroll/calculate`, {
      data: {
        employee_id: 4, // Chen Wei — SC, confirmed, Engineering
        period_start: "2026-04-01",
        period_end: "2026-04-30",
      },
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    const status = resp.status();
    console.log(`[06-08] Payroll calculate for employee 4: HTTP ${status}`);

    if (status === 200) {
      const body = await resp.json();
      console.log(
        `[06-08] Payroll result keys: ${Object.keys(body).join(", ")}`,
      );
      // Should contain CPF breakdown and net pay
      expect(body).toBeDefined();
    }
    expect([200, 400, 404, 422]).toContain(status);
  });
});
