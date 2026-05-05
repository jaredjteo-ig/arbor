/* ── Strategy depth API service (P3) ─────────────────────── */

import { apiClient } from "./client";

export interface WorkforcePlan {
  id: number;
  company_id: number;
  period_start: string;
  period_end: string;
  name: string;
  status: "draft" | "published" | "archived";
  headcount_targets: string;
  skills_priorities: string;
  retention_focus: string;
  narrative: string;
  created_by: number;
  approved_by: number;
}

export interface SkillEntry {
  id: number;
  employee_id: number;
  skill_name: string;
  proficiency: number;
  years_experience: number;
  last_used_date: string;
}

export interface SuccessionPlanRow {
  id: number;
  role_title: string;
  incumbent_employee_id: number;
  criticality: "low" | "medium" | "high";
  successors: string; // JSON
  notes: string;
}

export interface RetentionRow {
  employee_id: number;
  score: number;
  drivers: string[];
  recommendation: string;
}

export interface PayEquityBucket {
  bucket: string;
  count: number | "—";
  avg_salary: number | "—";
  gap_vs_overall_pct: number | "—";
}

export const strategyDepthApi = {
  // Plans
  listPlans: () =>
    apiClient.get<{ plans: WorkforcePlan[]; count: number }>(
      "/strategy/workforce-plan",
    ),
  createPlan: (data: Partial<WorkforcePlan>) =>
    apiClient.post<{ plan: WorkforcePlan }>("/strategy/workforce-plan", data),
  updatePlan: (id: number, data: Partial<WorkforcePlan>) =>
    apiClient.patch<{ plan: WorkforcePlan }>(
      `/strategy/workforce-plan/${id}`,
      data,
    ),
  // Skills
  listSkills: (employee_id?: number) => {
    const qs = employee_id !== undefined ? `?employee_id=${employee_id}` : "";
    return apiClient.get<{ skills: SkillEntry[]; count: number }>(
      `/strategy/skills${qs}`,
    );
  },
  skillsCoverage: () =>
    apiClient.get<{
      coverage: Array<{ skill: string; count: number }>;
      total_entries: number;
    }>("/strategy/skills/coverage"),
  createSkill: (data: Partial<SkillEntry>) =>
    apiClient.post<{ skill: SkillEntry }>("/strategy/skills", data),
  // Succession
  listSuccession: () =>
    apiClient.get<{ plans: SuccessionPlanRow[]; count: number }>(
      "/strategy/succession",
    ),
  createSuccession: (data: Partial<SuccessionPlanRow>) =>
    apiClient.post<{ plan: SuccessionPlanRow }>("/strategy/succession", data),
  // Retention risk
  retentionRisk: () =>
    apiClient.get<{
      rows: RetentionRow[];
      top_at_risk: RetentionRow[];
      headcount: number;
    }>("/strategy/retention-risk"),
  // Pay equity
  payEquity: () =>
    apiClient.get<{
      by_gender: PayEquityBucket[];
      by_pass_type: PayEquityBucket[];
      headcount: number;
      note: string;
    }>("/strategy/pay-equity"),
};
