/* ── QA Sessions API Service ──────────────────────────────── */

import { apiClient } from "./client";
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

export const qaApi = {
  /* ── Sessions ──────────────────────────────────────────────── */

  /** Create a new QA review session with the given filters. */
  createSession(data: CreateQASessionRequest): Promise<QASession> {
    return apiClient.post<QASession>("/admin/qa/sessions", data);
  },

  /** List all QA sessions, optionally filtered by status. */
  listSessions(
    status?: string,
    page?: number,
    pageSize?: number,
  ): Promise<QASessionListResponse> {
    const params: Record<string, string> = {};
    if (status) params.status = status;
    if (page !== undefined) params.page = String(page);
    if (pageSize !== undefined) params.page_size = String(pageSize);
    return apiClient.get<QASessionListResponse>("/admin/qa/sessions", params);
  },

  /** Get details of a single QA session. */
  getSession(sessionId: string): Promise<QASession> {
    return apiClient.get<QASession>(`/admin/qa/sessions/${sessionId}`);
  },

  /** List conversations assigned to a QA session. */
  getSessionConversations(
    sessionId: string,
  ): Promise<QASessionConversationsResponse> {
    return apiClient.get<QASessionConversationsResponse>(
      `/admin/qa/sessions/${sessionId}/conversations`,
    );
  },

  /** Complete a QA session (mark as completed). */
  completeSession(sessionId: string): Promise<QASession> {
    return apiClient.post<QASession>(
      `/admin/qa/sessions/${sessionId}/complete`,
    );
  },

  /** Get conversation history for a specific conversation. */
  getConversationHistory(
    conversationId: number,
  ): Promise<AdvisoryHistoryResponse> {
    return apiClient.get<AdvisoryHistoryResponse>(
      `/advisory/history/${conversationId}`,
    );
  },

  /* ── Evaluations ───────────────────────────────────────────── */

  /** Submit a turn-level QA evaluation. */
  submitEvaluation(data: SubmitEvaluationRequest): Promise<QAEvaluation> {
    return apiClient.post<QAEvaluation>("/admin/qa/evaluations", data);
  },

  /** List evaluations, optionally filtered by session ID. */
  listEvaluations(sessionId?: number): Promise<QAEvaluationListResponse> {
    const params: Record<string, string> = {};
    if (sessionId !== undefined) params.session_id = String(sessionId);
    return apiClient.get<QAEvaluationListResponse>(
      "/admin/qa/evaluations",
      params,
    );
  },

  /* ── Patches ───────────────────────────────────────────────── */

  /** List instruction patches, optionally filtered by status. */
  listPatches(status?: string): Promise<QAPatchListResponse> {
    const params: Record<string, string> = {};
    if (status) params.status = status;
    return apiClient.get<QAPatchListResponse>("/admin/qa/patches", params);
  },

  /** Approve an instruction patch. */
  approvePatch(patchId: number): Promise<QAPatch> {
    return apiClient.post<QAPatch>(`/admin/qa/patches/${patchId}/approve`);
  },

  /** Reject an instruction patch. */
  rejectPatch(patchId: number): Promise<QAPatch> {
    return apiClient.post<QAPatch>(`/admin/qa/patches/${patchId}/reject`);
  },
};
