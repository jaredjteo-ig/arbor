"use client";

import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, X, Lightbulb } from "lucide-react";
import clsx from "clsx";
import { useShadowAgent } from "./ShadowAgentContext";
import type { ObservationInsight } from "./useObservation";

/* ── Types ────────────────────────────────────────────────── */

export interface ShadowInsight {
  id: string;
  type: "compliance_gap" | "deadline" | "regulatory_update" | "suggestion";
  severity: "high" | "medium" | "low" | "info";
  title: string;
  description: string;
  provision?: string;
  fineAmount?: string;
  daysRemaining?: number;
  action?: { type: "navigate" | "calculate" | "advisory"; target: string };
}

interface ShadowMarginProps {
  insights: ShadowInsight[];
  isLoading?: boolean;
  /** T140: Proactive observation insights from the observation layer */
  observationInsights?: ObservationInsight[];
}

/* ── Severity colors ──────────────────────────────────────── */

const severityDotColors: Record<string, string> = {
  high: "bg-[var(--color-risk-red)]",
  medium: "bg-[var(--color-risk-amber)]",
  low: "bg-[var(--color-risk-green)]",
  info: "bg-[var(--shadow-accent)]",
};

const severityCardBorders: Record<string, string> = {
  high: "border-l-[var(--color-risk-red)]",
  medium: "border-l-[var(--color-risk-amber)]",
  low: "border-l-[var(--color-risk-green)]",
  info: "border-l-[var(--shadow-accent)]",
};

/* ── Component ────────────────────────────────────────────── */

/**
 * Shadow Margin — persistent right-edge strip showing AI awareness.
 *
 * Collapsed (48px): Pulse dot + context thread dots + action seed
 * Expanded (320px): Card stack with insights, actions, and memory thread
 *
 * Desktop only (>= 1024px). Mobile uses bottom sheet (T128).
 */
