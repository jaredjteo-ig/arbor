"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import clsx from "clsx";
import { ConversationSidebar } from "@/components/advisory";
import { useAdvisoryPanel } from "@/contexts/AdvisoryPanelContext";
import { AdvisoryPanelHeader } from "./AdvisoryPanelHeader";
import { PanelChatContainer } from "./PanelChatContainer";

/**
 * Sliding advisory drawer panel.
 * Fixed to the right edge of the viewport.
 * Contains the chat interface for asking AITE questions from any dashboard page.
 */
export function AdvisoryPanel() {
  const {
    isOpen,
    isAdvisoryPage,
    conversations,
    activeConversationId,
    close,
    startNewConversation,
    setActiveConversation,
  } = useAdvisoryPanel();

  const [historyOpen, setHistoryOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  /* Close on Escape key */
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, close]);

  /* Focus trap: keep tab within the panel when open */
  useEffect(() => {
    if (!isOpen || !panelRef.current) return;

    const panel = panelRef.current;

    function handleTabTrap(e: KeyboardEvent) {
      if (e.key !== "Tab") return;

      const focusable = panel.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    window.addEventListener("keydown", handleTabTrap);

    // Auto-focus the panel on open
    const firstFocusable = panel.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    firstFocusable?.focus();

    return () => window.removeEventListener("keydown", handleTabTrap);
  }, [isOpen]);

  /* Close history when panel closes */
  useEffect(() => {
    if (!isOpen) {
      setHistoryOpen(false);
    }
  }, [isOpen]);

  const handleToggleHistory = useCallback(() => {
    setHistoryOpen((prev) => !prev);
  }, []);

  const handleNewConversation = useCallback(() => {
    startNewConversation();
    setHistoryOpen(false);
  }, [startNewConversation]);

  const handleSelectConversation = useCallback(
    (id: number) => {
      setActiveConversation(id);
      setHistoryOpen(false);
    },
    [setActiveConversation],
  );

  const handleScrimClick = useCallback(() => {
    close();
  }, [close]);

  // Don't render on the advisory page
  if (isAdvisoryPage) return null;

  return (
    <>
      {/* Scrim for tablet and mobile */}
      {isOpen && (
        <div
          className={clsx(
            "fixed inset-0 z-[29] transition-opacity duration-200",
            "motion-reduce:transition-none",
            // Desktop: no scrim
            "hidden",
            // Tablet: light scrim
            "md:block md:bg-black/10",
            // Desktop (>=1024): no scrim
            "lg:hidden",
          )}
          onClick={handleScrimClick}
          aria-hidden="true"
        />
      )}

      {/* Mobile scrim (always visible on mobile when open) */}
      {isOpen && (
        <div
          className={clsx(
            "fixed inset-0 z-[29] bg-black/30 md:hidden",
            "transition-opacity duration-200",
            "motion-reduce:transition-none",
          )}
          onClick={handleScrimClick}
          aria-hidden="true"
        />
      )}

      {/* Panel */}
      <div
        ref={panelRef}
        id="advisory-panel"
        role="dialog"
        aria-label="AITE Advisory Panel"
        aria-modal="false"
        className={clsx(
          "fixed top-0 right-0 z-30 h-full",
          "bg-[var(--color-surface-card)] shadow-2xl",
          "flex flex-col",
          // Width: full on mobile, 420px on tablet+
          "w-full md:w-[420px]",
          // Slide animation
          "transition-transform duration-200 ease-out",
          "motion-reduce:transition-none",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        {/* Header */}
        <AdvisoryPanelHeader
          onToggleHistory={handleToggleHistory}
          onNewConversation={handleNewConversation}
          onClose={close}
          historyOpen={historyOpen}
        />

        {/* Content area */}
        <div className="flex-1 flex min-h-0 relative">
          {/* Conversation history overlay */}
          {historyOpen && (
            <div className="absolute inset-0 z-10 bg-[var(--color-surface-card)]">
              <ConversationSidebar
                conversations={conversations}
                activeId={activeConversationId}
                onSelect={handleSelectConversation}
                onNewConversation={handleNewConversation}
                collapsed={false}
                onToggle={handleToggleHistory}
                className="h-full border-r-0"
              />
            </div>
          )}

          {/* Chat container */}
          <div className="flex-1 flex flex-col min-h-0">
            {isOpen && <PanelChatContainer />}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="shrink-0 border-t border-[var(--color-gray-200)] bg-[var(--color-surface-card)]">
          <p className="text-[10px] text-[var(--color-gray-400)] px-4 py-1 text-center">
            AITE provides general guidance, not legal advice. Consult a
            qualified practitioner for specific situations.
          </p>
        </div>
      </div>
    </>
  );
}
