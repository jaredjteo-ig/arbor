"use client";

import { useState, useRef, useEffect } from "react";
import clsx from "clsx";
import { ThumbsUp, ThumbsDown } from "lucide-react";

export interface FeedbackPayload {
  rating: "up" | "down";
  text?: string;
}

export interface FeedbackButtonsProps {
  /** Called when feedback is submitted */
  onFeedback: (feedback: FeedbackPayload) => void;
  className?: string;
}

export function FeedbackButtons({
  onFeedback,
  className,
}: FeedbackButtonsProps) {
  const [selected, setSelected] = useState<"up" | "down" | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (selected === "down" && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [selected]);

  function handleUp() {
    if (submitted) return;
    setSelected("up");
    setSubmitted(true);
    onFeedback({ rating: "up" });
  }

  function handleDown() {
    if (submitted) return;
    setSelected("down");
  }

  function handleSubmitDown() {
    setSubmitted(true);
    onFeedback({
      rating: "down",
      text: feedbackText.trim() || undefined,
    });
  }

  if (submitted) {
    return (
      <div className={clsx("text-sm text-[var(--color-gray-500)]", className)}>
        Thank you for your feedback.
      </div>
    );
  }

  return (
    <div className={clsx("flex flex-col gap-2", className)}>
      <div className="flex items-center gap-2">
        {/* Thumbs up */}
        <button
          type="button"
          onClick={handleUp}
          aria-label="Helpful"
          aria-pressed={selected === "up"}
          className={clsx(
            "inline-flex items-center justify-center rounded-[8px] p-2 min-w-[44px] min-h-[44px]",
            "transition-colors",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
            selected === "up"
              ? "bg-[var(--color-success-bg)] text-[var(--color-success)]"
              : "text-[var(--color-gray-400)] hover:text-[var(--color-success)] hover:bg-[var(--color-success-bg)]",
          )}
        >
          <ThumbsUp className="h-5 w-5" />
        </button>

        {/* Thumbs down */}
        <button
          type="button"
          onClick={handleDown}
          aria-label="Not helpful"
          aria-pressed={selected === "down"}
          className={clsx(
            "inline-flex items-center justify-center rounded-[8px] p-2 min-w-[44px] min-h-[44px]",
            "transition-colors",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
            selected === "down"
              ? "bg-[var(--color-error-bg)] text-[var(--color-error)]"
              : "text-[var(--color-gray-400)] hover:text-[var(--color-error)] hover:bg-[var(--color-error-bg)]",
          )}
        >
          <ThumbsDown className="h-5 w-5" />
        </button>
      </div>

      {/* Expanded feedback form */}
      {selected === "down" && (
        <div className="flex flex-col gap-2">
          <textarea
            ref={textareaRef}
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            placeholder="What was wrong?"
            className={clsx(
              "w-full rounded-[8px] border px-3 py-2 text-sm min-h-[80px] resize-y",
              "bg-[var(--color-surface-input)] text-[var(--foreground)]",
              "border-[var(--color-surface-input-border)]",
              "placeholder:text-[var(--color-gray-400)]",
              "focus:border-[var(--color-surface-input-focus)]",
              "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
            )}
          />
          <button
            type="button"
            onClick={handleSubmitDown}
            className={clsx(
              "self-start inline-flex items-center justify-center rounded-[8px] font-medium",
              "px-3 py-1.5 text-sm min-h-[36px]",
              "bg-[var(--color-primary)] text-white",
              "hover:bg-[var(--color-primary-light)] active:bg-[var(--color-primary-dark)]",
              "transition-colors",
              "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
            )}
          >
            Submit
          </button>
        </div>
      )}
    </div>
  );
}
