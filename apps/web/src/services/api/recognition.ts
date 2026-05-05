/* ── Recognition API Service ─────────────────────────────── */
/*  P2-RC obayashi.                                            */

import { apiClient } from "./client";

export type RecognitionCategory =
  | "above_and_beyond"
  | "teamwork"
  | "customer"
  | "innovation"
  | "values";

export interface Recognition {
  id: number;
  company_id: number;
  from_user_id: number;
  to_employee_id: number;
  category: RecognitionCategory;
  message: string;
  is_public: boolean;
  is_archived: boolean;
  created_at: string;
}

export interface PeerNomination {
  id: number;
  company_id: number;
  nominator_user_id: number;
  nominee_employee_id: number;
  period: string;
  category: RecognitionCategory;
  rationale: string;
}

export const recognitionApi = {
  listCategories: () =>
    apiClient.get<{ categories: Array<{ key: string; label: string }> }>(
      "/recognition/categories",
    ),
  list: (scope: "public" | "received" = "public") =>
    apiClient.get<{ recognition: Recognition[]; count: number; scope: string }>(
      `/recognition?scope=${scope}`,
    ),
  feed: (days = 30) =>
    apiClient.get<{ feed: Recognition[]; count: number }>(
      `/recognition/feed?days=${days}`,
    ),
  received: () =>
    apiClient.get<{ recognition: Recognition[]; count: number }>(
      "/recognition/received",
    ),
  give: (data: {
    to_employee_id: number;
    category: RecognitionCategory;
    message: string;
    is_public?: boolean;
  }) => apiClient.post<{ recognition: Recognition }>("/recognition", data),
  nominate: (data: {
    nominee_employee_id: number;
    category: RecognitionCategory;
    rationale: string;
    period?: string;
  }) =>
    apiClient.post<{ nomination: PeerNomination }>(
      "/recognition/nominate",
      data,
    ),
  listNominations: (period?: string) => {
    const qs = period ? `?period=${period}` : "";
    return apiClient.get<{
      nominations: PeerNomination[];
      count: number;
      tally: Array<{ employee_id: number; count: number }>;
    }>(`/recognition/nominations${qs}`);
  },
};
