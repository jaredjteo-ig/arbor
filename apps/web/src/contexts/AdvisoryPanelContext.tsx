"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { usePathname } from "next/navigation";
import type { ConversationSummary } from "@/components/advisory";

/* ── Types ────────────────────────────────────────────────── */

interface AdvisoryPanelState {
  isOpen: boolean;
  conversations: ConversationSummary[];
  activeConversationId: number | null;
  pendingQuestion: string | null;
  /** True when the current pathname starts with /advisory */
  isAdvisoryPage: boolean;
}

interface AdvisoryPanelAPI {
  open: () => void;
  close: () => void;
  toggle: () => void;
  /** Opens panel and prefills a question to auto-send */
  askQuestion: (question: string) => void;
  startNewConversation: () => void;
  setActiveConversation: (id: number) => void;
  addConversation: (conv: ConversationSummary) => void;
  clearPendingQuestion: () => void;
}

type AdvisoryPanelContextValue = AdvisoryPanelState & AdvisoryPanelAPI;

/* ── Storage key ─────────────────────────────────────────── */

const ACTIVE_CONV_KEY = "arbor-advisory-active-conv";

/* ── Context ─────────────────────────────────────────────── */

const AdvisoryPanelContext = createContext<AdvisoryPanelContextValue | null>(
  null,
);

/* ── Provider ────────────────────────────────────────────── */

export function AdvisoryPanelProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isAdvisoryPage = pathname.startsWith("/advisory");

  const [isOpen, setIsOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<
    number | null
  >(null);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);

  /* Restore active conversation from sessionStorage on mount */
  useEffect(() => {
    const stored = sessionStorage.getItem(ACTIVE_CONV_KEY);
    if (stored !== null) {
      const parsed = parseInt(stored, 10);
      if (!Number.isNaN(parsed)) {
        setActiveConversationId(parsed);
      }
    }
  }, []);

  /* Persist active conversation to sessionStorage */
  useEffect(() => {
    if (activeConversationId !== null) {
      sessionStorage.setItem(ACTIVE_CONV_KEY, String(activeConversationId));
    } else {
      sessionStorage.removeItem(ACTIVE_CONV_KEY);
    }
  }, [activeConversationId]);

  /* Auto-close panel when navigating to /advisory page */
  useEffect(() => {
    if (isAdvisoryPage && isOpen) {
      setIsOpen(false);
    }
  }, [isAdvisoryPage, isOpen]);

  /* Keyboard shortcut: Ctrl+Shift+A / Cmd+Shift+A */
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Don't fire when user is typing in an input or textarea
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      const modKey = e.metaKey || e.ctrlKey;
      if (modKey && e.shiftKey && e.key.toLowerCase() === "a") {
        e.preventDefault();
        if (!isAdvisoryPage) {
          setIsOpen((prev) => !prev);
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isAdvisoryPage]);

  /* ── API methods ──────────────────────────────────────── */

  const open = useCallback(() => {
    if (!isAdvisoryPage) {
      setIsOpen(true);
    }
  }, [isAdvisoryPage]);

  const close = useCallback(() => {
    setIsOpen(false);
  }, []);

  const toggle = useCallback(() => {
    if (!isAdvisoryPage) {
      setIsOpen((prev) => !prev);
    }
  }, [isAdvisoryPage]);

  const askQuestion = useCallback(
    (question: string) => {
      setPendingQuestion(question);
      if (!isAdvisoryPage) {
        setIsOpen(true);
      }
    },
    [isAdvisoryPage],
  );

  const startNewConversation = useCallback(() => {
    setActiveConversationId(null);
  }, []);

  const setActiveConversation = useCallback((id: number) => {
    setActiveConversationId(id);
  }, []);

  const addConversation = useCallback((conv: ConversationSummary) => {
    setConversations((prev) => {
      if (prev.some((c) => c.id === conv.id)) return prev;
      return [conv, ...prev];
    });
  }, []);

  const clearPendingQuestion = useCallback(() => {
    setPendingQuestion(null);
  }, []);

  return (
    <AdvisoryPanelContext.Provider
      value={{
        isOpen,
        conversations,
        activeConversationId,
        pendingQuestion,
        isAdvisoryPage,
        open,
        close,
        toggle,
        askQuestion,
        startNewConversation,
        setActiveConversation,
        addConversation,
        clearPendingQuestion,
      }}
    >
      {children}
    </AdvisoryPanelContext.Provider>
  );
}

/* ── Hook ─────────────────────────────────────────────────── */

export function useAdvisoryPanel(): AdvisoryPanelContextValue {
  const context = useContext(AdvisoryPanelContext);
  if (!context) {
    throw new Error(
      "useAdvisoryPanel must be used within an AdvisoryPanelProvider",
    );
  }
  return context;
}
