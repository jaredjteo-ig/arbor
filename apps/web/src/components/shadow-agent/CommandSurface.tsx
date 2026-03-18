"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  X,
  ArrowRight,
  Compass,
  Calculator,
  Shield,
  FileText,
  AlertTriangle,
  ExternalLink,
  BookOpen,
} from "lucide-react";
import clsx from "clsx";
import {
  RiskTierBadge,
  type RiskTierLevel,
} from "@/components/design-system/RiskTierBadge";
import {
  SourceCitation,
  type AuthorityLevel,
} from "@/components/design-system/SourceCitation";
import type { CalculatorDisplayResult } from "./ShadowAgentContext";
import { useShadowAgent } from "./ShadowAgentContext";

/* ── Types ────────────────────────────────────────────────── */

interface CommandResult {
  type: "text" | "navigation" | "calculation" | "error";
  content: string;
  citations?: Array<{ label: string; authority: string }>;
  riskTier?: string;
  navigateTo?: string;
  calculatorResult?: CalculatorDisplayResult;
}

interface CommandSurfaceProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (query: string) => Promise<CommandResult | null>;
  /** Recent commands for suggestion list */
  recentCommands?: string[];
  /** Whether a command is currently being processed */
  isProcessing?: boolean;
}

/* ── Suggested commands (T118: includes deep advisory) ────── */

const ADMIN_SUGGESTED_COMMANDS = [
  { icon: Shield, text: "Check my compliance status", category: "compliance" },
  {
    icon: Calculator,
    text: "Calculate CPF for an employee",
    category: "calculator",
  },
  { icon: Compass, text: "Take me to emergency guides", category: "navigate" },
  { icon: FileText, text: "Generate a KET document", category: "document" },
  {
    icon: BookOpen,
    text: "Open deep advisory",
    category: "navigate",
  },
];

/* T137: Employee-specific command suggestions */
const EMPLOYEE_SUGGESTED_COMMANDS = [
  {
    icon: Calculator,
    text: "How many leave days do I have?",
    category: "advisory",
  },
  {
    icon: BookOpen,
    text: "What's my notice period?",
    category: "advisory",
  },
  {
    icon: Shield,
    text: "Show me the company leave policy",
    category: "navigate",
  },
  {
    icon: FileText,
    text: "What are my CPF contributions?",
    category: "advisory",
  },
];

/* ── Calculator Result Card (T115) ───────────────────────── */

function CalculatorResultCard({ result }: { result: CalculatorDisplayResult }) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Calculator className="h-4 w-4 text-[var(--color-secondary)]" />
        <span className="text-sm font-semibold text-[var(--foreground)]">
          {result.calculatorName}
        </span>
      </div>

      {/* Input parameters */}
      <div className="flex flex-wrap gap-2">
        {result.inputs.map((input) => (
          <span
            key={input.label}
            className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs bg-[var(--color-gray-100)] text-[var(--color-gray-600)]"
          >
            <span className="font-medium">{input.label}:</span> {input.value}
          </span>
        ))}
      </div>

      {/* Results grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
        {result.results.map((item) => (
          <div key={item.label} className="flex justify-between text-sm">
            <span className="text-[var(--color-gray-500)]">{item.label}</span>
            <span
              className={clsx(
                "font-medium tabular-nums",
                item.highlight
                  ? "text-[var(--color-secondary)]"
                  : "text-[var(--foreground)]",
              )}
            >
              {item.value}
            </span>
          </div>
        ))}
      </div>

      {/* Source + link */}
      <div className="flex items-center justify-between pt-1 border-t border-[var(--color-gray-200)]">
        <span className="text-[10px] text-[var(--color-gray-400)]">
          Source: {result.source}
        </span>
        <a
          href={result.linkTo}
          className="inline-flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline"
        >
          Open full calculator
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
}

/* ── Advisory Result (T114) ──────────────────────────────── */

