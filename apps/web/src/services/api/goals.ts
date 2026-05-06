/* ── Goals (OKR) API Service ─────────────────────────────── */

import { apiClient } from "./client";

export type GoalStatus = "draft" | "active" | "at_risk" | "done" | "cancelled";

export interface Goal {
  id: number;
  company_id: number;
  employee_id: number;
  manager_id: number;
  period_id: number;
  title: string;
  description: string;
  metric: string;
  target_value: string;
  start_date: string;
  due_date: string;
  status: GoalStatus;
  progress_pct: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface GoalCheckIn {
  id: number;
  goal_id: number;
  company_id: number;
  actor_user_id: number;
  actor_name?: string;
  progress_pct: number;
  note: string;
  created_at: string;
}

export const goalsApi = {
  list: (filters?: { employee_id?: number; status?: GoalStatus }) => {
    const qs = new URLSearchParams();
    if (filters?.employee_id !== undefined)
      qs.set("employee_id", String(filters.employee_id));
    if (filters?.status) qs.set("status", filters.status);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return apiClient.get<{ goals: Goal[]; count: number }>(`/goals${suffix}`);
  },
  create: (data: Partial<Goal>) =>
    apiClient.post<{ goal: Goal }>("/goals", data),
  get: (id: number) => apiClient.get<{ goal: Goal }>(`/goals/${id}`),
  update: (id: number, data: Partial<Goal>) =>
    apiClient.patch<{ goal: Goal }>(`/goals/${id}`, data),
  archive: (id: number) => apiClient.delete<{ id: number }>(`/goals/${id}`),
  listCheckins: (id: number) =>
    apiClient.get<{ checkins: GoalCheckIn[]; count: number }>(
      `/goals/${id}/checkins`,
    ),
  addCheckin: (id: number, data: { progress_pct: number; note?: string }) =>
    apiClient.post<{ checkin: GoalCheckIn }>(`/goals/${id}/checkins`, data),
};
