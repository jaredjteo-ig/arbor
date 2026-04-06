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

export interface CpfYtd {
  employee_id: number;
  year: number;
  total_ow: number;
  total_aw: number;
  total_employer_cpf: number;
  total_employee_cpf: number;
  months: Record<string, unknown>[];
}

export interface SummaryReport {
  run_id: number;
  period_start: string;
  period_end: string;
  total_gross: number;
  total_net: number;
  total_employer_cpf: number;
  total_employee_cpf: number;
  total_sdl: number;
  total_fwl: number;
  total_shg: number;
  employee_count: number;
  payslips: PayslipSummary[];
}

export interface YtdReport {
  year: number;
  total_gross: number;
  total_net: number;
  total_employer_cpf: number;
  total_employee_cpf: number;
  months: Record<string, unknown>[];
}

/* ── API Methods ─────────────────────────────────────────── */

/* ── Parallel Run Types ──────────────────────────────────── */

export interface ParallelRunUploadResult {
  id: number;
  filename: string;
  rows_parsed: number;
  status: "uploaded" | "error";
}

export interface ParallelRunVariance {
  employee_name: string;
  field: string;
  arbor_value: number;
  uploaded_value: number;
  difference: number;
  percentage_diff: number;
}

export interface ParallelRunComparison {
  id: number;
  total_employees: number;
  matched: number;
  variances: ParallelRunVariance[];
  status: "matched" | "has_variances";
}

export const payrollApi = {
  /** Calculate a new payroll run. */
  calculatePayroll(data: CalculatePayrollData): Promise<PayrollRun> {
    return apiClient.post<PayrollRun>("/payroll/calculate", data);
  },

  /** List all payroll runs for the current company. */
  listRuns(): Promise<PayrollRun[]> {
    return apiClient.get<PayrollRun[]>("/payroll/runs");
  },

  /** Get a single payroll run with payslip summaries. */
  getRun(id: number): Promise<PayrollRunDetail> {
    return apiClient.get<PayrollRunDetail>(`/payroll/runs/${id}`);
  },

  /** Get full payslip detail including line items. */
  getPayslipDetail(runId: number, payslipId: number): Promise<PayslipDetail> {
    return apiClient.get<PayslipDetail>(
      `/payroll/runs/${runId}/payslips/${payslipId}`,
    );
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
  myPayslips(): Promise<Payslip[]> {
    return apiClient.get<Payslip[]>("/payroll/my-payslips");
  },

  /** Employee: get own payslip detail with items. */
  myPayslipDetail(id: number): Promise<PayslipDetail> {
    return apiClient.get<PayslipDetail>(`/payroll/my-payslips/${id}`);
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

  /* ── Parallel Run ──────────────────────────────────────── */

  /** Upload a legacy payroll file for parallel comparison. */
  uploadParallelRun(
    runId: number,
    formData: FormData,
  ): Promise<ParallelRunUploadResult> {
    return apiClient.postFormData<ParallelRunUploadResult>(
      `/payroll/runs/${runId}/parallel-upload`,
      formData,
    );
  },

  /** Compare the uploaded file against the Arbor payroll run. */
  compareParallelRun(runId: number): Promise<ParallelRunComparison> {
    return apiClient.post<ParallelRunComparison>(
      `/payroll/runs/${runId}/parallel-compare`,
    );
  },

  /* ── Payslip PDF Downloads ─────────────────────────────── */

  /** Employee: download own payslip as PDF. */
  async downloadMyPayslipPdf(payslipId: number): Promise<Blob> {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(
      `${API_BASE}/payroll/my-payslips/${payslipId}/pdf`,
      {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      },
    );
    if (!res.ok) throw new Error("Failed to download payslip PDF");
    return res.blob();
  },

  /** Admin: download a payslip PDF for a specific run/payslip. */
  async downloadPayslipPdf(runId: number, payslipId: number): Promise<Blob> {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(
      `${API_BASE}/payroll/runs/${runId}/payslips/${payslipId}/pdf`,
      {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      },
    );
    if (!res.ok) throw new Error("Failed to download payslip PDF");
    return res.blob();
  },
};
