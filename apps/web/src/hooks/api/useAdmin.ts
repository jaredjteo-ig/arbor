/* ── Admin Dashboard Hooks ────────────────────────────────── */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/services/api/admin";
import type {
  PlatformMetricsResponse,
  RegulatoryUpdateResponse,
  CreateUpdateRequest,
  ReviewRequest,
  StalenessSummaryResponse,
  FeedbackSummaryResponse,
  KbGapsResponse,
  LearningRecommendationsResponse,
} from "@/types/api";

/** Query keys for the admin domain. */
export const adminKeys = {
  all: ["admin"] as const,
  metrics: () => [...adminKeys.all, "metrics"] as const,
  updates: () => [...adminKeys.all, "updates"] as const,
  updatesList: (status?: string) =>
    [...adminKeys.updates(), "list", status ?? "all"] as const,
  staleness: () => [...adminKeys.all, "staleness"] as const,
  feedbackSummary: () => [...adminKeys.all, "feedbackSummary"] as const,
  kbGaps: (priority?: string) =>
    [...adminKeys.all, "kbGaps", priority ?? "all"] as const,
  recommendations: (status?: string) =>
    [...adminKeys.all, "recommendations", status ?? "all"] as const,
};

/* ── Queries ─────────────────────────────────────────────── */

/** Fetch platform-wide metrics for the admin overview. */
export function useAdminMetrics() {
  return useQuery<PlatformMetricsResponse, Error>({
    queryKey: adminKeys.metrics(),
    queryFn: () => adminApi.metrics(),
  });
}

/** List regulatory updates, optionally filtered by status. */
export function useRegulatoryUpdates(status?: string) {
  return useQuery<RegulatoryUpdateResponse[], Error>({
    queryKey: adminKeys.updatesList(status),
    queryFn: () => adminApi.listUpdates(status),
  });
}

/** Fetch staleness summary for KB provisions. */
export function useStalenessSummary() {
  return useQuery<StalenessSummaryResponse, Error>({
    queryKey: adminKeys.staleness(),
    queryFn: () => adminApi.stalenessSummary(),
  });
}

/** Fetch feedback summary from the learning pipeline. */
export function useAdminFeedbackSummary() {
  return useQuery<FeedbackSummaryResponse, Error>({
    queryKey: adminKeys.feedbackSummary(),
    queryFn: () => adminApi.feedbackSummary(),
  });
}

/** Fetch KB gaps detected by the learning pipeline. */
export function useAdminKbGaps(priority?: string) {
  return useQuery<KbGapsResponse, Error>({
    queryKey: adminKeys.kbGaps(priority),
    queryFn: () => adminApi.kbGaps(priority),
  });
}

/** Fetch improvement recommendations. */
export function useAdminRecommendations(status?: string) {
  return useQuery<LearningRecommendationsResponse, Error>({
    queryKey: adminKeys.recommendations(status),
    queryFn: () => adminApi.recommendations(status),
  });
}

/* ── Mutations ───────────────────────────────────────────── */

/** Create a new regulatory update (draft). */
export function useCreateUpdate() {
  const queryClient = useQueryClient();

  return useMutation<RegulatoryUpdateResponse, Error, CreateUpdateRequest>({
    mutationFn: (data) => adminApi.createUpdate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.updates() });
      queryClient.invalidateQueries({ queryKey: adminKeys.metrics() });
    },
  });
}

/** Submit a draft update for review. */
export function useSubmitForReview() {
  const queryClient = useQueryClient();

  return useMutation<RegulatoryUpdateResponse, Error, string>({
    mutationFn: (updateId) => adminApi.submitForReview(updateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.updates() });
      queryClient.invalidateQueries({ queryKey: adminKeys.metrics() });
    },
  });
}

/** Approve an in-review update. */
export function useApproveUpdate() {
  const queryClient = useQueryClient();

  return useMutation<
    RegulatoryUpdateResponse,
    Error,
    { updateId: string; data: ReviewRequest }
  >({
    mutationFn: ({ updateId, data }) => adminApi.approveUpdate(updateId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.updates() });
      queryClient.invalidateQueries({ queryKey: adminKeys.metrics() });
    },
  });
}

/** Reject an in-review update. */
export function useRejectUpdate() {
  const queryClient = useQueryClient();

  return useMutation<
    RegulatoryUpdateResponse,
    Error,
    { updateId: string; data: ReviewRequest }
  >({
    mutationFn: ({ updateId, data }) => adminApi.rejectUpdate(updateId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.updates() });
      queryClient.invalidateQueries({ queryKey: adminKeys.metrics() });
    },
  });
}

/** Publish an approved update. */
export function usePublishUpdate() {
  const queryClient = useQueryClient();

  return useMutation<RegulatoryUpdateResponse, Error, string>({
    mutationFn: (updateId) => adminApi.publishUpdate(updateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.updates() });
      queryClient.invalidateQueries({ queryKey: adminKeys.metrics() });
    },
  });
}
