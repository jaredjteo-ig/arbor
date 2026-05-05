/* ── Strategy / Lifecycle API Service ────────────────────── */
/*  Cox 8-stage Employee Lifecycle dashboard data layer.
    Backend: src/hr_advisory/api/routers/strategy.py
*/

import { apiClient } from "./client";

export type LifecycleStageKey =
  | "strategy"
  | "attract"
  | "recruit"
  | "onboard"
  | "lnd"
  | "reward"
  | "progression"
  | "retain";

export type HealthPill = "green" | "amber" | "red";

export interface StageHealth {
  health: HealthPill;
  kpi: Record<string, unknown>;
}

export interface LifecycleHero {
  headcount_actual: number;
  headcount_target: number;
  open_jobs: number;
  stale_jobs: number;
  critical_roles_at_risk: number;
  churn_ytd_pct: number;
  churn_yoy_delta: number;
}

export interface DiSnapshot {
  composition: {
    gender?: Record<string, number>;
    pass_type?: Record<string, number>;
  };
  completeness: Record<string, number>;
  headline: string;
}

export interface ActivityRow {
  stage: string;
  kind: string;
  ts: string | null;
  summary: string;
}

export interface LifecycleDashboardResponse {
  company_id: number;
  generated_at: string;
  hero: LifecycleHero;
  stages: Record<LifecycleStageKey, StageHealth>;
  di_snapshot: DiSnapshot;
  activity: ActivityRow[];
}

export const strategyApi = {
  /** Fetch the Cox 8-stage lifecycle dashboard payload (hero +
   *  per-stage pills + D&I + activity in one round-trip). */
  async getLifecycleDashboard(): Promise<LifecycleDashboardResponse> {
    return apiClient.get<LifecycleDashboardResponse>(
      "/strategy/lifecycle-dashboard",
    );
  },

  /** Mark the lifecycle-tour pop-over as dismissed for this company. */
  async dismissLifecycleTour(): Promise<{ ok: boolean }> {
    return apiClient.post<{ ok: boolean }>("/strategy/lifecycle-tour/dismiss");
  },
};
