/* ── Exit Interviews API Service ─────────────────────────── */

import { apiClient } from "./client";

export interface ExitInterview {
  id: number;
  company_id: number;
  employee_id: number;
  triggered_at: string;
  triggered_by_event_id: number;
  survey_payload: string;
  themes: string;
  is_anonymous: boolean;
  submitted_at: string | null;
  is_archived: boolean;
}

export interface ThemeRow {
  theme: string;
  count: number;
}

export const exitInterviewsApi = {
  list: () =>
    apiClient.get<{ interviews: ExitInterview[]; count: number }>(
      "/exit-interviews",
    ),
  trigger: (data: {
    employee_id: number;
    is_anonymous?: boolean;
    event_id?: number;
  }) =>
    apiClient.post<{ interview: ExitInterview; submit_token: string }>(
      "/exit-interviews/trigger",
      data,
    ),
  themes: (since?: string) => {
    const qs = since ? `?since=${since}` : "";
    return apiClient.get<{
      tally: ThemeRow[];
      submitted_count: number;
      total_triggered: number;
      response_rate: number;
    }>(`/exit-interviews/themes${qs}`);
  },
};
