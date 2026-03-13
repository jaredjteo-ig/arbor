"use client";

import { AppCard } from "@/components/design-system";
import type { QASession } from "@/types/api";

/* ── Score bar colours ────────────────────────────────────── */

function scoreColor(score: number): string {
  if (score >= 4) return "var(--color-risk-green)";
  if (score >= 2.5) return "var(--color-risk-amber)";
  return "var(--color-risk-red)";
}

function scoreBgColor(score: number): string {
  if (score >= 4) return "var(--color-risk-green-bg)";
  if (score >= 2.5) return "var(--color-risk-amber-bg)";
  return "var(--color-risk-red-bg)";
}

/* ── Session Summary Component ────────────────────────────── */

interface SessionSummaryProps {
  session: QASession;
  onClose: () => void;
}

export function SessionSummary({ session, onClose }: SessionSummaryProps) {
  const dimensions = session.dimension_scores ?? [];
  const failures = session.failure_categories ?? [];
  const maxScore = 5;
  const totalFailures = failures.reduce((sum, f) => sum + f.count, 0);

  return (
    <div className="space-y-4">
      {/* Back link */}
      <button
        type="button"
        onClick={onClose}
        className="text-sm font-medium text-[var(--color-primary)] hover:underline"
      >
        Back to sessions list
      </button>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Session Scorecard
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Reviewed by {session.reviewer_name} &middot;{" "}
            {session.conversation_count} conversations &middot; Completed{" "}
            {session.completed_at
              ? new Date(session.completed_at).toLocaleDateString()
              : "N/A"}
          </p>
        </div>
        {session.average_overall_score !== null && (
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-semibold"
            style={{
              color: scoreColor(session.average_overall_score),
              backgroundColor: scoreBgColor(session.average_overall_score),
              borderColor: scoreColor(session.average_overall_score),
            }}
          >
            Overall: {session.average_overall_score.toFixed(1)} / {maxScore}
          </div>
        )}
      </div>

      {/* Dimension scores bar chart */}
      {dimensions.length > 0 && (
        <AppCard
          variant="flat"
          header={
            <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Per-Dimension Scores
            </h4>
          }
        >
          <div className="space-y-3">
            {dimensions.map((dim) => {
              const pct = Math.round((dim.average_score / maxScore) * 100);
              return (
                <div key={dim.dimension} className="flex items-center gap-3">
                  <span className="text-sm text-[var(--color-gray-700)] w-36 shrink-0 truncate">
                    {dim.dimension}
                  </span>
                  <div className="flex-1 h-6 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: scoreColor(dim.average_score),
                      }}
                    />
                  </div>
                  <span className="text-sm font-medium text-[var(--color-gray-700)] w-14 text-right shrink-0">
                    {dim.average_score.toFixed(1)} / {maxScore}
                  </span>
                </div>
              );
            })}
          </div>
        </AppCard>
      )}

      {/* Failure category breakdown */}
      {failures.length > 0 && (
        <AppCard
          variant="flat"
          header={
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
                Failure Categories
              </h4>
              <span className="text-xs text-[var(--color-gray-500)]">
                {totalFailures} total failure{totalFailures !== 1 ? "s" : ""}
              </span>
            </div>
          }
        >
          <div className="space-y-3">
            {failures.map((fail) => {
              const pct =
                totalFailures > 0
                  ? Math.round((fail.count / totalFailures) * 100)
                  : 0;
              return (
                <div key={fail.category} className="flex items-center gap-3">
                  <span className="text-sm text-[var(--color-gray-700)] w-36 shrink-0 truncate">
                    {fail.category}
                  </span>
                  <div className="flex-1 h-6 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500 bg-[var(--color-risk-red)]"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-[var(--color-gray-700)] w-10 text-right shrink-0">
                    {fail.count}
                  </span>
                </div>
              );
            })}
          </div>
        </AppCard>
      )}

      {/* Empty state when there are no scores yet */}
      {dimensions.length === 0 && failures.length === 0 && (
        <AppCard variant="flat">
          <p className="text-sm text-[var(--color-gray-500)] text-center py-6">
            No scoring data available for this session.
          </p>
        </AppCard>
      )}
    </div>
  );
}
