/* ── Payroll API Service ──────────────────────────────────── */

import { apiClient, getValidAccessToken } from "./client";

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
  /** Xero ManualJournalID once exported; empty string means not exported. */
  xero_journal_id?: string;
  /** ISO timestamp of last successful Xero export; empty string when never. */
  xero_exported_at?: string;
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

  /**
   * Employee: download own payslip as PDF.
   * Triggers a browser download of the file.
   */
  async downloadMyPayslipPdf(payslipId: number): Promise<void> {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = await getValidAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(
      `${API_BASE}/payroll/my-payslips/${payslipId}/pdf`,
      {
        method: "GET",
        headers,
      },
    );

    if (!response.ok) {
      throw new Error(`Failed to download payslip PDF (${response.status})`);
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
    const filename = filenameMatch?.[1] ?? `payslip-${payslipId}.pdf`;

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },

  /**
   * Admin: download payslip PDF for a specific employee in a payroll run.
   * Triggers a browser download of the file.
   */
  async downloadPayslipPdf(runId: number, payslipId: number): Promise<void> {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = await getValidAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(
      `${API_BASE}/payroll/runs/${runId}/payslips/${payslipId}/pdf`,
      { method: "POST", headers },
    );

    if (!response.ok) {
      throw new Error(`Failed to download payslip PDF (${response.status})`);
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
    const filename = filenameMatch?.[1] ?? `payslip-${payslipId}.pdf`;

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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

  /* ── Parallel payroll run (external HRIS comparison) ───── */

  /** Upload external payslip CSV for parallel comparison. */
  async uploadParallelRun(file: File): Promise<ParallelUploadResult> {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.postFormData<ParallelUploadResult>(
      "/payroll/parallel/upload",
      formData,
    );
  },

  /** Compare an uploaded parallel run against an Arbor payroll run. */
  async compareParallelRun(
    parallelRunId: string,
    payrollRunId: number,
  ): Promise<ParallelCompareResult> {
    return apiClient.post<ParallelCompareResult>("/payroll/parallel/compare", {
      parallel_run_id: parallelRunId,
      payroll_run_id: payrollRunId,
    });
  },
};

/* ── Parallel Payroll Types ──────────────────────────────── */

export interface ParallelRow {
  employee_name: string;
  employee_id: string;
  period: string;
  gross_salary: number;
  net_salary: number;
  employee_cpf: number;
  employer_cpf: number;
  sdl: number;
}

export interface ParallelUploadResult {
  parallel_run_id: string;
  filename: string;
  row_count: number;
  rows: ParallelRow[];
}

export interface ParallelFieldComparison {
  field: string;
  external: number;
  arbor: number;
  difference: number;
  match: boolean;
  tolerance: number;
}

export interface ParallelEmployeeComparison {
  employee_name: string;
  employee_id: string;
  matched_by: string;
  overall_match: boolean;
  fields: ParallelFieldComparison[];
}

export interface ParallelUnmatched {
  employee_name: string;
  employee_id?: string;
  employee_id_internal?: string;
  reason: string;
}

export interface ParallelCompareSummary {
  employees_compared: number;
  full_matches: number;
  mismatches: number;
  unmatched_external: number;
  unmatched_arbor: number;
  largest_deviation: number;
  largest_deviation_field: string;
  largest_deviation_employee: string;
}

export interface ParallelCompareResult {
  parallel_run_id: string;
  payroll_run_id: number;
  arbor_run_period: string;
  arbor_run_status: string;
  summary: ParallelCompareSummary;
  comparisons: ParallelEmployeeComparison[];
  unmatched_external: ParallelUnmatched[];
  unmatched_arbor: ParallelUnmatched[];
}

/* ── Xero export ─────────────────────────────────────────── */

/** Six buckets the user maps to Xero account codes before export. */
export interface XeroAccountMapping {
  salary_expense_code: string;
  bonus_expense_code: string;
  employer_cpf_expense_code: string;
  sdl_expense_code: string;
  cpf_payable_code: string;
  net_pay_payable_code: string;
}

export interface XeroStatusResponse {
  connected: boolean;
  mapping_present: boolean;
  mapping_complete: boolean;
}

export interface XeroAccount {
  Code: string;
  Name: string;
  Type: string;
  [key: string]: unknown;
}

export interface XeroChartOfAccountsResponse {
  accounts: XeroAccount[];
}

/** GET /payroll/xero/account-mapping — saved or auto-matched. */
export interface XeroMappingResponse {
  source: "saved" | "auto_match" | "empty";
  mapping: XeroAccountMapping;
  complete: boolean;
  last_updated_at: string;
}

export interface XeroExportRequest {
  bonus_total?: number;
  narration?: string;
  force?: boolean;
}

export interface XeroExportLine {
  account_code: string;
  description: string;
  amount: number;
}

export interface XeroExportResponse {
  journal_id: string;
  status: string;
  narration: string;
  date: string;
  line_count: number;
  exported_at: string;
  lines_preview: XeroExportLine[];
}

export const xeroPayrollApi = {
  getStatus(): Promise<XeroStatusResponse> {
    return apiClient.get<XeroStatusResponse>("/payroll/xero/status");
  },

  getChartOfAccounts(): Promise<XeroChartOfAccountsResponse> {
    return apiClient.get<XeroChartOfAccountsResponse>(
      "/payroll/xero/chart-of-accounts",
    );
  },

  getMapping(): Promise<XeroMappingResponse> {
    return apiClient.get<XeroMappingResponse>("/payroll/xero/account-mapping");
  },

  putMapping(mapping: XeroAccountMapping): Promise<{
    mapping: XeroAccountMapping;
    complete: boolean;
    last_updated_at: string;
  }> {
    return apiClient.put("/payroll/xero/account-mapping", { mapping });
  },

  exportRun(
    runId: number,
    body: XeroExportRequest = {},
  ): Promise<XeroExportResponse> {
    return apiClient.post<XeroExportResponse>(
      `/payroll/runs/${runId}/export-xero`,
      body,
    );
  },
};
