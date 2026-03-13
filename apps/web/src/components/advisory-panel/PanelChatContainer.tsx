"use client";

import { useEffect, useRef, useCallback } from "react";
import { ChatContainer } from "@/components/advisory";
import { useAdvisoryPanel } from "@/contexts/AdvisoryPanelContext";

/**
 * Thin wrapper around ChatContainer that integrates with the advisory panel context.
 * Handles:
 * - Forwarding conversation start events to the context
 * - Auto-sending pending questions from askQuestion()
 */
export function PanelChatContainer() {
  const {
    activeConversationId,
    pendingQuestion,
    setActiveConversation,
    addConversation,
    clearPendingQuestion,
  } = useAdvisoryPanel();

  const pendingHandled = useRef(false);

  const handleConversationStart = useCallback(
    (id: number) => {
      setActiveConversation(id);
      addConversation({
        id,
        title: "New conversation",
        lastMessage: "",
        timestamp: new Date().toISOString(),
      });
    },
    [setActiveConversation, addConversation],
  );

  /* Watch for pending questions and auto-send them.
   * We use a MutationObserver-free approach: when pendingQuestion changes,
   * we simulate submitting via the ChatInput's form. The ChatContainer
   * already supports prefilled questions via search params — here we
   * achieve the same by programmatically finding and submitting the input. */
  useEffect(() => {
    if (!pendingQuestion || pendingHandled.current) return;

    pendingHandled.current = true;

    // Small delay to ensure ChatContainer has mounted its input
    const timer = setTimeout(() => {
      const panelEl = document.getElementById("advisory-panel");
      if (!panelEl) {
        clearPendingQuestion();
        pendingHandled.current = false;
        return;
      }

      // Find the textarea/input inside the panel's chat input
      const input = panelEl.querySelector<
        HTMLTextAreaElement | HTMLInputElement
      >("textarea, input[type='text']");

      if (input) {
        // Set the value using native setter to trigger React's onChange
        const nativeSetter =
          Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype,
            "value",
          )?.set ??
          Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype,
            "value",
          )?.set;

        if (nativeSetter) {
          nativeSetter.call(input, pendingQuestion);
          input.dispatchEvent(new Event("input", { bubbles: true }));
        }

        // Submit the form after the value is set
        requestAnimationFrame(() => {
          const form = input.closest("form");
          if (form) {
            form.dispatchEvent(
              new Event("submit", { bubbles: true, cancelable: true }),
            );
          }
          clearPendingQuestion();
          pendingHandled.current = false;
        });
      } else {
        clearPendingQuestion();
        pendingHandled.current = false;
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [pendingQuestion, clearPendingQuestion]);

  /* Reset pending handled flag when pendingQuestion changes to a new value */
  useEffect(() => {
    if (pendingQuestion) {
      pendingHandled.current = false;
    }
  }, [pendingQuestion]);

  return (
    <ChatContainer
      conversationId={activeConversationId}
      onConversationStart={handleConversationStart}
    />
  );
}
