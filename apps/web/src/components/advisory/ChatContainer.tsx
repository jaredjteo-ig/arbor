"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ChatBubble, ChatInput, toast } from "@/components/design-system";
import { Info, AlertCircle, RefreshCw, Loader2 } from "lucide-react";
import { SystemMessage } from "./SystemMessage";
import { ContextBar } from "./ContextBar";
import { advisoryApi } from "@/services/api/advisory";
import { learningApi } from "@/services/api/learning";
import { humanizeError, BudgetExceededError } from "@/services/api/errors";
import { useAuth } from "@/contexts/AuthContext";
import type {
  AdvisoryMessage,
  AdvisoryStreamStartEvent,
  AdvisoryStreamCompleteEvent,
  ProvisionCited,
} from "@/types/api";

/* ── Message Types ──────────────────────────────────────────── */

interface UserMessage {
  role: "user";
  content: string;
  timestamp: string;
}

interface AssistantMessage {
  role: "assistant";
  content: string;
  timestamp: string;
  riskTier?: string;
  confidenceScore?: number;
  provisionsCited?: ProvisionCited[];
  streaming?: boolean;
  /** Set when the free-tier LLM budget has been exhausted. */
  budgetExceeded?: boolean;
}

type ChatMessage = UserMessage | AssistantMessage;

/* ── Follow-Up Suggestion Logic ─────────────────────────────── */

function generateFollowUps(riskTier?: string, content?: string): string[] {
  if (riskTier === "red") {
    return [
      "What are my immediate obligations?",
      "What documents do I need?",
      "What are the penalties for non-compliance?",
    ];
  }
  if (riskTier === "amber") {
    return [
      "How do I fix this?",
      "What is the deadline?",
      "Can you generate the required document?",
    ];
  }
  // General follow-ups based on content keywords
  if (content?.toLowerCase().includes("cpf")) {
    return [
      "Calculate CPF for a specific employee",
      "What about PR employees?",
    ];
  }
  if (content?.toLowerCase().includes("leave")) {
    return ["Calculate leave entitlement", "What about part-time employees?"];
  }
  return ["Tell me more", "What should I do next?"];
}

/* ── Initial Suggestions ────────────────────────────────────── */

const INITIAL_SUGGESTIONS = [
  "What leave entitlements do my employees have?",
  "How do I calculate CPF contributions?",
  "Am I compliant with the Employment Act?",
  "What are the foreign worker quota limits for my sector?",
  "How do I handle a resignation properly?",
];

/* ── Phased Thinking Indicator ──────────────────────────────── */

const THINKING_PHASES = [
  "Searching knowledge base...",
  "Analysing provisions...",
  "Generating response...",
] as const;

