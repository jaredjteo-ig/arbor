/* ── Engagement Surveys API Service ────────────────────────── */
/* Round-3 product revision: in-app only at v1 (no public route). */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export type AnonymityTier = "identified" | "pseudonymous" | "anonymous";
export type Methodology =
  | "custom"
  | "gallup_q12"
  | "trust_index"
  | "pulse"
  | "enps";

export type QuestionType =
  | "likert5"
  | "single"
  | "multi"
  | "short_text"
  | "long_text"
  | "enps";

export interface SurveyQuestion {
  id: string;
  text: string;
  type: QuestionType;
  is_required?: boolean;
  options?: string[];
  max_length?: number;
}

export interface SurveySection {
  title: string;
  questions: SurveyQuestion[];
}

export interface EngagementTemplate {
  id: number;
  company_id: number;
  name: string;
  description: string;
  methodology: Methodology;
  sections: string; // JSON-encoded SurveySection[]
  is_archived: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface EngagementCohortRow {
  id: number;
  company_id: number;
  name: string;
  description: string;
  filter_spec: string; // JSON
  is_archived: boolean;
  created_at?: string;
}

export interface CohortFilterSpec {
  all_active?: boolean;
  departments?: string[];
  designations_like?: string[];
  pass_types?: string[];
  tenure_min_days?: number;
  tenure_max_days?: number;
  manager_ids?: number[];
  ad_hoc_employee_ids?: number[];
}

export interface CohortPreviewWarning {
  kind: "anonymity_unsafe" | "overlap_active_survey";
  message: string;
  min_cohort_size?: number;
  matched_count?: number;
  survey_id?: number;
  survey_name?: string;
  overlap_count?: number;
}

export interface CohortPreviewResponse {
  matched_count: number;
  sample_names: string[];
  anonymity_safe: boolean;
  warnings: CohortPreviewWarning[];
}

export interface EngagementSurvey {
  id: number;
  company_id: number;
  template_id: number;
  template_sections_snapshot: string;
  cohort_id: number;
  cohort_filter_spec: string;
  name: string;
  anonymity_tier: AnonymityTier;
  schedule_id: number;
  launched_at?: string | null;
  closes_at?: string | null;
  closed_at?: string | null;
  target_count: number;
  voided_count: number;
  consent_notice_version: string;
  email_delivery_status: string;
  is_archived: boolean;
  created_at?: string;
  /* Derived fields (Z07 — added by router enrich) */
  response_count?: number;
  response_rate?: number;
}

export interface EngagementResponseRow {
  id: number;
  survey_id: number;
  employee_id: number;
  employee_pseudonym: string;
  employee_name?: string;
  employee_email?: string;
  pseudonym_version: number;
  themes: string;
  enps_score: number | null;
  submitted_at: string | null;
  is_void: boolean;
}

/* ── Aggregator + Trend ──────────────────────────────────── */

export interface ByQuestionRow {
  question_id: string;
  n: number;
  is_anonymity_safe: boolean;
  avg?: number | null;
  distribution?: Record<string, number>;
}

export interface ByCohortRow {
  label: string;
  axis: string;
  value: string;
  n: number;
  is_anonymity_safe: boolean;
  avg_likert?: number | null;
  themes?: { theme: string; count: number }[];
}

export interface AggregateResponse {
  submitted_count: number;
  is_anonymity_safe: boolean;
  overall_avg_likert: number | null;
  by_question: ByQuestionRow[];
  by_cohort: ByCohortRow[];
  themes_tally: { theme: string; count: number }[];
  enps_score: number | null;
}

export interface TrendPoint {
  survey_id: number;
  closed_at: string;
  name: string;
  avg_likert: number | null;
  enps: number | null;
  n: number;
  is_anonymity_safe: boolean;
}

export interface TrendResponse {
  cohort_label: string;
  window: number;
  points: TrendPoint[];
}

/* ── Manager + actions + loop-closing ────────────────────── */

export interface TeamAggregate {
  is_visible: boolean;
  /** D1 — when true, only themes are populated (n=3-4 themes-only mode). */
  is_limited?: boolean;
  scope_size?: number;
  n?: number;
  reason?: string;
  message?: string;
  survey_id?: number;
  survey_name?: string;
  avg_likert?: number | null;
  enps_score?: number | null;
  themes?: { theme: string; count: number }[];
  /** Per-question avg breakdown (n>=5 only). Sorted ascending — lowest first. */
  by_question?: {
    question_id: string;
    question_text: string;
    n: number;
    avg: number;
  }[];
  /** 6-pulse mini trend for the manager's scope, oldest → newest. */
  trend?: {
    survey_id: number;
    survey_name: string;
    closed_at: string | null;
    n: number;
    avg_likert: number | null;
  }[];
}

export interface SuggestedActionsResponse {
  cohort_label?: string;
  theme?: string;
  score?: number | null;
  suggestions?: { text: string; source: "deterministic" | "llm" }[];
  source?: string;
  reason?: string;
}

export interface EngagementAction {
  id: number;
  company_id: number;
  survey_id: number;
  cohort_label: string;
  finding_summary: string;
  suggested_action_text: string;
  status: "proposed" | "accepted" | "rejected" | "done";
  linked_goal_id: number;
  next_pulse_question: string;
  next_pulse_survey_id: number;
  resolved_at?: string | null;
  resolved_score_delta?: number | null;
  created_by: number;
  created_at?: string;
}

/**
 * D3 (red-team Phase 2) — 3-state loop closing.
 *  "action_taken"  → action_payload populated; show "HR did Y"
 *  "under_review"  → HR has opened the survey detail; copy "HR is reviewing"
 *  "notified"      → no admin view yet; copy "HR has been notified"
 */
export type LoopClosingStatus = "action_taken" | "under_review" | "notified";

export interface LoopClosingPayload {
  last_pulse_closed_at: string;
  top_theme: string;
  status: LoopClosingStatus;
  action_taken: {
    headline: string;
    linked_goal_label: string;
  } | null;
  next_pulse_anchored_question: string;
}

/* ── Pending / history (employee) ─────────────────────────── */

export interface PendingResponse {
  response_id: number;
  survey_id: number;
  survey_name: string;
  anonymity_tier: AnonymityTier;
  closes_at: string | null;
}

export interface HistoryEntry {
  response_id: number;
  survey_id: number;
  survey_name: string;
  anonymity_tier: AnonymityTier;
  submitted_at: string | null;
  themes?: string;
}

export interface RenderResponse {
  response_id: number;
  survey_id: number;
  survey_name: string;
  anonymity_tier: AnonymityTier;
  consent_notice_version: string;
  template_sections_snapshot: string;
}

/* ── API surface ──────────────────────────────────────────── */

export const engagementApi = {
  /* Templates */
  listTemplates: () =>
    apiClient.get<{ templates: EngagementTemplate[]; count: number }>(
      "/engagement-surveys/templates",
    ),
  getTemplate: (id: number) =>
    apiClient.get<{ template: EngagementTemplate }>(
      `/engagement-surveys/templates/${id}`,
    ),
  createTemplate: (data: Partial<EngagementTemplate>) =>
    apiClient.post<{ template: EngagementTemplate }>(
      "/engagement-surveys/templates",
      data,
    ),
  cloneTemplate: (sourceId: number, overrides: Partial<EngagementTemplate>) =>
    apiClient.post<{ template: EngagementTemplate }>(
      `/engagement-surveys/templates?clone_from=${sourceId}`,
      overrides,
    ),
  updateTemplate: (id: number, data: Partial<EngagementTemplate>) =>
    apiClient.patch<{ template: EngagementTemplate }>(
      `/engagement-surveys/templates/${id}`,
      data,
    ),
  archiveTemplate: (id: number) =>
    apiClient.delete<{ detail: string }>(`/engagement-surveys/templates/${id}`),

  /* Cohorts */
  listCohorts: () =>
    apiClient.get<{ cohorts: EngagementCohortRow[]; count: number }>(
      "/engagement-surveys/cohorts",
    ),
  createCohort: (data: {
    name: string;
    description?: string;
    filter_spec: CohortFilterSpec;
  }) =>
    apiClient.post<{ cohort: EngagementCohortRow }>(
      "/engagement-surveys/cohorts",
      data,
    ),
  updateCohort: (
    id: number,
    data: Partial<{
      name: string;
      description: string;
      filter_spec: CohortFilterSpec;
      is_archived: boolean;
    }>,
  ) =>
    apiClient.patch<{ cohort: EngagementCohortRow }>(
      `/engagement-surveys/cohorts/${id}`,
      data,
    ),
  archiveCohort: (id: number) =>
    apiClient.delete<{ detail: string }>(`/engagement-surveys/cohorts/${id}`),
  previewCohort: (data: {
    filter_spec: CohortFilterSpec;
    anonymity_tier?: AnonymityTier;
  }) =>
    apiClient.post<CohortPreviewResponse>(
      "/engagement-surveys/cohorts/preview",
      data,
    ),

  /* Surveys */
  listSurveys: () =>
    apiClient.get<{ surveys: EngagementSurvey[]; count: number }>(
      "/engagement-surveys/surveys",
    ),
  getSurvey: (id: number) =>
    apiClient.get<{ survey: EngagementSurvey }>(
      `/engagement-surveys/surveys/${id}`,
    ),
  listResponses: (surveyId: number) =>
    apiClient.get<{
      responses: EngagementResponseRow[];
      count: number;
      anonymity_tier: AnonymityTier;
    }>(`/engagement-surveys/surveys/${surveyId}/responses`),
  closeSurvey: (surveyId: number) =>
    apiClient.post<{
      ok: boolean;
      closed_at?: string;
      already_closed?: boolean;
    }>(`/engagement-surveys/surveys/${surveyId}/close`, {}),
  launchSurvey: (data: {
    template_id: number;
    cohort_id?: number;
    cohort_filter_spec?: CohortFilterSpec;
    name: string;
    anonymity_tier: AnonymityTier;
    closes_at: string;
    consent_notice_text?: string;
    force_overlap_acknowledged?: boolean;
    force_anonymity_acknowledged?: boolean;
  }) =>
    apiClient.post<
      | { ok: true; survey_id: number; target_count: number }
      | {
          ok: false;
          warnings: CohortPreviewWarning[];
          can_proceed: boolean;
        }
    >("/engagement-surveys/surveys/launch", data),

  /* Aggregate + trend */
  getAggregate: (surveyId: number, cohort = "all") =>
    apiClient.get<AggregateResponse>(
      `/engagement-surveys/surveys/${surveyId}/aggregate?cohort=${encodeURIComponent(
        cohort,
      )}`,
    ),
  getTrend: (cohort = "all", window = 6) =>
    apiClient.get<TrendResponse>(
      `/engagement-surveys/surveys/trend?cohort=${encodeURIComponent(
        cohort,
      )}&window=${window}`,
    ),

  /* Manager view */
  getTeamAggregate: (surveyId?: number) =>
    apiClient.get<TeamAggregate>(
      `/engagement-surveys/team/aggregate${surveyId ? `?survey_id=${surveyId}` : ""}`,
    ),

  /* Suggested actions + actions CRUD */
  getSuggestedActions: (surveyId: number) =>
    apiClient.get<SuggestedActionsResponse>(
      `/engagement-surveys/surveys/${surveyId}/suggested-actions`,
    ),
  createAction: (
    surveyId: number,
    data: {
      cohort_label?: string;
      finding_summary?: string;
      suggested_action_text: string;
      /* D4: explicit theme tag (growth/manager/comp/...) so the
         loop-closing card lookup is exact-match instead of substring. */
      theme?: string;
      next_pulse_question?: string;
      status?: "proposed" | "accepted" | "rejected";
      create_linked_goal?: boolean;
      goal_title?: string;
    },
  ) =>
    apiClient.post<{ action: EngagementAction }>(
      `/engagement-surveys/surveys/${surveyId}/actions`,
      data,
    ),
  updateAction: (
    id: number,
    data: Partial<{
      status: "proposed" | "accepted" | "rejected" | "done";
      suggested_action_text: string;
      linked_goal_id: number;
      next_pulse_question: string;
      next_pulse_survey_id: number;
    }>,
  ) =>
    apiClient.patch<{ action: EngagementAction }>(
      `/engagement-surveys/actions/${id}`,
      data,
    ),
  listActions: (surveyId?: number) =>
    apiClient.get<{ actions: EngagementAction[]; count: number }>(
      `/engagement-surveys/actions${surveyId ? `?survey_id=${surveyId}` : ""}`,
    ),

  /* Employee endpoints */
  myPending: () =>
    apiClient.get<{ pending: PendingResponse[]; count: number }>(
      "/engagement-surveys/my-pending",
    ),
  myHistory: () =>
    apiClient.get<{ history: HistoryEntry[]; count: number }>(
      "/engagement-surveys/my-history",
    ),
  myLoopClosing: () =>
    apiClient.get<{ payload: LoopClosingPayload | null }>(
      "/engagement-surveys/my-loop-closing",
    ),
  renderMyResponse: (responseId: number) =>
    apiClient.get<RenderResponse>(
      `/engagement-surveys/my-responses/${responseId}/render`,
    ),
  submitMyResponse: (responseId: number, payload: Record<string, unknown>) =>
    /* Server derives an idempotency key from sha256(response_id + payload)
       when no explicit header is sent (Z08). Adding a custom header
       requires extending apiClient — deferred. */
    apiClient.post<{
      ok: boolean;
      themes: string[];
      idempotent_replay?: boolean;
    }>(`/engagement-surveys/my-responses/${responseId}/submit`, payload),
};

/* ── Helpers ──────────────────────────────────────────────── */

export function parseSections(raw: string | null | undefined): SurveySection[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as SurveySection[]) : [];
  } catch {
    return [];
  }
}

