/* ── Projects API Service ─────────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface Project {
  id: number;
  company_id: number;
  name: string;
  code: string;
  description: string;
  status: "active" | "completed" | "on_hold" | "archived";
  start_date: string;
  end_date: string;
  budget: number;
  actual_cost: number;
  client_name: string;
  manager_id: number;
  manager_name?: string;
  assignment_count?: number;
}

export interface ProjectAssignment {
  id: number;
  project_id: number;
  employee_id: number;
  employee_name?: string;
  role: string;
  start_date: string;
  end_date: string;
  allocation_pct: number;
  hourly_rate: number;
  is_active: boolean;
}

export interface ProjectRole {
  id: number;
  project_id: number;
  name: string;
  default_hourly_rate: number;
}

export interface TimesheetEntry {
  id: number;
  project_id: number;
  employee_id: number;
  employee_name?: string;
  project_name?: string;
  entry_date: string;
  hours: number;
  description: string;
  status: "draft" | "submitted" | "approved" | "rejected";
  approved_by?: number;
}

export interface ProjectAllocation {
  id: number;
  project_id: number;
  employee_id: number;
  employee_name?: string;
  month: string;
  allocated_hours: number;
  actual_hours: number;
}

export interface ProjectCostSummary {
  project_id: number;
  total_budget: number;
  total_actual: number;
  total_timesheet_cost: number;
  total_overhead_cost: number;
  variance: number;
}

/* ── API ──────────────────────────────────────────────────── */

export const projectsApi = {
  /* Projects */
  listProjects: () =>
    apiClient.get<{ projects: Project[]; count: number }>("/projects"),
  getProject: (id: number) => apiClient.get<Project>(`/projects/${id}`),
  createProject: (data: Partial<Project>) =>
    apiClient.post<Project>("/projects", data),
  updateProject: (id: number, data: Partial<Project>) =>
    apiClient.put<Project>(`/projects/${id}`, data),

  /* Assignments */
  listAssignments: (projectId: number) =>
    apiClient.get<{ assignments: ProjectAssignment[]; count: number }>(
      `/projects/${projectId}/assignments`,
    ),
  createAssignment: (projectId: number, data: Partial<ProjectAssignment>) =>
    apiClient.post<ProjectAssignment>(
      `/projects/${projectId}/assignments`,
      data,
    ),
  removeAssignment: (projectId: number, assignmentId: number) =>
    apiClient.delete<{ message: string }>(
      `/projects/${projectId}/assignments/${assignmentId}`,
    ),

  /* Timesheets -- backend mounts at /projects/timesheets */
  listTimesheets: (params?: Record<string, string>) =>
    apiClient.get<{ entries: TimesheetEntry[]; count: number }>(
      "/projects/timesheets",
      params,
    ),
  createTimesheet: (data: Partial<TimesheetEntry>) =>
    apiClient.post<TimesheetEntry>("/projects/timesheets/entries", data),
  updateTimesheet: (id: number, data: Partial<TimesheetEntry>) =>
    apiClient.put<TimesheetEntry>(`/projects/timesheets/entries/${id}`, data),
  submitTimesheet: (id: number) =>
    apiClient.post<{ message: string }>(
      `/projects/timesheets/entries/${id}/submit`,
    ),
  approveTimesheet: (id: number) =>
    apiClient.post<{ message: string }>(
      `/projects/timesheets/entries/${id}/approve`,
    ),
  rejectTimesheet: (id: number, reason: string) =>
    apiClient.post<{ message: string }>(
      `/projects/timesheets/entries/${id}/reject`,
      { reason },
    ),

  /* My Timesheets (employee self-service) */
  listMyTimesheets: (params?: Record<string, string>) =>
    apiClient.get<{ entries: TimesheetEntry[]; count: number }>(
      "/projects/timesheets/me",
      params,
    ),

  /* Costs */
  getProjectCosts: (projectId: number) =>
    apiClient.get<ProjectCostSummary>(`/projects/${projectId}/costs`),

  /* Allocations */
  listAllocations: (projectId: number) =>
    apiClient.get<{ allocations: ProjectAllocation[]; count: number }>(
      `/projects/${projectId}/allocations`,
    ),
};