function ThinkingIndicator() {
  const [phaseIndex, setPhaseIndex] = useState(0);

  useEffect(() => {
    // Phase 1 → Phase 2 at 2s, Phase 2 → Phase 3 at 4s
    const timers = [
      setTimeout(() => setPhaseIndex(1), 2000),
      setTimeout(() => setPhaseIndex(2), 4000),
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[80%] rounded-[12px] bg-[var(--color-surface-card)] p-4 shadow-[var(--shadow-card)]">
        <div className="flex items-center gap-2">
          <span className="inline-flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-bounce [animation-delay:300ms]" />
          </span>
          <span className="text-sm text-[var(--color-gray-500)] animate-pulse">
            {THINKING_PHASES[phaseIndex]}
          </span>
        </div>
      </div>
    </div>
  );
}

/* ── Chat Container Component ───────────────────────────────── */

interface ChatContainerProps {
  conversationId: number | null;
  onConversationStart: (id: number) => void;
  /** Messages loaded from conversation history API. */
  loadedMessages?: AdvisoryMessage[];
  /** Whether history messages are currently loading. */
  messagesLoading?: boolean;
  /** Error encountered while loading history. */
  messagesError?: Error | null;
  /** Retry callback for failed message loading. */
  onRetryLoad?: () => void;
}

/** Convert API history messages to internal ChatMessage format. */
function apiMessagesToChatMessages(msgs: AdvisoryMessage[]): ChatMessage[] {
  return msgs.map((m) => {
    if (m.role === "user") {
      return {
        role: "user" as const,
        content: m.content,
        timestamp: m.timestamp,
      };
    }
    return {
      role: "assistant" as const,
      content: m.content,
      timestamp: m.timestamp,
      riskTier: m.risk_tier,
      confidenceScore: m.confidence_score,
      provisionsCited: m.provisions_cited,
      streaming: false,
    };
  });
}

export function ChatContainer({
  conversationId,
  onConversationStart,
  loadedMessages,
  messagesLoading = false,
  messagesError = null,
  onRetryLoad,
}: ChatContainerProps) {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const prefillQuestion = searchParams.get("q");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeConvId, setActiveConvId] = useState<number | null>(
    conversationId,
  );
  const [isListening, setIsListening] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prefillHandled = useRef(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const lastLoadedConvRef = useRef<number | null>(null);

  // Check if Web Speech API is available
  const speechSupported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Sync external conversationId changes
  useEffect(() => {
    setActiveConvId(conversationId);
    // Clear messages when switching to a new conversation (null = new)
    if (conversationId === null) {
      setMessages([]);
      lastLoadedConvRef.current = null;
    }
  }, [conversationId]);

  // Load messages from history when they arrive
  useEffect(() => {
    if (
      loadedMessages &&
      loadedMessages.length > 0 &&
      conversationId !== null &&
      conversationId !== lastLoadedConvRef.current &&
      !isStreaming
    ) {
      setMessages(apiMessagesToChatMessages(loadedMessages));
      lastLoadedConvRef.current = conversationId;
    }
  }, [loadedMessages, conversationId, isStreaming]);

  // Handle prefilled question from onboarding
  useEffect(() => {
    if (prefillQuestion && !prefillHandled.current && messages.length === 0) {
      prefillHandled.current = true;
      sendMessage(prefillQuestion);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefillQuestion]);

  const sendMessage = useCallback(
    (text: string) => {
      if (isStreaming) return;

      // Add user message
      const userMsg: UserMessage = {
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };

      // Add placeholder assistant message for streaming
      const assistantMsg: AssistantMessage = {
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      // Start SSE stream
      const controller = advisoryApi.stream(
        {
          query: text,
          company_id: user?.company_id ?? undefined,
          conversation_id: activeConvId ?? undefined,
        },
        {
          onStart: (data: AdvisoryStreamStartEvent) => {
            if (!activeConvId) {
              setActiveConvId(data.conversation_id);
              onConversationStart(data.conversation_id);
            }
          },
          onToken: (token: string) => {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + token,
                };
              }
              return updated;
            });
          },
          onComplete: (data: AdvisoryStreamCompleteEvent) => {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: data.response,
                  riskTier: data.risk_tier,
                  confidenceScore: data.confidence_score,
                  provisionsCited: data.provisions_cited,
                  streaming: false,
                };
              }
              return updated;
            });
            setIsStreaming(false);
            abortRef.current = null;
          },
          onError: (error: Error) => {
            const isBudgetExceeded = error instanceof BudgetExceededError;
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: humanizeError(error),
                  riskTier: undefined,
                  streaming: false,
                  budgetExceeded: isBudgetExceeded,
                };
              }
              return updated;
            });
            setIsStreaming(false);
            abortRef.current = null;
          },
        },
      );

      abortRef.current = controller;
    },
    [isStreaming, user?.company_id, activeConvId, onConversationStart],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      if (recognitionRef.current) {
        recognitionRef.current.abort();
        recognitionRef.current = null;
      }
    };
  }, []);

  // Voice input handler using Web Speech API
  const handleVoice = useCallback(() => {
    if (!speechSupported) return;

    // If already listening, stop
    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognitionCtor =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognitionCtor) return;

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = "en-SG";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript;
      if (transcript && transcript.trim()) {
        sendMessage(transcript.trim());
      }
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognition.onerror = () => {
      setIsListening(false);
      recognitionRef.current = null;
      toast.error(
        "Could not recognise speech. Please check your microphone and try again.",
      );
    };

    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    setIsListening(true);
    recognition.start();
  }, [speechSupported, isListening, sendMessage]);

  const handleFeedback = useCallback(
    async (rating: "up" | "down", text?: string) => {
      const sessionId =
        activeConvId != null ? String(activeConvId) : crypto.randomUUID();
      try {
        await learningApi.submitFeedback({
          session_id: sessionId,
          is_positive: rating === "up",
          category: text ? "inaccurate" : undefined,
          query_snippet: text,
        });
        toast.success("Thank you for your feedback");
      } catch {
        toast.error("Could not submit feedback. Please try again.");
      }
    },
    [activeConvId],
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    // Mark the last assistant message as done streaming
    setMessages((prev) => {
      const updated = [...prev];
      const last = updated[updated.length - 1];
      if (last?.role === "assistant" && (last as AssistantMessage).streaming) {
        updated[updated.length - 1] = {
          ...last,
          streaming: false,
          content:
            (last as AssistantMessage).content ||
            "Response was stopped by user.",
        } as AssistantMessage;
      }
      return updated;
    });
  }, []);

  const isEmpty = messages.length === 0 && !messagesLoading;

  return (
    <div className="flex flex-col h-full">
      {/* Context bar */}
      <ContextBar />

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {/* Loading state while fetching conversation history */}
        {messagesLoading ? (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-lg mx-auto">
            <Loader2 className="h-8 w-8 text-[var(--color-primary)] animate-spin mb-4" />
            <p className="text-sm text-[var(--color-gray-500)]">
              Loading conversation...
            </p>
          </div>
        ) : messagesError ? (
          /* Error state with retry option */
          <div className="flex flex-col items-center justify-center h-full text-center max-w-sm mx-auto">
            <div className="w-12 h-12 rounded-full bg-[var(--color-error-bg,var(--color-gray-100))] flex items-center justify-center mb-3">
              <AlertCircle className="h-6 w-6 text-[var(--color-error)]" />
            </div>
            <h3 className="text-base font-semibold text-[var(--color-gray-900)] mb-1">
              Could not load conversation
            </h3>
            <p className="text-sm text-[var(--color-gray-500)] mb-4">
              {messagesError.message ||
                "Something went wrong. Please try again."}
            </p>
            {onRetryLoad && (
              <button
                type="button"
                onClick={onRetryLoad}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-[var(--color-primary)] text-white hover:opacity-90 transition-opacity"
              >
                <RefreshCw className="h-4 w-4" />
                Try again
              </button>
            )}
          </div>
        ) : isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-lg mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-[var(--color-primary-bg)] flex items-center justify-center mb-4">
              <span className="text-2xl">&#x1F4AC;</span>
            </div>
            <h2 className="text-xl font-bold text-[var(--color-gray-900)] mb-2">
              Ask Central anything about HR compliance
            </h2>
            <p className="text-sm text-[var(--color-gray-500)] mb-6">
              Get instant, cited guidance about employment law, CPF, foreign
              worker rules, leave entitlements, and more.
            </p>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.map((msg, idx) => {
              if (msg.role === "user") {
                return (
                  <ChatBubble key={idx} role="user">
                    {msg.content}
                  </ChatBubble>
                );
              }

              const assistantMsg = msg as AssistantMessage;
              const isLast = idx === messages.length - 1;

              // Streaming placeholder with no content yet — show phased thinking
              if (assistantMsg.streaming && !assistantMsg.content) {
                return (
                  <div key={idx} className="pl-0">
                    <ThinkingIndicator />
                  </div>
                );
              }

              // Budget exceeded — show a friendly info card instead of a generic error
              if (assistantMsg.budgetExceeded) {
                return (
                  <div key={idx} className="flex justify-start">
                    <div className="w-full max-w-[80%] rounded-[12px] border border-[var(--color-warning-border,var(--color-amber-200,#fde68a))] bg-[var(--color-warning-bg,var(--color-amber-50,#fffbeb))] p-4 shadow-[var(--shadow-card)]">
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 shrink-0">
                          <Info className="h-5 w-5 text-[var(--color-warning,var(--color-amber-600,#d97706))]" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-[var(--color-gray-900)] mb-1">
                            Free advisory limit reached
                          </p>
                          <p className="text-sm text-[var(--color-gray-600)] mb-3">
                            You&apos;ve used your free advisory allowance for
                            this month. To continue using the AI advisor, add
                            your own API key or set up a local AI model.
                          </p>
                          <Link
                            href="/settings/ai"
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-[var(--color-primary)] text-white hover:opacity-90 transition-opacity"
                          >
                            Go to AI Settings
                          </Link>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              }

              return (
                <SystemMessage
                  key={idx}
                  content={assistantMsg.content}
                  riskTier={assistantMsg.riskTier}
                  confidenceScore={assistantMsg.confidenceScore}
                  provisionsCited={assistantMsg.provisionsCited}
                  streaming={assistantMsg.streaming}
                  suggestions={
                    isLast && !assistantMsg.streaming
                      ? generateFollowUps(
                          assistantMsg.riskTier,
                          assistantMsg.content,
                        )
                      : undefined
                  }
                  onSuggestionClick={sendMessage}
                  onFeedback={
                    !assistantMsg.streaming ? handleFeedback : undefined
                  }
                />
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-[var(--color-gray-200)] bg-[var(--color-surface-card)] px-4 py-3">
        <div className="max-w-3xl mx-auto">
          <ChatInput
            onSend={sendMessage}
            onVoice={speechSupported ? handleVoice : undefined}
            isListening={isListening}
            isStreaming={isStreaming}
            onStop={handleStop}
            placeholder={
              isListening
                ? "Listening..."
                : isStreaming
                  ? "Waiting for response..."
                  : "Ask an HR question..."
            }
            disabled={isStreaming}
            suggestions={isEmpty ? INITIAL_SUGGESTIONS : undefined}
            onSuggestionClick={sendMessage}
          />
        </div>
      </div>

      {/* Legal disclaimer */}
      <div className="border-t border-[var(--color-gray-200)] bg-[var(--color-surface-card)] px-4 py-2">
        <div className="max-w-3xl mx-auto flex items-start gap-1.5">
          <Info className="h-3 w-3 text-[var(--color-gray-500)] mt-0.5 shrink-0" />
          <p className="text-xs text-[var(--color-gray-500)] leading-relaxed">
            Central provides general guidance based on Singapore employment
            regulations. This is not legal advice. Always consult a qualified
            employment law practitioner for specific situations.
          </p>
        </div>
      </div>
    </div>
  );
}