export function parseFilterSpec(
  raw: string | null | undefined,
): CohortFilterSpec {
  if (!raw) return {};
  try {
    return JSON.parse(raw) as CohortFilterSpec;
  } catch {
    return {};
  }
}

export function formatAnonymityTierLabel(tier: AnonymityTier): string {
  switch (tier) {
    case "identified":
      return "Names visible";
    case "pseudonymous":
      return "Pseudonymous";
    case "anonymous":
      return "Anonymous";
  }
}

export function describeAnonymityTier(
  tier: AnonymityTier,
  hasFreeText: boolean = false,
): string {
  const freeTextCaveat = hasFreeText
    ? " Free-text comments may still be readable to HR — keep them general if you want full privacy."
    : "";
  switch (tier) {
    case "identified":
      return "Your name will be visible to HR.";
    case "pseudonymous":
      return `Your name is hidden. Your responses across surveys can be tracked as a trend, but never traced back to you.${freeTextCaveat}`;
    case "anonymous":
      return `Your name is hidden. No trend tracking.${freeTextCaveat}`;
  }
}

export function templateHasFreeText(sections: SurveySection[]): boolean {
  return sections.some((s) =>
    (s.questions ?? []).some(
      (q) => q.type === "short_text" || q.type === "long_text",
    ),
  );
}
