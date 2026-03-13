/* ── Learning Pipeline API Service ────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface FeedbackSubmission {
  session_id: string;
  is_positive: boolean;
  category?: string;
  domains?: string[];
  query_snippet?: string;
}

export interface FeedbackResponse {
  feedback_id: string;
  recorded: boolean;
  timestamp: string;
}

/* ── API Methods ─────────────────────────────────────────── */

export const learningApi = {
  /** Submit feedback on an advisory response. */
  submitFeedback(data: FeedbackSubmission): Promise<FeedbackResponse> {
    return apiClient.post<FeedbackResponse>("/learning/feedback", data);
  },
};
