/* ── Advisory History Hook ────────────────────────────────── */
/* Manages conversation list, selection, deletion, and rename  */
/* using @tanstack/react-query for server state.               */

"use client";

import { useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { advisoryApi } from "@/services/api/advisory";
import type {
  ConversationListResponse,
  AdvisoryHistoryResponse,
  ConversationDeleteResponse,
  ConversationRenameResponse,
} from "@/types/api";

/* ── Query Keys ──────────────────────────────────────────── */

export const conversationKeys = {
  all: ["conversations"] as const,
  list: () => [...conversationKeys.all, "list"] as const,
  history: (id: number) => [...conversationKeys.all, "history", id] as const,
};

/* ── Hook: Conversations List ────────────────────────────── */

export function useConversationList() {
  return useQuery<ConversationListResponse, Error>({
    queryKey: conversationKeys.list(),
    queryFn: () => advisoryApi.listConversations(),
    refetchInterval: 30_000,
  });
}

/* ── Hook: Conversation Messages ─────────────────────────── */

export function useConversationMessages(conversationId: number | null) {
  return useQuery<AdvisoryHistoryResponse, Error>({
    queryKey: conversationKeys.history(conversationId ?? 0),
    queryFn: () => advisoryApi.getHistory(conversationId!),
    enabled: conversationId !== null && conversationId > 0,
  });
}

/* ── Hook: Delete Conversation ───────────────────────────── */

export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation<
    ConversationDeleteResponse,
    Error,
    number,
    { previous: ConversationListResponse | undefined }
  >({
    mutationFn: (conversationId) =>
      advisoryApi.deleteConversation(conversationId),
    onMutate: async (conversationId) => {
      // Optimistically remove from cache immediately (don't wait for refetch)
      await queryClient.cancelQueries({
        queryKey: conversationKeys.list(),
      });
      const previous = queryClient.getQueryData<ConversationListResponse>(
        conversationKeys.list(),
      );
      if (previous) {
        queryClient.setQueryData<ConversationListResponse>(
          conversationKeys.list(),
          {
            ...previous,
            conversations: previous.conversations.filter(
              (c) => c.id !== conversationId,
            ),
          },
        );
      }
      return { previous };
    },
    onError: (_err, _conversationId, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(conversationKeys.list(), context.previous);
      }
    },
    onSettled: (_data, _error, conversationId) => {
      queryClient.invalidateQueries({
        queryKey: conversationKeys.list(),
      });
      queryClient.removeQueries({
        queryKey: conversationKeys.history(conversationId),
      });
    },
  });
}

/* ── Hook: Rename Conversation ───────────────────────────── */

export function useRenameConversation() {
  const queryClient = useQueryClient();

  return useMutation<
    ConversationRenameResponse,
    Error,
    { conversationId: number; title: string }
  >({
    mutationFn: ({ conversationId, title }) =>
      advisoryApi.renameConversation(conversationId, title),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: conversationKeys.list(),
      });
    },
  });
}

/* ── Combined Hook ───────────────────────────────────────── */
/* Provides all conversation management functions together.   */

// Legacy-fallback phrases anchored at the start of a turn. Must stay
// in sync with the backend persistence filter
// (src/hr_advisory/agents/memory/short_term.py::_LEGACY_FALLBACK_PATTERNS)
// and the purge script (scripts/maintenance/purge_legacy_advisory.py).
// Round-3 + P5-AD-1 ensure new rows don't land here; this filter is
// defence-in-depth for any rows that escaped the backend gate.
const LEGACY_FALLBACK_PHRASES = [
  "I'm having trouble processing your question",
  "I was unable to fully process your query",
] as const;

function isLegacyFallback(text: string | null | undefined): boolean {
  if (!text) return false;
  return LEGACY_FALLBACK_PHRASES.some((phrase) => text.includes(phrase));
}

export function useAdvisoryHistory(activeConversationId: number | null) {
  const listQuery = useConversationList();
  const messagesQuery = useConversationMessages(activeConversationId);
  const deleteMutation = useDeleteConversation();
  const renameMutation = useRenameConversation();
  const queryClient = useQueryClient();

  const refreshConversations = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: conversationKeys.list(),
    });
  }, [queryClient]);

  // Red-team P5-AD-1: drop conversations whose preview is a legacy
  // guardrail-fallback string. Earlier rounds replaced the text with
  // "(earlier reply unavailable)" but the buyer still saw N orphan
  // entries in the sidebar. Hiding them is correct — the prod DB
  // purge (scripts/maintenance/purge_legacy_advisory.py) deletes the
  // underlying rows, and the backend persistence filter blocks new
  // ones from landing in the first place.
  const allConversations = listQuery.data?.conversations ?? [];
  const visibleConversations = allConversations.filter(
    (c) => !isLegacyFallback(c.last_message),
  );

  // Filter assistant turns whose body contains the fallback phrase,
  // plus any stranded user turn left immediately before such a
  // fallback. Defence-in-depth for any single-message slice still
  // lurking in a conversation we kept.
  const rawMessages = messagesQuery.data?.messages ?? [];
  const cleanedMessages = (() => {
    const filtered: typeof rawMessages = [];
    for (const msg of rawMessages) {
      const isFallback =
        msg.role === "assistant" && isLegacyFallback(msg.content);
      if (isFallback) {
        // Drop the user turn that triggered the failed response, if
        // it is the most recent thing we've kept. Otherwise leave
        // history structurally intact.
        if (
          filtered.length > 0 &&
          filtered[filtered.length - 1].role === "user"
        ) {
          filtered.pop();
        }
        continue;
      }
      filtered.push(msg);
    }
    return filtered;
  })();

  return {
    /** Conversation list data and status (legacy-fallback rows hidden) */
    conversations: visibleConversations,
    conversationsLoading: listQuery.isLoading,
    conversationsError: listQuery.error,

    /** Selected conversation messages */
    messages: cleanedMessages,
    messagesLoading: messagesQuery.isLoading,
    messagesError: messagesQuery.error,
    refetchMessages: messagesQuery.refetch,

    /** Mutations */
    deleteConversation: deleteMutation.mutateAsync,
    deleteLoading: deleteMutation.isPending,

    renameConversation: renameMutation.mutateAsync,
    renameLoading: renameMutation.isPending,

    /** Manual refresh — invalidates the conversations cache so the
     * sidebar reflects new server state immediately. Call this on
     * any mutation path where the cache could go stale (e.g. SSE
     * error during streaming, manual import). */
    refreshConversations,
  };
}
