"use client";

import { MessageSquare, History, Plus, X } from "lucide-react";
import clsx from "clsx";

interface AdvisoryPanelHeaderProps {
  onToggleHistory: () => void;
  onNewConversation: () => void;
  onClose: () => void;
  historyOpen: boolean;
}

/**
 * Header bar for the advisory side panel.
 * Shows AITE branding plus history, new conversation, and close controls.
 */
export function AdvisoryPanelHeader({
  onToggleHistory,
  onNewConversation,
  onClose,
  historyOpen,
}: AdvisoryPanelHeaderProps) {
  const buttonBase = clsx(
    "p-2 rounded-lg min-w-[36px] min-h-[36px]",
    "flex items-center justify-center",
    "transition-colors",
    "focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--color-primary)]",
  );

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shrink-0">
      {/* Branding */}
      <div className="flex items-center gap-2">
        <div className="flex items-center justify-center h-7 w-7 rounded-lg bg-[var(--color-primary-bg)]">
          <MessageSquare className="h-4 w-4 text-[var(--color-primary)]" />
        </div>
        <span className="text-sm font-semibold text-[var(--color-gray-900)]">
          Ask AITE
        </span>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={onToggleHistory}
          aria-label={
            historyOpen
              ? "Close conversation history"
              : "View conversation history"
          }
          title="History"
          className={clsx(
            buttonBase,
            historyOpen
              ? "bg-[var(--color-primary-bg)] text-[var(--color-primary)]"
              : "text-[var(--color-gray-500)] hover:bg-[var(--color-gray-100)]",
          )}
        >
          <History className="h-4 w-4" />
        </button>

        <button
          type="button"
          onClick={onNewConversation}
          aria-label="New conversation"
          title="New conversation"
          className={clsx(
            buttonBase,
            "text-[var(--color-primary)] hover:bg-[var(--color-gray-100)]",
          )}
        >
          <Plus className="h-4 w-4" />
        </button>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close advisory panel"
          title="Close (Esc)"
          className={clsx(
            buttonBase,
            "text-[var(--color-gray-500)] hover:bg-[var(--color-gray-100)]",
          )}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
