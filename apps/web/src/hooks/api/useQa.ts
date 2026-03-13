/* ── QA Sessions Hooks ────────────────────────────────────── */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qaApi } from "@/services/api/qa";
import type {
  CreateQASessionRequest,
  QASession,
  QASessionListResponse,
  QASessionConversationsResponse,
  SubmitEvaluationRequest,
  QAEvaluation,
  QAEvaluationListResponse,
  QAPatch,
  QAPatchListResponse,
  AdvisoryHistoryResponse,
} from "@/types/api";

/** Query keys for the QA domain. */
export const qaKeys = {
  all: ["qa"] as const,
  sessions: () => [...qaKeys.all, "sessions"] as const,
  sessionsList: (status?: string, page?: number) =>
    [...qaKeys.sessions(), "list", status ?? "all", page ?? 1] as const,
  session: (id: string) => [...qaKeys.sessions(), "detail", id] as const,
  sessionConversations: (id: string) =>
    [...qaKeys.sessions(), "conversations", id] as const,
  evaluations: () => [...qaKeys.all, "evaluations"] as const,
  evaluationsList: (sessionId?: number) =>
    [...qaKeys.evaluations(), "list", sessionId ?? "all"] as const,
  patches: () => [...qaKeys.all, "patches"] as const,
  patchesList: (status?: string) =>
    [...qaKeys.patches(), "list", status ?? "all"] as const,
  conversationHistory: (conversationId: number) =>
    [...qaKeys.all, "conversationHistory", conversationId] as const,
};

/* ── Session Queries ─────────────────────────────────────── */

/** List QA sessions with optional status filter and pagination. */
export function useQaSessions(
  status?: string,
  page?: number,
  pageSize?: number,
) {
  return useQuery<QASessionListResponse, Error>({
    queryKey: qaKeys.sessionsList(status, page),
    queryFn: () => qaApi.listSessions(status, page, pageSize),
  });
}

/** Fetch a single QA session by ID. */
export function useQaSession(sessionId: string) {
  return useQuery<QASession, Error>({
    queryKey: qaKeys.session(sessionId),
    queryFn: () => qaApi.getSession(sessionId),
    enabled: !!sessionId,
  });
}

/** Fetch conversations assigned to a QA session. */
export function useQaSessionConversations(sessionId: string) {
  return useQuery<QASessionConversationsResponse, Error>({
    queryKey: qaKeys.sessionConversations(sessionId),
    queryFn: () => qaApi.getSessionConversations(sessionId),
    enabled: !!sessionId,
  });
}

/* ── Evaluation Queries ──────────────────────────────────── */

/** List evaluations, optionally filtered by session ID. */
export function useQaEvaluations(sessionId?: number) {
  return useQuery<QAEvaluationListResponse, Error>({
    queryKey: qaKeys.evaluationsList(sessionId),
    queryFn: () => qaApi.listEvaluations(sessionId),
  });
}

/* ── Conversation History ─────────────────────────────────── */

/** Fetch conversation message history for a specific conversation. */
export function useConversationHistory(conversationId: number) {
  return useQuery<AdvisoryHistoryResponse, Error>({
    queryKey: qaKeys.conversationHistory(conversationId),
    queryFn: () => qaApi.getConversationHistory(conversationId),
    enabled: conversationId > 0,
  });
}

/* ── Patch Queries ───────────────────────────────────────── */

/** List instruction patches, optionally filtered by status. */
export function useQaPatches(status?: string) {
  return useQuery<QAPatchListResponse, Error>({
    queryKey: qaKeys.patchesList(status),
    queryFn: () => qaApi.listPatches(status),
  });
}

/* ── Session Mutations ───────────────────────────────────── */

/** Create a new QA review session. */
export function useCreateQaSession() {
  const queryClient = useQueryClient();

  return useMutation<QASession, Error, CreateQASessionRequest>({
    mutationFn: (data) => qaApi.createSession(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qaKeys.sessions() });
    },
  });
}

/** Complete a QA session (mark as completed). */
export function useCompleteSession() {
  const queryClient = useQueryClient();

  return useMutation<QASession, Error, string>({
    mutationFn: (sessionId) => qaApi.completeSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qaKeys.sessions() });
    },
  });
}

/* ── Evaluation Mutations ────────────────────────────────── */

/** Submit a turn-level QA evaluation. */
export function useSubmitEvaluation() {
  const queryClient = useQueryClient();

  return useMutation<QAEvaluation, Error, SubmitEvaluationRequest>({
    mutationFn: (data) => qaApi.submitEvaluation(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qaKeys.evaluations() });
      queryClient.invalidateQueries({ queryKey: qaKeys.patches() });
    },
  });
}

/* ── Patch Mutations ─────────────────────────────────────── */

/** Approve an instruction patch. */
export function useApprovePatch() {
  const queryClient = useQueryClient();

  return useMutation<QAPatch, Error, number>({
    mutationFn: (patchId) => qaApi.approvePatch(patchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qaKeys.patches() });
    },
  });
}

/** Reject an instruction patch. */
export function useRejectPatch() {
  const queryClient = useQueryClient();

  return useMutation<QAPatch, Error, number>({
    mutationFn: (patchId) => qaApi.rejectPatch(patchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qaKeys.patches() });
    },
  });
}
