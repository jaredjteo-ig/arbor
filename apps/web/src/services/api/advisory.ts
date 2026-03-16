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
  ConversationListResponse,
  ConversationDeleteResponse,
  ConversationRenameResponse,
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
    callbacks: SSECallbacks<
      AdvisoryStreamStartEvent,
      AdvisoryStreamCompleteEvent
    >,
  ): AbortController {
    return createSSEStream<
      AdvisoryStreamStartEvent,
      AdvisoryStreamCompleteEvent
    >("/advisory/stream", data, callbacks);
  },

  /** Retrieve conversation history for a given conversation. */
  getHistory(conversationId: number): Promise<AdvisoryHistoryResponse> {
    return apiClient.get<AdvisoryHistoryResponse>(
      `/advisory/history/${conversationId}`,
    );
  },

  /** List all conversations for the current user. */
  listConversations(): Promise<ConversationListResponse> {
    return apiClient.get<ConversationListResponse>("/advisory/conversations");
  },

  /** Delete a conversation by ID. */
  deleteConversation(
    conversationId: number,
  ): Promise<ConversationDeleteResponse> {
    return apiClient.delete<ConversationDeleteResponse>(
      `/advisory/conversations/${conversationId}`,
    );
  },

  /** Rename a conversation. */
  renameConversation(
    conversationId: number,
    title: string,
  ): Promise<ConversationRenameResponse> {
    return apiClient.patch<ConversationRenameResponse>(
      `/advisory/conversations/${conversationId}`,
      { title },
    );
  },
};
