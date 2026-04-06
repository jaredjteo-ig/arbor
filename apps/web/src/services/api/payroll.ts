/* ── Payroll API Service ──────────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface PayrollRun {
  id: number;
  company_id: number;
  period_start: string;
  period_end: string;
  pay_date: string;
  status: "draft" | "approved" | "paid" | "cancelled";
  payroll_type: string;
  total_gross: number;
  total_net: number;
  total_employer_cpf: number;
  total_employee_cpf: number;
  total_sdl: number;
  total_fwl: number;
  total_shg: number;
  employee_count: number;
  created_by: number;
  approved_by: number | null;
  approved_at: string;
  notes: string;
}

export interface PayslipSummary {
  payslip_id: number;
  employee_id: number;
  name: string;
  basic_salary: number;
  gross_salary: number;
  net_salary: number;
  employer_cpf: number;
  employee_cpf: number;
  employee_name?: string;
  employee_email?: string;
}

export interface PayslipItem {
  id: number;
  item_type: string;
  name: string;
  amount: number;
  is_taxable: boolean;
  is_cpf_applicable: boolean;
  notes: string;
}

export interface Payslip extends PayslipSummary {
  period_start: string;
  period_end: string;
  sdl: number;
  fwl: number;
  shg_fund: string;
  shg_amount: number;
  cpf_ow_used: number;
  status: string;
}

export interface CalculatePayrollData {
  period_start: string;
  period_end: string;
  pay_date: string;
  payroll_type: string;
}

export interface PayrollRunDetail extends PayrollRun {
  payslips: PayslipSummary[];
}

export interface PayslipDetail extends Payslip {
  items: PayslipItem[];
}

export interface CpfYtdRecord {
  employee_id: number;
  company_id: number;
  year: number;
  month: number;
  ow_subject_to_cpf: number;
  aw_subject_to_cpf: number;
  ytd_ow_total: number;
  ytd_aw_total: number;
  employer_cpf: number;
  employee_cpf: number;
  payslip_id: number;
}

export interface CpfYtd {
  year: number;
  records: CpfYtdRecord[];
}

export interface DepartmentSummary {
  department: string;
  employee_count: number;
  total_gross: number;
  total_net: number;
  total_employer_cpf: number;
  total_employee_cpf: number;
}

export interface SummaryReport {
  run: PayrollRun;
  by_department: DepartmentSummary[];
}

export interface YtdEmployee {
  employee_id: number;
  name: string;
  department: string;
  ytd_gross: number;
  ytd_net: number;
  ytd_employer_cpf: number;
  ytd_employee_cpf: number;
  months_paid: number;
}

export interface YtdReport {
  year: number;
  employees: YtdEmployee[];
}

/* ── API Methods ─────────────────────────────────────────── */

export const payrollApi = {
  /** Calculate a new payroll run. Returns the payroll_run object. */
  async calculatePayroll(data: CalculatePayrollData): Promise<PayrollRun> {
    const resp = await apiClient.post<{
      payroll_run: PayrollRun;
      payslips: PayslipSummary[];
    }>("/payroll/calculate", data);
    return resp.payroll_run;
  },

  /** List all payroll runs for the current company. */
  async listRuns(): Promise<PayrollRun[]> {
    const resp = await apiClient.get<{ runs: PayrollRun[]; count: number }>(
      "/payroll/runs",
    );
    return resp.runs;
  },

  /** Get a single payroll run with payslip summaries. */
  async getRun(id: number): Promise<PayrollRunDetail> {
    const resp = await apiClient.get<{
      run: PayrollRun;
      payslips: PayslipSummary[];
    }>(`/payroll/runs/${id}`);
    return { ...resp.run, payslips: resp.payslips };
  },

  /** Get full payslip detail including line items. */
  async getPayslipDetail(
    runId: number,
    payslipId: number,
  ): Promise<PayslipDetail> {
    const resp = await apiClient.get<{
      payslip: Payslip;
      items: PayslipItem[];
    }>(`/payroll/runs/${runId}/payslips/${payslipId}`);
    return { ...resp.payslip, items: resp.items };
  },

  /** Approve a payroll run. */
  approveRun(id: number): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/payroll/runs/${id}/approve`);
  },

  /** Mark a payroll run as paid. */
  markPaid(id: number): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/payroll/runs/${id}/mark-paid`);
  },

  /** Cancel a payroll run. */
  cancelRun(id: number): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/payroll/runs/${id}/cancel`);
  },

  /** Employee: list own payslips. */
  async myPayslips(): Promise<Payslip[]> {
    const resp = await apiClient.get<{ payslips: Payslip[] }>(
      "/payroll/my-payslips",
    );
    return resp.payslips;
  },

  /** Employee: get own payslip detail with items. */
  async myPayslipDetail(id: number): Promise<PayslipDetail> {
    const resp = await apiClient.get<{
      payslip: Payslip;
      items: PayslipItem[];
    }>(`/payroll/my-payslips/${id}`);
    return { ...resp.payslip, items: resp.items };
  },

  /** CPF year-to-date for an employee. */
  cpfYtd(employeeId: number, year: number): Promise<CpfYtd> {
    return apiClient.get<CpfYtd>(`/payroll/cpf-ytd/${employeeId}`, {
      year: String(year),
    });
  },

  /** Summary report for a payroll run. */
  summaryReport(runId: number): Promise<SummaryReport> {
    return apiClient.get<SummaryReport>("/payroll/reports/summary", {
      run_id: String(runId),
    });
  },

  /** Year-to-date report. */
  ytdReport(year: number): Promise<YtdReport> {
    return apiClient.get<YtdReport>("/payroll/reports/ytd", {
      year: String(year),
    });
  },
};
