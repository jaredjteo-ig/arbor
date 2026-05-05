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

  // M6 redteam (round-12): the fallback "I'm having trouble processing
  // your question right now" message advertises a transient LLM/rate-limit
  // failure that has long since resolved. Surfacing it in past
  // conversations makes the platform look broken even when it isn't.
  // Filter assistant turns whose body contains the fallback phrase, plus
  // any stranded user turn left immediately before such a fallback.
  const FALLBACK_PHRASE = "I'm having trouble processing your question";
  const rawMessages = messagesQuery.data?.messages ?? [];
  const cleanedMessages = (() => {
    const filtered: typeof rawMessages = [];
    for (let i = 0; i < rawMessages.length; i++) {
      const msg = rawMessages[i];
      const isFallback =
        msg.role === "assistant" &&
        typeof msg.content === "string" &&
        msg.content.includes(FALLBACK_PHRASE);
      if (isFallback) {
        // Drop the user turn that triggered the failed response, if it
        // is the most recent thing we've kept. Otherwise leave history
        // structurally intact.
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
    /** Conversation list data and status */
    conversations: listQuery.data?.conversations ?? [],
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

    /** Manual refresh */
    refreshConversations,
  };
}
