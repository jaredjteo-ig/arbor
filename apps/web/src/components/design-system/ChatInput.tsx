"use client";

import { useState, useRef, type KeyboardEvent } from "react";
import clsx from "clsx";
import { Mic, Send } from "lucide-react";

export interface ChatInputProps {
  /** Called when the user submits a message */
  onSend: (message: string) => void;
  /** Called when the voice button is pressed */
  onVoice?: () => void;
  /** Whether the microphone is actively listening */
  isListening?: boolean;
  /** Suggested prompts displayed as chips below the input */
  suggestions?: string[];
  /** Called when a suggestion chip is clicked */
  onSuggestionClick?: (suggestion: string) => void;
  /** Placeholder text for the input */
  placeholder?: string;
  /** Disable the input */
  disabled?: boolean;
  className?: string;
}

export function ChatInput({
  onSend,
  onVoice,
  isListening = false,
  suggestions,
  onSuggestionClick,
  placeholder = "Type your question...",
  disabled = false,
  className,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const trimmed = value.trim();

  function handleSend() {
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    inputRef.current?.focus();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleSuggestion(s: string) {
    if (onSuggestionClick) {
      onSuggestionClick(s);
    } else {
      onSend(s);
    }
  }

  return (
    <div className={clsx("flex flex-col gap-2", className)}>
      {/* Input row */}
      <div
        className={clsx(
          "flex items-center gap-2 rounded-[12px] border px-3 py-2",
          "bg-[var(--color-surface-input)] border-[var(--color-surface-input-border)]",
          "focus-within:border-[var(--color-surface-input-focus)]",
          "transition-colors",
        )}
      >
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          className={clsx(
            "flex-1 bg-transparent text-base text-[var(--foreground)]",
            "placeholder:text-[var(--color-gray-400)]",
            "outline-none min-h-[40px]",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          )}
        />

        {/* Voice button */}
        {onVoice && (
          <button
            type="button"
            onClick={onVoice}
            disabled={disabled}
            aria-label={isListening ? "Stop voice input" : "Voice input"}
            className={clsx(
              "flex items-center justify-center rounded-full p-2 min-w-[44px] min-h-[44px]",
              "transition-colors",
              "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              isListening
                ? "bg-[var(--color-error)] text-white animate-pulse"
                : "text-[var(--color-gray-500)] hover:text-[var(--color-primary)] hover:bg-[var(--color-gray-100)]",
            )}
          >
            <Mic className="h-5 w-5" />
          </button>
        )}

        {/* Send button */}
        <button
          type="button"
          onClick={handleSend}
          disabled={disabled || !trimmed}
          aria-label="Send message"
          className={clsx(
            "flex items-center justify-center rounded-full p-2 min-w-[44px] min-h-[44px]",
            "transition-colors",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            trimmed
              ? "bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-light)]"
              : "bg-[var(--color-gray-200)] text-[var(--color-gray-400)]",
          )}
        >
          <Send className="h-5 w-5" />
        </button>
      </div>

      {/* Suggestion chips */}
      {suggestions && suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 overflow-x-auto pb-1">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => handleSuggestion(s)}
              disabled={disabled}
              className={clsx(
                "inline-flex items-center whitespace-nowrap rounded-full",
                "px-3 py-1.5 text-sm min-h-[36px]",
                "border border-[var(--color-gray-300)] bg-[var(--color-surface-card)]",
                "text-[var(--color-gray-700)]",
                "hover:bg-[var(--color-gray-100)] hover:border-[var(--color-primary)]",
                "hover:text-[var(--color-primary)]",
                "transition-colors",
                "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
                "disabled:opacity-50 disabled:cursor-not-allowed",
              )}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