function AdvisoryResult({
  content,
  riskTier,
  citations,
}: {
  content: string;
  riskTier?: string;
  citations?: Array<{ label: string; authority: string }>;
}) {
  // Map risk tier strings to RiskTierLevel
  const tierMap: Record<string, RiskTierLevel> = {
    green: "green",
    low: "green",
    amber: "amber",
    medium: "amber",
    red: "red",
    high: "red",
  };

  // Map authority strings to AuthorityLevel
  const authorityMap: Record<string, AuthorityLevel> = {
    statutory: "statutory",
    guideline: "guideline",
    "best-practice": "best-practice",
    "best practice": "best-practice",
  };

  const normalizedTier = riskTier ? tierMap[riskTier.toLowerCase()] : undefined;

  return (
    <div className="space-y-2">
      {/* Risk tier badge */}
      {normalizedTier && (
        <RiskTierBadge tier={normalizedTier} className="text-xs" />
      )}

      {/* Truncated content */}
      <p className="text-sm text-[var(--foreground)] whitespace-pre-wrap leading-relaxed">
        {content}
      </p>

      {/* Citation pills */}
      {citations && citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {citations.map((c, i) => (
            <SourceCitation
              key={i}
              label={c.label}
              authority={
                authorityMap[c.authority?.toLowerCase()] || "statutory"
              }
              className="text-[10px] px-2 py-0.5 min-h-0"
            />
          ))}
        </div>
      )}

      {/* Deep advisory link */}
      <div className="pt-1">
        <a
          href="/advisory"
          className="inline-flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline"
        >
          View full response in Advisory
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
}

/* ── Main Command Surface ────────────────────────────────── */

/**
 * The Command Surface -- a centered command palette overlay for AI interaction.
 *
 * Not a chat drawer. A command palette -- like Cmd+K search, but for AI.
 * Each invocation is a fresh command. No visible conversation history.
 * Stateless in presentation, contextful in intelligence.
 */
