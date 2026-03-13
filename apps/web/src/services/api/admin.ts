/* ── Admin API Service ────────────────────────────────────── */

import { apiClient } from "./client";
import type {
  PlatformMetricsResponse,
  QueryPatternsResponse,
  FeedbackSummaryResponse,
  MonthlyReportResponse,
  RegulatoryUpdateResponse,
  CreateUpdateRequest,
  ReviewRequest,
  StalenessSummaryResponse,
  KbGapsResponse,
  LearningRecommendationsResponse,
} from "@/types/api";

export const adminApi = {
  /* ── Metrics ─────────────────────────────────────────────── */

  /** Fetch platform-wide metrics for the admin dashboard. */
  metrics(): Promise<PlatformMetricsResponse> {
    return apiClient.get<PlatformMetricsResponse>("/admin/metrics");
  },

  /* ── Regulatory Updates ──────────────────────────────────── */

  /** List all regulatory updates, optionally filtered by status. */
  listUpdates(status?: string): Promise<RegulatoryUpdateResponse[]> {
    const params = status ? { status } : undefined;
    return apiClient.get<RegulatoryUpdateResponse[]>("/admin/updates", params);
  },

  /** Create a new regulatory update (draft). */
  createUpdate(data: CreateUpdateRequest): Promise<RegulatoryUpdateResponse> {
    return apiClient.post<RegulatoryUpdateResponse>("/admin/updates", data);
  },

  /** Submit a draft update for review. */
  submitForReview(updateId: string): Promise<RegulatoryUpdateResponse> {
    return apiClient.post<RegulatoryUpdateResponse>(
      `/admin/updates/${updateId}/submit`,
    );
  },

  /** Approve an in-review update. */
  approveUpdate(
    updateId: string,
    data: ReviewRequest,
  ): Promise<RegulatoryUpdateResponse> {
    return apiClient.post<RegulatoryUpdateResponse>(
      `/admin/updates/${updateId}/approve`,
      data,
    );
  },

  /** Reject an in-review update. */
  rejectUpdate(
    updateId: string,
    data: ReviewRequest,
  ): Promise<RegulatoryUpdateResponse> {
    return apiClient.post<RegulatoryUpdateResponse>(
      `/admin/updates/${updateId}/reject`,
      data,
    );
  },

  /** Publish an approved update. */
  publishUpdate(updateId: string): Promise<RegulatoryUpdateResponse> {
    return apiClient.post<RegulatoryUpdateResponse>(
      `/admin/updates/${updateId}/publish`,
    );
  },

  /* ── Staleness ───────────────────────────────────────────── */

  /** Get a summary of provision staleness status. */
  stalenessSummary(): Promise<StalenessSummaryResponse> {
    return apiClient.get<StalenessSummaryResponse>("/admin/staleness/summary");
  },

  /* ── Learning Pipeline (Admin) ───────────────────────────── */

  /** List tracked query patterns sorted by frequency. */
  queryPatterns(): Promise<QueryPatternsResponse> {
    return apiClient.get<QueryPatternsResponse>("/learning/admin/patterns");
  },

  /** Get a summary of all recorded feedback. */
  feedbackSummary(): Promise<FeedbackSummaryResponse> {
    return apiClient.get<FeedbackSummaryResponse>("/learning/admin/feedback");
  },

  /** Get the latest monthly learning pipeline report. */
  monthlyReport(): Promise<MonthlyReportResponse> {
    return apiClient.get<MonthlyReportResponse>("/learning/admin/report");
  },

  /** List detected KB gaps (admin view with suggested provisions). */
  kbGaps(priority?: string): Promise<KbGapsResponse> {
    const params = priority ? { priority } : undefined;
    return apiClient.get<KbGapsResponse>("/learning/admin/gaps", params);
  },

  /** List improvement recommendations from the learning pipeline. */
  recommendations(status?: string): Promise<LearningRecommendationsResponse> {
    const params = status ? { status } : undefined;
    return apiClient.get<LearningRecommendationsResponse>(
      "/learning/admin/recommendations",
      params,
    );
  },
};
