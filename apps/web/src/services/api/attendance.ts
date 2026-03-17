/* ── Attendance API Service ───────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface AttendanceRecord {
  id: number;
  employee_id: number;
  employee_name?: string;
  date: string;
  clock_in: string | null;
  clock_out: string | null;
  work_hours: number;
  overtime_hours: number;
  status: "present" | "late" | "absent" | "half_day" | "on_leave" | "holiday";
  remarks: string;
  is_manual: boolean;
}

export interface AttendanceSettings {
  work_start_time: string;
  work_end_time: string;
  late_threshold_minutes: number;
  overtime_threshold_minutes: number;
  auto_clock_out: boolean;
  auto_clock_out_time: string | null;
}

export interface TimesheetApproval {
  id: number;
  employee_id: number;
  employee_name: string;
  period_start: string;
  period_end: string;
  total_days: number;
  total_hours: number;
  status: "pending" | "approved" | "rejected";
  submitted_at: string;
  approved_at: string | null;
  approver_name: string | null;
}

export interface AttendanceSummary {
  total_working_days: number;
  present_days: number;
  late_days: number;
  absent_days: number;
  leave_days: number;
  average_hours: number;
}

export interface TodayAttendance {
  employee_id: number;
  employee_name: string;
  clock_in: string | null;
  clock_out: string | null;
  status: "present" | "late" | "absent" | "on_leave" | "not_clocked_in";
}

/* ── API Methods ─────────────────────────────────────────── */

export const attendanceApi = {
  /** Clock in for the current employee. */
  clockIn(data?: {
    location?: { lat: number; lng: number };
    photo?: string;
  }): Promise<{ record: AttendanceRecord }> {
    return apiClient.post<{ record: AttendanceRecord }>(
      "/attendance/clock-in",
      data ?? {},
    );
  },

  /** Clock out for the current employee. */
  clockOut(data?: {
    location?: { lat: number; lng: number };
    photo?: string;
  }): Promise<{ record: AttendanceRecord }> {
    return apiClient.post<{ record: AttendanceRecord }>(
      "/attendance/clock-out",
      data ?? {},
    );
  },

  /** Get today's attendance record for the current employee. */
  getToday(): Promise<{ record: AttendanceRecord | null }> {
    return apiClient.get<{ record: AttendanceRecord | null }>(
      "/attendance/today",
    );
  },

  /** List attendance records with optional filters. */
  listRecords(params?: {
    employee_id?: string;
    month?: number;
    year?: number;
  }): Promise<{ records: AttendanceRecord[]; count: number }> {
    return apiClient.get<{ records: AttendanceRecord[]; count: number }>(
      "/attendance/records",
      params as Record<string, string>,
    );
  },

  /** Get attendance summary for a period. */
  getSummary(params: {
    employee_id?: string;
    start_date: string;
    end_date: string;
  }): Promise<AttendanceSummary> {
    return apiClient.get<AttendanceSummary>("/attendance/summary", params);
  },

  /** Get attendance settings (admin). */
  getSettings(): Promise<AttendanceSettings> {
    return apiClient.get<AttendanceSettings>("/attendance/settings");
  },

  /** Update attendance settings (admin). */
  updateSettings(
    data: Partial<AttendanceSettings>,
  ): Promise<AttendanceSettings> {
    return apiClient.put<AttendanceSettings>("/attendance/settings", data);
  },

  /** Submit a timesheet for approval. */
  submitTimesheet(params: {
    period_start: string;
    period_end: string;
  }): Promise<TimesheetApproval> {
    return apiClient.post<TimesheetApproval>(
      "/attendance/timesheets/submit",
      params,
    );
  },

  /** Approve a timesheet (admin). */
  approveTimesheet(timesheetId: number): Promise<TimesheetApproval> {
    return apiClient.post<TimesheetApproval>(
      `/attendance/timesheets/${timesheetId}/approve`,
    );
  },

  /** List timesheets with optional filters. */
  listTimesheets(params?: {
    status?: string;
    employee_id?: string;
  }): Promise<{ timesheets: TimesheetApproval[]; count: number }> {
    return apiClient.get<{ timesheets: TimesheetApproval[]; count: number }>(
      "/attendance/timesheets",
      params,
    );
  },

  /** Get today's attendance overview for all employees (admin). */
  getTodayOverview(): Promise<{ employees: TodayAttendance[] }> {
    return apiClient.get<{ employees: TodayAttendance[] }>(
      "/attendance/today/overview",
    );
  },
};
