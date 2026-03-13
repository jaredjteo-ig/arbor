/* ── Advisory Hooks ───────────────────────────────────────── */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { advisoryApi } from "@/services/api/advisory";
import type {
  AdvisoryQueryRequest,
  AdvisoryQueryResponse,
  AdvisoryHistoryResponse,
} from "@/types/api";

/** Query keys for advisory domain. */
export const advisoryKeys = {
  all: ["advisory"] as const,
  history: (conversationId: number) =>
    [...advisoryKeys.all, "history", conversationId] as const,
};

/**
 * Submit a regulatory advisory query (non-streaming).
 * Returns a mutation that the caller triggers explicitly.
 */
export function useAdvisoryQuery() {
  const queryClient = useQueryClient();

  return useMutation<AdvisoryQueryResponse, Error, AdvisoryQueryRequest>({
    mutationFn: (data) => advisoryApi.query(data),
    onSuccess: (data) => {
      /* Invalidate conversation history so it re-fetches with the new message */
      queryClient.invalidateQueries({
        queryKey: advisoryKeys.history(data.conversation_id),
      });
    },
  });
}

/**
 * Fetch conversation history for a given conversation ID.
 * Only fetches when conversationId is provided (> 0).
 */
export function useAdvisoryHistory(conversationId: number) {
  return useQuery<AdvisoryHistoryResponse, Error>({
    queryKey: advisoryKeys.history(conversationId),
    queryFn: () => advisoryApi.getHistory(conversationId),
    enabled: conversationId > 0,
  });
}
