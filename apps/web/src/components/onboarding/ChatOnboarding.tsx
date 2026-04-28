"use client";

/**
 * ChatOnboarding (T223)
 * --------------------------------------------------------------
 * A conversational alternative to CompanySetupModal. The shadow
 * agent asks for each field one at a time. Backend state machine
 * (POST /shadow/onboarding/chat) decides what to ask next; this
 * component is just the chat surface.
 *
 * On `next_step === "done"` the component:
 *   1. Calls profileApi.create() with the collected fields,
 *   2. Refreshes the auth user (to pick up company_id),
 *   3. Calls onComplete() so the parent can route forward
 *      (e.g. show the compliance snapshot or go to the dashboard).
 */

import { useEffect, useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import { ChatBubble } from "@/components/design-system/ChatBubble";
import { ChatInput } from "@/components/design-system/ChatInput";
import { useAuth } from "@/contexts/AuthContext";
import { profileApi } from "@/services/api/profile";
import { shadowApi } from "@/services/api/shadow";

/* ── Types ────────────────────────────────────────────────── */

interface ChatMessage {
  id: string;
  role: "user" | "system";
  text: string;
}

interface OnboardingFields {
  name?: string;
  sector?: string;
  headcount?: string;
  foreign_workers?: boolean;
}

export interface ChatOnboardingResult extends OnboardingFields {
  /** The numeric company id returned by /profile create (null on failure). */
  companyId: number | null;
}

interface ChatOnboardingProps {
  /** Called once the company profile has been created successfully. */
  onComplete?: (result: ChatOnboardingResult) => void;
  /** Called when the user dismisses the chat ("I'll do this later"). */
  onSkip?: () => void;
  /** Suggested chip prompts shown beneath the chat input for the current step. */
  className?: string;
}

const STEP_SUGGESTIONS: Record<string, string[]> = {
  sector: [
    "Technology",
    "F&B",
    "Retail",
    "Manufacturing",
    "Construction",
    "Services",
    "Healthcare",
  ],
  headcount: ["1-5", "6-25", "26-50", "51-100", "101-200"],
  foreign_workers: ["Yes", "No"],
  confirm: ["Yes", "No"],
};

/* ── Component ────────────────────────────────────────────── */

export function ChatOnboarding({
  onComplete,
  onSkip,
  className,
}: ChatOnboardingProps) {
  const { refreshUser } = useAuth();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [step, setStep] = useState<string>("");
  const [fields, setFields] = useState<OnboardingFields>({});
  const [isSending, setIsSending] = useState(false);
  const [isFinalising, setIsFinalising] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const initialisedRef = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  /* Kick off the conversation on mount. */
  useEffect(() => {
    if (initialisedRef.current) return;
    initialisedRef.current = true;
    void kickoff();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* Auto-scroll to the latest message. */
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isSending, isFinalising]);

  async function kickoff() {
    setIsSending(true);
    setErrorBanner(null);
    try {
      const res = await shadowApi.onboardingChat("", "", {});
      setStep(res.next_step);
      setFields((res.fields ?? {}) as OnboardingFields);
      appendSystem(res.prompt);
    } catch (err: unknown) {
      const message =
        (err as { detail?: string; message?: string })?.detail ??
        (err as { message?: string })?.message ??
        "Couldn't reach the assistant. Please try again.";
      setErrorBanner(message);
    } finally {
      setIsSending(false);
    }
  }

  function appendUser(text: string) {
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}-${prev.length}`, role: "user", text },
    ]);
  }

  function appendSystem(text: string) {
    setMessages((prev) => [
      ...prev,
      { id: `s-${Date.now()}-${prev.length}`, role: "system", text },
    ]);
  }

  async function handleSend(rawAnswer: string) {
    const answer = rawAnswer.trim();
    if (!answer || isSending || isFinalising) return;

    appendUser(answer);
    setIsSending(true);
    setErrorBanner(null);

    try {
      const res = await shadowApi.onboardingChat(
        step,
        answer,
        fields as Record<string, unknown>,
      );

      setFields((res.fields ?? {}) as OnboardingFields);

      if (res.next_step === "done") {
        appendSystem(res.prompt);
        setStep("done");
        await finaliseProfile((res.fields ?? {}) as OnboardingFields);
        return;
      }

      setStep(res.next_step);
      appendSystem(res.prompt);

      if (res.error) {
        // Soft clarification — show the error inline as another system bubble.
        appendSystem(`Arbor: ${res.error}`);
      }
    } catch (err: unknown) {
      const message =
        (err as { detail?: string; message?: string })?.detail ??
        (err as { message?: string })?.message ??
        "Something went wrong. Please try again.";
      setErrorBanner(message);
    } finally {
      setIsSending(false);
    }
  }

  async function finaliseProfile(finalFields: OnboardingFields) {
    setIsFinalising(true);
    try {
      const created = await profileApi.create({
        name: finalFields.name ?? "",
        sector: finalFields.sector ?? "",
      } as Parameters<typeof profileApi.create>[0]);

      await refreshUser?.();

      appendSystem(
        "Arbor: All done. Your company profile is set up and the full HR suite is unlocked.",
      );

      onComplete?.({
        ...finalFields,
        companyId: created?.id ?? null,
      });
    } catch (err: unknown) {
      const message =
        (err as { detail?: string; message?: string })?.detail ??
        (err as { message?: string })?.message ??
        "Couldn't create the company profile. Please try again.";
      setErrorBanner(message);
      appendSystem(
        "Arbor: I hit a snag creating the profile. You can retry, or use the standard form instead.",
      );
      // Step back to confirm so the user can retry by saying "yes" again.
      setStep("confirm");
    } finally {
      setIsFinalising(false);
    }
  }

  const suggestions =
    !isSending && !isFinalising && step && step !== "done"
      ? STEP_SUGGESTIONS[step]
      : undefined;

  const placeholder =
    step === "name"
      ? "Type your company name..."
      : step === "sector"
        ? "Type or pick an industry..."
        : step === "headcount"
          ? "Type a range or number..."
          : step === "foreign_workers" || step === "confirm"
            ? "Yes or no..."
            : "Type your reply...";

  return (
    <div
      className={[
        "flex flex-col w-full max-w-2xl mx-auto",
        "bg-[var(--color-surface-page)] rounded-2xl",
        "border border-[var(--color-gray-200)] shadow-sm",
        "overflow-hidden",
        className ?? "",
      ].join(" ")}
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-[var(--color-gray-200)] bg-white">
        <div className="w-9 h-9 rounded-full bg-[var(--color-primary-bg)] flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-[var(--color-primary)]" />
        </div>
        <div className="flex-1">
          <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
            Set up with Arbor
          </h2>
          <p className="text-xs text-[var(--color-gray-500)]">
            Conversational onboarding (beta)
          </p>
        </div>
        {onSkip && (
          <button
            type="button"
            onClick={onSkip}
            className="text-xs text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] underline"
          >
            I&apos;ll do this later
          </button>
        )}
      </div>

      {/* Error banner */}
      {errorBanner && (
        <div
          role="alert"
          className="px-5 py-2 text-sm bg-[var(--color-risk-red-bg)] text-[var(--color-risk-red)] border-b border-[var(--color-risk-red-border)]"
        >
          {errorBanner}
        </div>
      )}

      {/* Message list */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-5 py-4 space-y-3 max-h-[60vh] min-h-[320px]"
      >
        {messages.map((msg) =>
          msg.role === "user" ? (
            <ChatBubble key={msg.id} role="user">
              {msg.text}
            </ChatBubble>
          ) : (
            <ChatBubble key={msg.id} role="system">
              {/* Preserve newlines from the backend prompt. */}
              <div className="whitespace-pre-wrap">{msg.text}</div>
            </ChatBubble>
          ),
        )}

        {(isSending || isFinalising) && (
          <ChatBubble role="system">
            <span className="inline-flex items-center gap-1 text-[var(--color-gray-500)]">
              <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
              <span
                className="w-1.5 h-1.5 rounded-full bg-current animate-pulse"
                style={{ animationDelay: "150ms" }}
              />
              <span
                className="w-1.5 h-1.5 rounded-full bg-current animate-pulse"
                style={{ animationDelay: "300ms" }}
              />
              <span className="ml-2 text-xs">
                {isFinalising ? "Creating your company..." : "Thinking..."}
              </span>
            </span>
          </ChatBubble>
        )}
      </div>

      {/* Input */}
      <div className="px-5 py-4 border-t border-[var(--color-gray-200)] bg-white">
        <ChatInput
          onSend={handleSend}
          suggestions={suggestions}
          onSuggestionClick={(s) => void handleSend(s)}
          placeholder={placeholder}
          disabled={isSending || isFinalising || step === "done"}
        />
      </div>
    </div>
  );
}