export function ShadowMargin({
  insights,
  isLoading = false,
  observationInsights = [],
}: ShadowMarginProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const { openCommand } = useShadowAgent();

  const visibleInsights = insights.filter((i) => !dismissedIds.has(i.id));
  const visibleObservations = observationInsights.filter(
    (i) => !dismissedIds.has(i.id),
  );
  const hasInsights =
    visibleInsights.length > 0 || visibleObservations.length > 0;

  // Don't render on mobile/tablet
  const [isDesktop, setIsDesktop] = useState(false);
  useEffect(() => {
    const check = () => setIsDesktop(window.innerWidth >= 1024);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  if (!isDesktop || (!hasInsights && !isLoading)) return null;

  const dismissInsight = (id: string) => {
    setDismissedIds((prev) => new Set(prev).add(id));
  };

  return (
    <div
      className={clsx(
        "fixed top-0 right-0 h-full",
        "transition-[width] duration-[var(--shadow-transition-normal)] ease-out",
        "bg-[var(--color-surface-card)]",
        "border-l border-[var(--color-gray-200)]",
        isExpanded
          ? "w-[var(--shadow-margin-expanded)]"
          : "w-[var(--shadow-margin-collapsed)]",
      )}
      style={{ zIndex: "var(--z-shadow-margin)" }}
    >
      {/* ── Collapsed state ──────────────────────────────── */}
      {!isExpanded && (
        <div className="flex flex-col items-center h-full py-4 gap-4">
          {/* Shadow pulse dot */}
          <div
            className={clsx(
              "w-2 h-2 rounded-full",
              hasInsights
                ? "bg-[var(--shadow-accent)] animate-shadow-breathe"
                : "bg-[var(--color-gray-300)]",
            )}
            aria-hidden="true"
          />

          {/* Context thread dots */}
          <div className="flex flex-col gap-2">
            {visibleInsights.slice(0, 5).map((insight) => (
              <button
                key={insight.id}
                type="button"
                onClick={() => setIsExpanded(true)}
                className="group relative"
                aria-label={insight.title}
              >
                <span
                  className={clsx(
                    "block w-2 h-2 rounded-full transition-transform",
                    "hover:scale-150",
                    severityDotColors[insight.severity],
                  )}
                />
                {/* Tooltip — appears to the left */}
                <span className="absolute right-6 top-1/2 -translate-y-1/2 whitespace-nowrap bg-[var(--color-gray-900)] text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  {insight.title}
                </span>
              </button>
            ))}
          </div>

          {/* Expand button at bottom */}
          <button
            type="button"
            onClick={() => setIsExpanded(true)}
            className="mt-auto p-1.5 rounded-lg text-[var(--color-gray-400)] hover:text-[var(--foreground)] hover:bg-[var(--color-gray-100)] transition-colors"
            aria-label="Expand shadow margin"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* ── Expanded state ───────────────────────────────── */}
      {isExpanded && (
        <div className="flex flex-col h-full animate-shadow-fade-in">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-gray-200)]">
            <div className="flex items-center gap-2">
              <svg
                width="16"
                height="16"
                viewBox="0 0 18 18"
                fill="none"
                aria-hidden="true"
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
              <span className="text-sm font-medium text-[var(--foreground)]">
                AITE Insights
              </span>
              <span className="text-[10px] text-[var(--color-gray-400)]">
                {visibleInsights.length}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setIsExpanded(false)}
              className="p-1 rounded text-[var(--color-gray-400)] hover:text-[var(--foreground)] transition-colors"
              aria-label="Collapse margin"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* Insight cards */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
            {isLoading && (
              <div className="flex items-center gap-2 px-3 py-4 text-sm text-[var(--color-gray-500)]">
                <div className="h-4 w-4 rounded-full border-2 border-[var(--shadow-accent)] border-t-transparent animate-spin" />
                Loading insights...
              </div>
            )}

            {visibleInsights.map((insight) => (
              <div
                key={insight.id}
                className={clsx(
                  "rounded-lg p-3 border-l-2",
                  "bg-[var(--shadow-surface)]",
                  severityCardBorders[insight.severity],
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-[var(--foreground)] leading-snug">
                      {insight.title}
                    </p>
                    <p className="text-[11px] text-[var(--color-gray-500)] mt-0.5 leading-snug">
                      {insight.description}
                    </p>
                    {insight.provision && (
                      <span className="inline-block mt-1 text-[10px] font-medium text-[var(--color-authority-statutory)] bg-[var(--color-authority-statutory-bg)] rounded-full px-1.5 py-0.5">
                        {insight.provision}
                      </span>
                    )}
                    {insight.daysRemaining !== undefined && (
                      <span className="inline-block mt-1 ml-1 text-[10px] font-medium text-[var(--color-risk-amber)]">
                        {insight.daysRemaining} days
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => dismissInsight(insight.id)}
                    className="shrink-0 p-0.5 rounded text-[var(--color-gray-300)] hover:text-[var(--color-gray-500)] transition-colors"
                    aria-label={`Dismiss ${insight.title}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))}

            {/* T140: Proactive observation insights */}
            {visibleObservations.length > 0 && (
              <>
                {visibleInsights.length > 0 && (
                  <div className="my-2 border-t border-[var(--color-gray-200)]" />
                )}
                <p className="text-[10px] font-medium text-[var(--color-gray-400)] uppercase tracking-wider px-1 mb-1">
                  Patterns
                </p>
                {visibleObservations.map((obs) => (
                  <div
                    key={obs.id}
                    className="rounded-lg p-3 border-l-2 bg-[var(--shadow-surface)] border-l-[var(--shadow-accent)]"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <Lightbulb className="h-3 w-3 text-[var(--shadow-accent)]" />
                          <span className="text-[10px] font-medium text-[var(--shadow-accent)]">
                            Pattern detected
                          </span>
                        </div>
                        <p className="text-[11px] text-[var(--color-gray-500)] leading-snug">
                          {obs.message}
                        </p>
                        {obs.actionPrompt && (
                          <button
                            type="button"
                            onClick={() => {
                              setIsExpanded(false);
                              openCommand();
                            }}
                            className="mt-1.5 text-[10px] font-medium text-[var(--color-primary)] hover:underline"
                          >
                            {obs.actionPrompt}
                          </button>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => dismissInsight(obs.id)}
                        className="shrink-0 p-0.5 rounded text-[var(--color-gray-300)] hover:text-[var(--color-gray-500)] transition-colors"
                        aria-label={`Dismiss pattern`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </>
            )}

            {!isLoading &&
              visibleInsights.length === 0 &&
              visibleObservations.length === 0 && (
                <p className="text-xs text-[var(--color-gray-400)] text-center py-4">
                  No insights right now
                </p>
              )}
          </div>

          {/* Quick command bar at bottom */}
          <div className="px-3 py-2 border-t border-[var(--color-gray-200)]">
            <button
              type="button"
              onClick={() => {
                setIsExpanded(false);
                openCommand();
              }}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--color-gray-100)] text-sm text-[var(--color-gray-500)] hover:bg-[var(--color-gray-200)] transition-colors"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 18 18"
                fill="none"
                aria-hidden="true"
              >
                <circle cx="7" cy="9" r="5" fill="currentColor" opacity="0.4" />
                <ellipse
                  cx="12"
                  cy="9"
                  rx="4"
                  ry="3.5"
                  fill="currentColor"
                  opacity="0.15"
                />
              </svg>
              Ask AITE...
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
