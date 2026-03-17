/* ── Shifts API Service ──────────────────────────────────── */
/* Shift scheduling: templates, assignments, publishing.      */

import { apiClient } from "./client";

/* ── Types ──────────────────────────────────────────────── */

export interface ShiftTemplate {
  id: number;
  company_id: number;
  name: string;
  start_time: string;
  end_time: string;
  break_minutes: number;
  work_hours: number;
  colour: string;
  is_active: boolean;
}

export interface ShiftAssignment {
  id: number;
  employee_id: number;
  company_id: number;
  shift_template_id: number;
  date: string;
  status: "scheduled" | "confirmed" | "completed" | "cancelled" | "no_show";
  actual_start: string;
  actual_end: string;
  notes: string;
  // Enriched fields from API
  employee_name?: string;
  template_name?: string;
  template_colour?: string;
}

export interface ShiftPublishRecord {
  id: number;
  company_id: number;
  week_start: string;
  published_at: string;
  published_by: number;
}

export interface EmployeeHours {
  employee_id: number;
  name: string;
  total_hours: number;
  exceeds_limit: boolean;
}

/* ── API Methods ─────────────────────────────────────────── */

export const shiftsApi = {
  /* Shift Templates */
  listTemplates: () =>
    apiClient.get<{ templates: ShiftTemplate[] }>("/shifts/templates"),

  createTemplate: (data: Partial<ShiftTemplate>) =>
    apiClient.post<{ template: ShiftTemplate }>("/shifts/templates", data),

  updateTemplate: (id: number, data: Partial<ShiftTemplate>) =>
    apiClient.patch<{ message: string }>(`/shifts/templates/${id}`, data),

  /* Schedule */
  getSchedule: (weekStart: string, department?: string) => {
    const params: Record<string, string> = { week_start: weekStart };
    if (department) params.department = department;
    return apiClient.get<{ assignments: ShiftAssignment[] }>(
      "/shifts/schedule",
      params,
    );
  },

  /* Assignments */
  createAssignment: (data: {
    employee_id: number;
    shift_template_id: number;
    date: string;
    notes?: string;
  }) =>
    apiClient.post<{ assignment: ShiftAssignment }>(
      "/shifts/assignments",
      data,
    ),

  updateAssignment: (id: number, data: Partial<ShiftAssignment>) =>
    apiClient.patch<{ message: string }>(`/shifts/assignments/${id}`, data),

  deleteAssignment: (id: number) =>
    apiClient.delete<{ message: string }>(`/shifts/assignments/${id}`),

  /* Publishing */
  publishSchedule: (weekStart: string) =>
    apiClient.post<{ message: string }>("/shifts/publish", {
      week_start: weekStart,
    }),

  /* Employee views */
  mySchedule: (weekStart: string) =>
    apiClient.get<{ assignments: ShiftAssignment[] }>("/shifts/my-schedule", {
      week_start: weekStart,
    }),

  /* Availability */
  getAvailability: (date: string) =>
    apiClient.get<{ available: Array<{ id: number; name: string }> }>(
      "/shifts/availability",
      { date },
    ),

  /* Hours tracking */
  getHours: (weekStart: string) =>
    apiClient.get<{ employees: EmployeeHours[] }>("/shifts/hours", {
      week_start: weekStart,
    }),
};
