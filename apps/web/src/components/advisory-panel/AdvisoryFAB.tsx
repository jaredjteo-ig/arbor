"use client";

import { MessageSquare } from "lucide-react";
import clsx from "clsx";
import { useAdvisoryPanel } from "@/contexts/AdvisoryPanelContext";

/**
 * Floating action button for opening the advisory side panel.
 * Fixed to the bottom-right corner. Hidden when the panel is open
 * or when the user is on the /advisory page.
 */
export function AdvisoryFAB() {
  const { isOpen, isAdvisoryPage, activeConversationId, open } =
    useAdvisoryPanel();

  if (isOpen || isAdvisoryPage) return null;

  const hasActiveConversation = activeConversationId !== null;

  return (
    <button
      type="button"
      onClick={open}
      aria-label="Ask Arbor (Ctrl+Shift+A)"
      title="Ask Arbor (Ctrl+Shift+A)"
      className={clsx(
        "fixed bottom-6 right-6 z-20",
        "flex items-center justify-center",
        "h-14 w-14 rounded-full",
        "bg-[var(--color-primary)] text-white shadow-lg",
        "hover:scale-105 active:scale-95",
        "transition-transform duration-150 ease-out",
        "motion-reduce:transition-none motion-reduce:hover:scale-100",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
      )}
    >
      <MessageSquare className="h-6 w-6" />

      {/* Active conversation indicator dot */}
      {hasActiveConversation && (
        <span
          className="absolute top-0 right-0 h-3.5 w-3.5 rounded-full bg-[var(--color-risk-amber)] border-2 border-white"
          aria-hidden="true"
        />
      )}
    </button>
  );
}
