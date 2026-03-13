"use client";

import { AppButton, AppCard } from "@/components/design-system";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { useCompleteSession, useQaEvaluations } from "@/hooks/api/useQa";
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

/* ── Props ───────────────────────────────────────────────── */

interface SessionSummaryViewProps {
  session: QASession;
  onCompleted: () => void;
}

/* ── Skeleton ────────────────────────────────────────────── */

function SummarySkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      {Array.from({ length: 8 }, (_, i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="h-4 w-36 bg-[var(--color-gray-200)] rounded" />
          <div className="flex-1 h-6 bg-[var(--color-gray-200)] rounded-full" />
          <div className="h-4 w-14 bg-[var(--color-gray-200)] rounded" />
        </div>
      ))}
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────── */

export function SessionSummaryView({
  session,
  onCompleted,
}: SessionSummaryViewProps) {
  const completeSession = useCompleteSession();
  const { data: evalData, isLoading: evalsLoading } = useQaEvaluations(
    Number(session.id),
  );

  const maxScore = 5;

  /* Compute aggregate dimension scores from evaluations */
  const evaluations = evalData?.evaluations ?? [];

  const scoreFields = [
    { key: "score_legal_accuracy", label: "Legal Accuracy" },
    { key: "score_contextual_relevance", label: "Contextual Relevance" },
    { key: "score_coherence", label: "Coherence" },
    { key: "score_actionability", label: "Actionability" },
    { key: "score_risk_awareness", label: "Risk Awareness" },
    { key: "score_citation_quality", label: "Citation Quality" },
    { key: "score_language", label: "Language Understanding" },
    { key: "score_completeness", label: "Completeness" },
  ] as const;

  const dimensionScores =
    evaluations.length > 0
      ? scoreFields.map(({ key, label }) => {
          const avg =
            evaluations.reduce((sum, e) => sum + (e[key] as number), 0) /
            evaluations.length;
          return {
            dimension: label,
            average_score: Math.round(avg * 100) / 100,
          };
        })
      : [];

  const overallScore =
    dimensionScores.length > 0
      ? dimensionScores.reduce((sum, d) => sum + d.average_score, 0) /
        dimensionScores.length
      : null;

  /* Failure category breakdown */
  const failureCounts: Record<string, number> = {};
  for (const e of evaluations) {
    if (e.has_material_correction && e.failure_category) {
      failureCounts[e.failure_category] =
        (failureCounts[e.failure_category] ?? 0) + 1;
    }
  }
  const failureCategories = Object.entries(failureCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([category, count]) => ({ category, count }));
  const totalFailures = failureCategories.reduce((sum, f) => sum + f.count, 0);

  function handleComplete() {
    completeSession.mutate(String(session.id), {
      onSuccess: () => {
        onCompleted();
      },
    });
  }

  if (evalsLoading) {
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
          Session Summary
        </h3>
        <AppCard variant="flat">
          <SummarySkeleton />
        </AppCard>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with overall score */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Session Summary
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            {evaluations.length} evaluation{evaluations.length !== 1 ? "s" : ""}{" "}
            completed
          </p>
        </div>
        {overallScore !== null && (
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-semibold"
            style={{
              color: scoreColor(overallScore),
              backgroundColor: scoreBgColor(overallScore),
              borderColor: scoreColor(overallScore),
            }}
          >
            Overall: {overallScore.toFixed(1)} / {maxScore}
          </div>
        )}
      </div>

      {/* Dimension scores bar chart */}
      {dimensionScores.length > 0 && (
        <AppCard
          variant="flat"
          header={
            <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Per-Dimension Scores
            </h4>
          }
        >
          <div className="space-y-3">
            {dimensionScores.map((dim) => {
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
      {failureCategories.length > 0 && (
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
            {failureCategories.map((fail) => {
              const pct =
                totalFailures > 0
                  ? Math.round((fail.count / totalFailures) * 100)
                  : 0;
              return (
                <div key={fail.category} className="flex items-center gap-3">
                  <span className="text-sm text-[var(--color-gray-700)] w-36 shrink-0 truncate">
                    {fail.category.replace(/_/g, " ")}
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

      {/* Empty state */}
      {dimensionScores.length === 0 && failureCategories.length === 0 && (
        <AppCard variant="flat">
          <p className="text-sm text-[var(--color-gray-500)] text-center py-6">
            No scoring data available yet.
          </p>
        </AppCard>
      )}

      {/* Complete Session button */}
      {session.status === "active" && (
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-2 text-sm text-[var(--color-gray-500)]">
            <CheckCircle2 className="h-4 w-4" />
            <span>
              All conversations reviewed. Ready to complete this session.
            </span>
          </div>
          <AppButton
            size="sm"
            onClick={handleComplete}
            loading={completeSession.isPending}
          >
            Complete Session
          </AppButton>
        </div>
      )}

      {/* Complete error */}
      {completeSession.isError && (
        <div className="flex items-start gap-2 text-sm text-[var(--color-error)]">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{completeSession.error.message}</span>
        </div>
      )}
    </div>
  );
}
