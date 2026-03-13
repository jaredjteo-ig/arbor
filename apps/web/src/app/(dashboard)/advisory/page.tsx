"use client";

import { useState, useCallback, Suspense } from "react";
import {
  ChatContainer,
  ConversationSidebar,
} from "@/components/advisory";
import type { ConversationSummary } from "@/components/advisory";
import { LoadingState } from "@/components/design-system";

/**
 * Advisory page — full chat interface with conversation history sidebar.
 *
 * Layout: sidebar (collapsible, 288px) | chat area (flex-1)
 * The chat area uses ChatContainer which handles SSE streaming,
 * message rendering, and input management.
 */

// Placeholder conversations for demo — replaced by API data in production
const DEMO_CONVERSATIONS: ConversationSummary[] = [];

function AdvisoryContent() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<
    number | null
  >(null);
  const [conversations, setConversations] =
    useState<ConversationSummary[]>(DEMO_CONVERSATIONS);

  const handleNewConversation = useCallback(() => {
    setActiveConversationId(null);
  }, []);

  const handleConversationStart = useCallback(
    (id: number) => {
      setActiveConversationId(id);
      // Add to conversation list if not already present
      setConversations((prev) => {
        if (prev.some((c) => c.id === id)) return prev;
        return [
          {
            id,
            title: "New conversation",
            lastMessage: "",
            timestamp: new Date().toISOString(),
          },
          ...prev,
        ];
      });
    },
    [],
  );

  const handleSelectConversation = useCallback((id: number) => {
    setActiveConversationId(id);
    // In production: load conversation history via useAdvisoryHistory
  }, []);

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* Conversation history sidebar */}
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConversationId}
        onSelect={handleSelectConversation}
        onNewConversation={handleNewConversation}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        className="hidden md:flex"
      />

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatContainer
          conversationId={activeConversationId}
          onConversationStart={handleConversationStart}
        />
      </div>
    </div>
  );
}

export default function AdvisoryPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-[calc(100vh-64px)]">
          <LoadingState variant="chat" count={3} />
        </div>
      }
    >
      <AdvisoryContent />
    </Suspense>
  );
}
