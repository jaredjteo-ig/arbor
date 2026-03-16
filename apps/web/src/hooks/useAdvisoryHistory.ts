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

  return useMutation<ConversationDeleteResponse, Error, number>({
    mutationFn: (conversationId) =>
      advisoryApi.deleteConversation(conversationId),
    onSuccess: (_data, conversationId) => {
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

  return {
    /** Conversation list data and status */
    conversations: listQuery.data?.conversations ?? [],
    conversationsLoading: listQuery.isLoading,
    conversationsError: listQuery.error,

    /** Selected conversation messages */
    messages: messagesQuery.data?.messages ?? [],
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
