/* ── Reports API Service ──────────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface ReportParams {
  start_date?: string;
  end_date?: string;
  department?: string;
  employee_id?: string;
  format?: "json" | "csv";
}

export interface HeadcountRow {
  department: string;
  active: number;
  inactive: number;
  total: number;
}

export interface TurnoverRow {
  month: string;
  hires: number;
  terminations: number;
  headcount: number;
  turnover_rate: number;
}

export interface TurnoverSummary {
  total_active: number;
  total_exits: number;
  overall_turnover_rate: number;
  avg_tenure_months: number;
}

export interface TurnoverByDepartment {
  department: string;
  active: number;
  exits: number;
  turnover_rate: number;
}

export interface TurnoverByExitType {
  exit_type: string;
  count: number;
}

export interface TurnoverReportResponse {
  rows: TurnoverRow[];
  summary: TurnoverSummary;
  by_department: TurnoverByDepartment[];
  by_exit_type: TurnoverByExitType[];
  generated_at: string;
}

export interface PayrollSummaryRow {
  period: string;
  total_gross: number;
  total_net: number;
  total_cpf_employee: number;
  total_cpf_employer: number;
  total_sdl: number;
  employee_count: number;
}

export interface LeaveUtilizationRow {
  leave_type: string;
  total_entitled: number;
  total_used: number;
  total_pending: number;
  utilization_pct: number;
}

export interface AttendanceRow {
  employee_name: string;
  total_days: number;
  present: number;
  absent: number;
  late: number;
  overtime_hours: number;
}

export interface ClaimsSummaryRow {
  category: string;
  total_claims: number;
  total_amount: number;
  approved_amount: number;
  pending_amount: number;
}

export interface ProjectCostRow {
  project_name: string;
  budget: number;
  actual_cost: number;
  variance: number;
  utilization_pct: number;
}

/* ── Response types matching actual backend ────────────────── */

export interface EmployeesReportResponse {
  employees: Record<string, unknown>[];
  count: number;
}

export interface PayrollReportResponse {
  period_start: string;
  period_end: string;
  runs: PayrollSummaryRow[];
  totals: {
    gross_pay: number;
    net_pay: number;
    employer_cpf: number;
    employee_cpf: number;
  };
}

export interface LeaveReportResponse {
  applications: Record<string, unknown>[];
  count: number;
}

export interface AttendanceReportResponse {
  date_from: string;
  date_to: string;
  records: Record<string, unknown>[];
  count: number;
  total_hours: number;
  total_overtime: number;
}

export interface ClaimsReportResponse {
  claims: Record<string, unknown>[];
  count: number;
  total_amount: number;
}

export interface ProjectsReportResponse {
  projects: ProjectCostRow[];
  count: number;
}

/* ── API ──────────────────────────────────────────────────── */

export const reportsApi = {
  /* Workforce -- GET /reports/employees */
  employees: (params?: Record<string, string>) =>
    apiClient.get<EmployeesReportResponse>("/reports/employees", params),

  /* Turnover -- GET /reports/turnover */
  turnover: (params?: Record<string, string>) =>
    apiClient.get<TurnoverReportResponse>("/reports/turnover", params),

  /* Payroll -- GET /reports/payroll */
  payrollSummary: (params?: Record<string, string>) =>
    apiClient.get<PayrollReportResponse>("/reports/payroll", params),

  /* Leave -- GET /reports/leave */
  leaveUtilization: (params?: Record<string, string>) =>
    apiClient.get<LeaveReportResponse>("/reports/leave", params),

  /* Attendance -- GET /reports/attendance */
  attendance: (params?: Record<string, string>) =>
    apiClient.get<AttendanceReportResponse>("/reports/attendance", params),

  /* Claims -- GET /reports/claims */
  claimsSummary: (params?: Record<string, string>) =>
    apiClient.get<ClaimsReportResponse>("/reports/claims", params),

  /* Projects -- GET /reports/projects */
  projectCosts: (params?: Record<string, string>) =>
    apiClient.get<ProjectsReportResponse>("/reports/projects", params),
};