export function CommandSurface({
  isOpen,
  onClose,
  onSubmit,
  recentCommands = [],
  isProcessing = false,
}: CommandSurfaceProps) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<CommandResult | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { userRole } = useShadowAgent();
  const suggestedCommands =
    userRole === "employee"
      ? EMPLOYEE_SUGGESTED_COMMANDS
      : ADMIN_SUGGESTED_COMMANDS;

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      // Small delay to allow animation to start
      const timer = setTimeout(() => inputRef.current?.focus(), 100);
      return () => clearTimeout(timer);
    }
    // Reset state when closed
    if (!isOpen) {
      setQuery("");
      setResult(null);
      setIsStreaming(false);
    }
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  const handleSubmit = useCallback(
    async (input: string) => {
      if (!input.trim() || isProcessing) return;

      setResult(null);
      setIsStreaming(true);

      try {
        const commandResult = await onSubmit(input.trim());
        if (commandResult) {
          setResult(commandResult);
          // T116: If navigation, show confirmation then auto-close
          if (commandResult.type === "navigation" && commandResult.navigateTo) {
            setTimeout(() => onClose(), 800);
          }
        }
      } catch {
        setResult({
          type: "error",
          content: "Something went wrong. Please try again.",
        });
      } finally {
        setIsStreaming(false);
      }
    },
    [isProcessing, onSubmit, onClose],
  );

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 animate-shadow-fade-in"
        style={{ zIndex: "var(--z-shadow-command)" }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Command palette */}
      <div
        className="fixed inset-x-0 top-[30vh] sm:top-[15vh] flex justify-center px-4 animate-shadow-scale-in"
        style={{ zIndex: "calc(var(--z-shadow-command) + 1)" }}
        role="dialog"
        aria-label="Arbor Command Surface"
        aria-modal="true"
      >
        <div className="w-full max-w-2xl bg-[var(--color-surface-card)] rounded-2xl shadow-[var(--shadow-modal)] overflow-hidden">
          {/* Input bar */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--color-gray-200)]">
            <svg
              width="20"
              height="20"
              viewBox="0 0 18 18"
              fill="none"
              aria-hidden="true"
              className="shrink-0"
            >
              <circle
                cx="7"
                cy="9"
                r="5"
                fill="var(--color-primary)"
                opacity="0.6"
              />
              <ellipse
                cx="12"
                cy="9"
                rx="4"
                ry="3.5"
                fill="var(--color-primary)"
                opacity="0.2"
              />
            </svg>

            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleSubmit(query);
                }
              }}
              placeholder="Ask anything about Singapore HR, or tell me what to do..."
              className={clsx(
                "flex-1 bg-transparent text-base",
                "text-[var(--foreground)] placeholder:text-[var(--color-gray-400)]",
                "outline-none",
              )}
              disabled={isStreaming}
            />

            {query.trim() && !isStreaming ? (
              <button
                type="button"
                onClick={() => handleSubmit(query)}
                className="shrink-0 p-1.5 rounded-lg bg-[var(--color-primary)] text-white hover:opacity-90 transition-opacity"
                aria-label="Submit command"
              >
                <ArrowRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onClose}
                className="shrink-0 p-1.5 rounded-lg text-[var(--color-gray-500)] hover:text-[var(--foreground)] hover:bg-[var(--color-gray-100)] transition-colors"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Results area */}
          <div className="max-h-[50vh] overflow-y-auto">
            {/* Streaming indicator */}
            {isStreaming && (
              <div className="px-4 py-3 flex items-center gap-2 text-sm text-[var(--color-gray-500)]">
                <div className="h-4 w-4 rounded-full border-2 border-[var(--shadow-accent)] border-t-transparent animate-spin" />
                <span>Thinking...</span>
              </div>
            )}

            {/* Result display */}
            {result && !isStreaming && (
              <div className="px-4 py-3">
                {result.type === "error" ? (
                  <div className="flex items-start gap-2 text-sm text-[var(--color-risk-red)]">
                    <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                    <p>{result.content}</p>
                  </div>
                ) : result.type === "navigation" ? (
                  <div className="flex items-center gap-2 text-sm text-[var(--color-gray-600)]">
                    <Compass className="h-4 w-4 shrink-0" />
                    <span>{result.content}</span>
                  </div>
                ) : result.type === "calculation" && result.calculatorResult ? (
                  /* T115: Calculator result card */
                  <CalculatorResultCard result={result.calculatorResult} />
                ) : (
                  /* T114: Advisory result with risk badge and citations */
                  <AdvisoryResult
                    content={result.content}
                    riskTier={result.riskTier}
                    citations={result.citations}
                  />
                )}
              </div>
            )}

            {/* Suggestions -- shown when no result and no streaming */}
            {!result && !isStreaming && (
              <div className="px-4 py-3 space-y-3">
                {/* Recent commands */}
                {recentCommands.length > 0 && (
                  <div>
                    <p className="text-[10px] font-medium text-[var(--color-gray-400)] uppercase tracking-wider mb-1.5">
                      Recent
                    </p>
                    {recentCommands.slice(0, 3).map((cmd, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          setQuery(cmd);
                          handleSubmit(cmd);
                        }}
                        className="w-full text-left px-2 py-1.5 rounded-lg text-sm text-[var(--color-gray-600)] hover:bg-[var(--color-gray-100)] transition-colors truncate"
                      >
                        {cmd}
                      </button>
                    ))}
                  </div>
                )}

                {/* Suggested commands */}
                <div>
                  <p className="text-[10px] font-medium text-[var(--color-gray-400)] uppercase tracking-wider mb-1.5">
                    Suggestions
                  </p>
                  {suggestedCommands.map((cmd) => (
                    <button
                      key={cmd.text}
                      type="button"
                      onClick={() => {
                        setQuery(cmd.text);
                        handleSubmit(cmd.text);
                      }}
                      className="w-full flex items-center gap-2.5 px-2 py-2 rounded-lg text-sm text-[var(--color-gray-600)] hover:bg-[var(--color-gray-100)] transition-colors"
                    >
                      <cmd.icon className="h-4 w-4 text-[var(--color-gray-400)]" />
                      <span>{cmd.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer hint */}
          <div className="px-4 py-2 border-t border-[var(--color-gray-200)] flex items-center justify-between">
            <span className="text-[10px] text-[var(--color-gray-400)]">
              Press Escape to close
            </span>
            <span className="text-[10px] text-[var(--color-gray-400)]">
              Ctrl+Shift+A
            </span>
          </div>
        </div>
      </div>
    </>
  );
}
