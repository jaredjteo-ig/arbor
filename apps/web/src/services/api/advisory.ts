/* ── Advisory API Service ─────────────────────────────────── */

import { apiClient } from "./client";
import { createSSEStream, type SSECallbacks } from "./sse";
import type {
  AdvisoryQueryRequest,
  AdvisoryQueryResponse,
  AdvisoryStreamRequest,
  AdvisoryStreamStartEvent,
  AdvisoryStreamCompleteEvent,
  AdvisoryHistoryResponse,
} from "@/types/api";

export const advisoryApi = {
  /** Submit a regulatory advisory query (non-streaming). */
  query(data: AdvisoryQueryRequest): Promise<AdvisoryQueryResponse> {
    return apiClient.post<AdvisoryQueryResponse>("/advisory/query", data);
  },

  /**
   * Open a streaming advisory query via SSE.
   * Returns an AbortController to cancel the stream.
   */
  stream(
    data: AdvisoryStreamRequest,
    callbacks: SSECallbacks<AdvisoryStreamStartEvent, AdvisoryStreamCompleteEvent>,
  ): AbortController {
    return createSSEStream<AdvisoryStreamStartEvent, AdvisoryStreamCompleteEvent>(
      "/advisory/stream",
      data,
      callbacks,
    );
  },

  /** Retrieve conversation history for a given conversation. */
  getHistory(conversationId: number): Promise<AdvisoryHistoryResponse> {
    return apiClient.get<AdvisoryHistoryResponse>(
      `/advisory/history/${conversationId}`,
    );
  },
};
