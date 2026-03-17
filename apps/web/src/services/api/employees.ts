/* ── Employees API Service ────────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface Employee {
  id: number;
  name: string;
  email: string;
  department: string;
  job_title?: string;
  status: "active" | "invited" | "inactive";
  start_date?: string;
  employment_type?: string;
}

export interface EmployeeRecord {
  id: number;
  name: string;
  email: string;
  department: string;
  job_title: string;
  start_date: string;
  employment_type: string;
}

export interface LeaveBalance {
  name: string;
  entitlement: number;
  used: number;
  pending: number;
}

export interface CompanyPolicy {
  id: string;
  title: string;
  summary: string;
  content: string[];
  category?: string;
}

export interface InviteEmployeeData {
  email: string;
  role: string;
}

/* ── API Methods ─────────────────────────────────────────── */

export const employeesApi = {
  /** Admin: list all employees for the current company. */
  list(): Promise<{ employees: Employee[]; count: number }> {
    return apiClient.get<{ employees: Employee[]; count: number }>(
      "/employees",
    );
  },

  /** Employee: get own employee record. */
  me(): Promise<EmployeeRecord> {
    return apiClient.get<EmployeeRecord>("/employees/me");
  },

  /** Admin: invite a new employee by email. */
  invite(data: InviteEmployeeData): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>("/employees/invite", data);
  },

  /** Get leave balances for the current employee. */
  leaveBalances(): Promise<{ balances: LeaveBalance[] }> {
    return apiClient.get<{ balances: LeaveBalance[] }>("/employees/me/leave");
  },

  /** Get company policies (company-specific or platform defaults). */
  policies(): Promise<{ policies: CompanyPolicy[] }> {
    return apiClient.get<{ policies: CompanyPolicy[] }>("/employees/policies");
  },
};
