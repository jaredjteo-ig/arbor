"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Clock,
  Check,
  X,
  RotateCcw,
  ChevronRight,
  Loader2,
} from "lucide-react";
import clsx from "clsx";
import {
  shadowApi,
  type ShadowAction,
  type ShadowHistoryResponse,
} from "@/services/api/shadow";

/* ── Types ────────────────────────────────────────────────── */

interface ArborHistoryProps {
  /** Whether the history panel is visible. */
  isOpen: boolean;
  /** Called when the user closes the panel. */
  onClose: () => void;
  /** Maximum number of actions to show. */
  limit?: number;
}

/* ── Helpers ──────────────────────────────────────────────── */

/** Group actions by day (YYYY-MM-DD). */
function groupByDay(actions: ShadowAction[]): Map<string, ShadowAction[]> {
  const groups = new Map<string, ShadowAction[]>();
  for (const action of actions) {
    const day = action.timestamp.slice(0, 10); // "2026-03-20"
    if (!groups.has(day)) {
      groups.set(day, []);
    }
    groups.get(day)!.push(action);
  }
  return groups;
}

/** Format a date string as "Today", "Yesterday", or "Mon 20 Mar". */
function formatDayLabel(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const diff = today.getTime() - date.getTime();
  const dayMs = 86_400_000;

  if (diff < dayMs) return "Today";
  if (diff < dayMs * 2) return "Yesterday";

  return date.toLocaleDateString("en-SG", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

/** Format ISO timestamp as "2:30 PM". */
function formatTime(isoStr: string): string {
  return new Date(isoStr).toLocaleTimeString("en-SG", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/** Human-readable action label. */
function actionLabel(action: ShadowAction): string {
  const mod = action.module.replace(/_/g, " ");
  const act = action.action.replace(/_/g, " ");
  return `${mod} — ${act}`;
}

/* ── Component ────────────────────────────────────────────── */

/**
 * ArborHistory (T473)
 *
 * Shows recent Arbor actions from GET /shadow/history.
 * Grouped by day, most recent first. Each entry shows action
 * description, time, status, and an undo option if within window.
 */
export function ArborHistory({
  isOpen,
  onClose,
  limit = 50,
}: ArborHistoryProps) {
  const [data, setData] = useState<ShadowHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await shadowApi.history(limit);
      setData(result);
    } catch {
      setError("Could not load action history.");
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    }
  }, [isOpen, fetchHistory]);

  if (!isOpen) return null;

  const groups = data ? groupByDay(data.actions) : new Map();

  return (
    <div
      className="fixed inset-y-0 right-0 z-[var(--z-shadow-margin,70)] w-80 bg-[var(--background)] border-l border-[var(--color-gray-200)] shadow-xl flex flex-col animate-in slide-in-from-right duration-200"
      role="complementary"
      aria-label="Central action history"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-gray-200)]">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-[var(--color-primary)]" />
          <h2 className="text-sm font-semibold text-[var(--foreground)]">
            Action History
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-md text-[var(--color-gray-500)] hover:bg-[var(--color-gray-100)] transition-colors"
          aria-label="Close history"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 text-[var(--color-primary)] animate-spin" />
          </div>
        )}

        {error && (
          <div className="px-4 py-6 text-center">
            <p className="text-sm text-[var(--color-gray-500)]">{error}</p>
            <button
              type="button"
              onClick={fetchHistory}
              className="mt-2 text-xs text-[var(--color-primary)] hover:underline"
            >
              Try again
            </button>
          </div>
        )}

        {!loading && !error && data && data.actions.length === 0 && (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-[var(--color-gray-500)]">
              No actions yet. Use the command palette to get started.
            </p>
          </div>
        )}

        {!loading &&
          !error &&
          Array.from(groups.entries()).map(
            ([day, actions]: [string, ShadowAction[]]) => (
              <div key={day}>
                {/* Day header */}
                <div className="sticky top-0 bg-[var(--color-gray-50)] px-4 py-1.5 border-b border-[var(--color-gray-100)]">
                  <span className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
                    {formatDayLabel(day)}
                  </span>
                </div>

                {/* Actions for this day */}
                {actions.map((action, i) => (
                  <div
                    key={`${day}-${i}`}
                    className="px-4 py-2.5 border-b border-[var(--color-gray-100)] hover:bg-[var(--color-gray-50)] transition-colors"
                  >
                    <div className="flex items-start gap-2.5">
                      {/* Status icon */}
                      <div className="mt-0.5">
                        {action.success ? (
                          <div className="flex h-4 w-4 items-center justify-center rounded-full bg-[var(--color-primary)]/20">
                            <Check className="h-2.5 w-2.5 text-[var(--color-primary)]" />
                          </div>
                        ) : (
                          <div className="flex h-4 w-4 items-center justify-center rounded-full bg-[var(--color-risk-red)]/20">
                            <X className="h-2.5 w-2.5 text-[var(--color-risk-red)]" />
                          </div>
                        )}
                      </div>

                      {/* Action details */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-[var(--foreground)] truncate">
                          {actionLabel(action)}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-[var(--color-gray-500)]">
                            {formatTime(action.timestamp)}
                          </span>
                          <span
                            className={clsx(
                              "text-xs px-1.5 py-0.5 rounded-full",
                              action.trust_level === "autonomous"
                                ? "bg-[var(--color-gray-100)] text-[var(--color-gray-500)]"
                                : action.trust_level === "double_confirm"
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
                            )}
                          >
                            {action.trust_level.replace(/_/g, " ")}
                          </span>
                        </div>
                      </div>

                      <ChevronRight className="h-4 w-4 text-[var(--color-gray-300)] shrink-0 mt-0.5" />
                    </div>
                  </div>
                ))}
              </div>
            ),
          )}
      </div>

      {/* Footer with total count */}
      {data && (
        <div className="px-4 py-2 border-t border-[var(--color-gray-200)] bg-[var(--color-gray-50)]">
          <p className="text-xs text-[var(--color-gray-500)]">
            Showing {data.showing} of {data.total} actions
          </p>
        </div>
      )}
    </div>
  );
}
