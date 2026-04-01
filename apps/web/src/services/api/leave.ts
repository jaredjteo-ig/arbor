/* ── Leave API Service ────────────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface LeaveType {
  id: number;
  name: string;
  description: string;
  is_paid: boolean;
  requires_attachment: boolean;
  max_days_per_year: number;
  is_active: boolean;
}

export interface LeaveApplication {
  id: number;
  employee_id: number;
  employee_name: string;
  leave_type_id: number;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  half_day_start: boolean;
  half_day_end: boolean;
  total_days: number;
  reason: string;
  status:
    | "draft"
    | "pending"
    | "approved"
    | "rejected"
    | "withdrawn"
    | "cancelled";
  attachment_url: string | null;
  approver_id: number | null;
  approver_name: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeaveBalance {
  leave_type_id: number;
  leave_type_name: string;
  entitlement: number;
  used: number;
  pending: number;
  remaining: number;
}

export interface PublicHoliday {
  id: number;
  name: string;
  date: string;
  is_recurring: boolean;
}

export interface LeaveCalendarEntry {
  date: string;
  employee_id: number;
  employee_name: string;
  leave_type_name: string;
  status: string;
  is_half_day: boolean;
}

export interface ApplyLeaveData {
  leave_type_id: number;
  start_date: string;
  end_date: string;
  half_day_start?: boolean;
  half_day_end?: boolean;
  reason: string;
}

/* ── API Methods ─────────────────────────────────────────── */

export const leaveApi = {
  /** List all leave types configured for the company. */
  listTypes(): Promise<{ types: LeaveType[] }> {
    return apiClient.get<{ types: LeaveType[] }>("/leave/types");
  },

  /** Apply for leave. */
  applyLeave(data: ApplyLeaveData): Promise<LeaveApplication> {
    return apiClient.post<LeaveApplication>("/leave/applications", data);
  },

  /** Upload an attachment (e.g. medical certificate) for a leave application. */
  uploadAttachment(
    applicationId: number,
    formData: FormData,
  ): Promise<{ url: string }> {
    return apiClient.postFormData<{ url: string }>(
      `/leave/applications/${applicationId}/attachment`,
      formData,
    );
  },

  /** List leave applications with optional filters. */
  listApplications(params?: {
    status?: string;
    employee_id?: string;
  }): Promise<{ applications: LeaveApplication[]; count: number }> {
    return apiClient.get<{ applications: LeaveApplication[]; count: number }>(
      "/leave/applications",
      params,
    );
  },

  /** Approve a leave application. */
  approve(applicationId: number): Promise<LeaveApplication> {
    return apiClient.patch<LeaveApplication>(
      `/leave/applications/${applicationId}/approve`,
    );
  },

  /** Reject a leave application. */
  reject(applicationId: number, reason: string): Promise<LeaveApplication> {
    return apiClient.patch<LeaveApplication>(
      `/leave/applications/${applicationId}/reject`,
      { reason },
    );
  },

  /** Withdraw a pending leave application (by the employee). */
  withdraw(applicationId: number): Promise<LeaveApplication> {
    return apiClient.patch<LeaveApplication>(
      `/leave/applications/${applicationId}/withdraw`,
    );
  },

  /** Cancel an approved leave application (by admin). */
  cancel(applicationId: number): Promise<LeaveApplication> {
    return apiClient.patch<LeaveApplication>(
      `/leave/applications/${applicationId}/cancel`,
    );
  },

  /** Get leave balances for the current employee. */
  getBalances(): Promise<{ balances: LeaveBalance[] }> {
    return apiClient.get<{ balances: LeaveBalance[] }>("/leave/balances");
  },

  /** Get leave balances for a specific employee (admin). */
  getEmployeeBalances(
    employeeId: number,
  ): Promise<{ balances: LeaveBalance[] }> {
    return apiClient.get<{ balances: LeaveBalance[] }>(
      `/leave/balances/${employeeId}`,
    );
  },

  /** List public holidays. */
  listHolidays(): Promise<{ holidays: PublicHoliday[] }> {
    return apiClient.get<{ holidays: PublicHoliday[] }>(
      "/leave/public-holidays",
    );
  },

  /** Get leave calendar for a date range. */
  getCalendar(params: {
    start_date: string;
    end_date: string;
  }): Promise<{ entries: LeaveCalendarEntry[] }> {
    return apiClient.get<{ entries: LeaveCalendarEntry[] }>(
      "/leave/calendar",
      params,
    );
  },
};
