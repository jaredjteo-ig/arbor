"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  ChatBubble,
  ChatInput,
  LoadingState,
  toast,
} from "@/components/design-system";
import { SystemMessage } from "./SystemMessage";
import { ContextBar } from "./ContextBar";
import { advisoryApi } from "@/services/api/advisory";
import { learningApi } from "@/services/api/learning";
import { useAuth } from "@/contexts/AuthContext";
import type {
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

/* ── Chat Container Component ───────────────────────────────── */

interface ChatContainerProps {
  conversationId: number | null;
  onConversationStart: (id: number) => void;
}

export function ChatContainer({
  conversationId,
  onConversationStart,
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
  }, [conversationId]);

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
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: `Sorry, something went wrong: ${error.message}. Please try again.`,
                  riskTier: undefined,
                  streaming: false,
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

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full">
      {/* Context bar */}
      <ContextBar />

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-lg mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-[var(--color-primary-bg)] flex items-center justify-center mb-4">
              <span className="text-2xl">💬</span>
            </div>
            <h2 className="text-xl font-bold text-[var(--color-gray-900)] mb-2">
              Ask AITE anything about Singapore HR
            </h2>
            <p className="text-sm text-[var(--color-gray-500)] mb-6">
              Get instant, cited answers about employment law, CPF, foreign
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

              // Streaming placeholder with no content yet
              if (assistantMsg.streaming && !assistantMsg.content) {
                return (
                  <div key={idx} className="pl-0">
                    <LoadingState variant="chat" count={1} />
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
    </div>
  );
}
