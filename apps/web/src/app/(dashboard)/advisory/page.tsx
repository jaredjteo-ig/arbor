"use client";

import { useState, useCallback, Suspense } from "react";
import { ChatContainer, ConversationSidebar } from "@/components/advisory";
import type { ConversationSummary } from "@/components/advisory";
import { LoadingState } from "@/components/design-system";
import { useAdvisoryHistory } from "@/hooks/useAdvisoryHistory";

/**
 * Advisory page -- full chat interface with conversation history sidebar.
 *
 * Layout: sidebar (collapsible, 288px) | chat area (flex-1)
 * The chat area uses ChatContainer which handles SSE streaming,
 * message rendering, and input management.
 *
 * Conversation history is loaded from the API via useAdvisoryHistory.
 */

function AdvisoryContent() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<
    number | null
  >(null);

  const {
    conversations,
    messages: loadedMessages,
    messagesLoading,
    messagesError,
    refetchMessages,
    deleteConversation,
    deleteLoading,
    renameConversation,
    renameLoading,
    refreshConversations,
  } = useAdvisoryHistory(activeConversationId);

  // Red-team P5-AD-1: the hook itself now filters legacy-fallback
  // conversations OUT (rather than substituting "(earlier reply
  // unavailable)" — which still left a buyer-visible orphan).
  // Combined with the backend persistence-boundary filter and the
  // prod DB purge script, these rows are gone end-to-end.
  const sidebarConversations: ConversationSummary[] = conversations.map(
    (c) => ({
      id: c.id,
      title: c.title,
      lastMessage: c.last_message ?? "",
      timestamp: c.timestamp,
      riskTier: c.risk_tier,
    }),
  );

  const handleNewConversation = useCallback(() => {
    setActiveConversationId(null);
  }, []);

  const handleConversationStart = useCallback(
    (id: number) => {
      setActiveConversationId(id);
      // Refresh the conversation list so the new conversation appears
      refreshConversations();
    },
    [refreshConversations],
  );

  const handleSelectConversation = useCallback((id: number) => {
    setActiveConversationId(id);
  }, []);

  const handleDeleteConversation = useCallback(
    (id: number) => {
      deleteConversation(id).then(() => {
        // If the deleted conversation was active, clear the chat
        if (activeConversationId === id) {
          setActiveConversationId(null);
        }
      });
    },
    [deleteConversation, activeConversationId],
  );

  const handleRenameConversation = useCallback(
    (id: number, title: string) => {
      renameConversation({ conversationId: id, title });
    },
    [renameConversation],
  );

  const handleRetryLoad = useCallback(() => {
    refetchMessages();
  }, [refetchMessages]);

  // Red-team P5-AD-2: when an SSE stream fails (network drop, budget
  // exceeded, rate limit), the conversations sidebar may have rendered
  // a row optimistically — invalidate so the next paint reflects the
  // canonical server state.
  const handleStreamError = useCallback(() => {
    refreshConversations();
  }, [refreshConversations]);

  return (
    <div className="flex h-[calc(100dvh-56px)]">
      {/* Conversation history sidebar */}
      <ConversationSidebar
        conversations={sidebarConversations}
        activeId={activeConversationId}
        onSelect={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDelete={handleDeleteConversation}
        onRename={handleRenameConversation}
        deleteLoading={deleteLoading}
        renameLoading={renameLoading}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        className="hidden md:flex"
      />

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatContainer
          conversationId={activeConversationId}
          onConversationStart={handleConversationStart}
          loadedMessages={loadedMessages}
          messagesLoading={messagesLoading}
          messagesError={messagesError}
          onRetryLoad={handleRetryLoad}
          onStreamError={handleStreamError}
        />
      </div>
    </div>
  );
}

export default function AdvisoryPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-[calc(100dvh-56px)]">
          <LoadingState variant="chat" count={3} />
        </div>
      }
    >
      <AdvisoryContent />
    </Suspense>
  );
}
