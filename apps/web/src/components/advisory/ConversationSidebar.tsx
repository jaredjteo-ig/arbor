"use client";

import { useState } from "react";
import clsx from "clsx";
import {
  MessageSquare,
  Search,
  Plus,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

export interface ConversationSummary {
  id: number;
  title: string;
  lastMessage: string;
  timestamp: string;
  riskTier?: string;
}

interface ConversationSidebarProps {
  conversations: ConversationSummary[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onNewConversation: () => void;
  collapsed: boolean;
  onToggle: () => void;
  className?: string;
}

function groupByDate(conversations: ConversationSummary[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  const groups: { label: string; items: ConversationSummary[] }[] = [
    { label: "Today", items: [] },
    { label: "This Week", items: [] },
    { label: "This Month", items: [] },
    { label: "Earlier", items: [] },
  ];

  for (const c of conversations) {
    const ts = new Date(c.timestamp);
    if (ts >= today) {
      groups[0].items.push(c);
    } else if (ts >= weekAgo) {
      groups[1].items.push(c);
    } else if (ts >= monthAgo) {
      groups[2].items.push(c);
    } else {
      groups[3].items.push(c);
    }
  }

  return groups.filter((g) => g.items.length > 0);
}

export function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNewConversation,
  collapsed,
  onToggle,
  className,
}: ConversationSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = searchQuery.trim()
    ? conversations.filter(
        (c) =>
          c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          c.lastMessage.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : conversations;

  const groups = groupByDate(filtered);

  if (collapsed) {
    return (
      <div
        className={clsx(
          "flex flex-col items-center py-3 border-r border-[var(--color-gray-200)] bg-[var(--color-surface-card)]",
          className,
        )}
      >
        <button
          type="button"
          onClick={onToggle}
          aria-label="Expand conversation history"
          className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] text-[var(--color-gray-500)] min-w-[44px] min-h-[44px] flex items-center justify-center"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
        <button
          type="button"
          onClick={onNewConversation}
          aria-label="New conversation"
          className="mt-2 p-2 rounded-lg hover:bg-[var(--color-gray-100)] text-[var(--color-primary)] min-w-[44px] min-h-[44px] flex items-center justify-center"
        >
          <Plus className="h-5 w-5" />
        </button>
      </div>
    );
  }

  return (
    <div
      className={clsx(
        "flex flex-col w-72 border-r border-[var(--color-gray-200)] bg-[var(--color-surface-card)]",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-[var(--color-gray-200)]">
        <h2 className="text-sm font-semibold text-[var(--color-gray-900)]">
          History
        </h2>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onNewConversation}
            aria-label="New conversation"
            className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] text-[var(--color-primary)] min-w-[44px] min-h-[44px] flex items-center justify-center"
          >
            <Plus className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={onToggle}
            aria-label="Collapse sidebar"
            className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] text-[var(--color-gray-500)] min-w-[44px] min-h-[44px] flex items-center justify-center"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="p-2">
        <div className="flex items-center gap-2 rounded-lg border border-[var(--color-gray-200)] bg-[var(--color-surface-input)] px-2 py-1.5">
          <Search className="h-4 w-4 text-[var(--color-gray-400)] shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="flex-1 bg-transparent text-sm text-[var(--foreground)] placeholder:text-[var(--color-gray-400)] outline-none"
          />
        </div>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {groups.length === 0 && (
          <div className="p-4 text-center text-sm text-[var(--color-gray-400)]">
            {searchQuery ? "No matching conversations" : "No conversations yet"}
          </div>
        )}

        {groups.map((group) => (
          <div key={group.label}>
            <div className="px-3 py-1.5 text-xs font-medium text-[var(--color-gray-400)] uppercase tracking-wider">
              {group.label}
            </div>
            {group.items.map((conv) => (
              <button
                key={conv.id}
                type="button"
                onClick={() => onSelect(conv.id)}
                className={clsx(
                  "w-full text-left px-3 py-2.5 transition-colors",
                  "hover:bg-[var(--color-gray-100)]",
                  "focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-primary)]",
                  activeId === conv.id &&
                    "bg-[var(--color-primary-bg)] border-l-2 border-l-[var(--color-primary)]",
                )}
              >
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-3.5 w-3.5 text-[var(--color-gray-400)] shrink-0" />
                  <span className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                    {conv.title}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-[var(--color-gray-500)] truncate pl-5">
                  {conv.lastMessage}
                </p>
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
