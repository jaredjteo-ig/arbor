"use client";

import { apiClient } from "./client";

/* ── Types ───────────────────────────────────────────────── */

export interface TeamSizeResponse {
  team_size: number;
}

export interface PendingApprovalsTile {
  leave: number;
  claims: number;
  timesheets: number;
  total: number;
}

export interface TeamLeaveEntry {
  employee_id: number;
  employee_name: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  return_date: string;
}

export interface TeamMember {
  id: number;
  user_id: number;
  name: string;
  email: string;
  department: string;
  designation: string;
  employment_type: string;
  pass_type: string;
  confirmation_status: string;
  start_date: string;
  is_active: boolean;
}

export interface TeamDashboard {
  team_size: number;
  pending_approvals: PendingApprovalsTile;
  on_leave_today: TeamLeaveEntry[];
  upcoming_leave: TeamLeaveEntry[];
  team_members: TeamMember[];
}

/* ── API ─────────────────────────────────────────────────── */

export const teamApi = {
  /** Lightweight call used by the sidebar to decide visibility of
   *  the Team link. Returns 0 for callers with no direct reports. */
  async size(): Promise<TeamSizeResponse> {
    return apiClient.get<TeamSizeResponse>("/team/size");
  },

  /** Bundled dashboard data for the /team page. */
  async dashboard(): Promise<TeamDashboard> {
    return apiClient.get<TeamDashboard>("/team/dashboard");
  },

  /** Roster only, with an option to include inactive employees. */
  async members(
    activeOnly = true,
  ): Promise<{ members: TeamMember[]; count: number }> {
    return apiClient.get<{ members: TeamMember[]; count: number }>(
      `/team/members?active_only=${activeOnly}`,
    );
  },
};
