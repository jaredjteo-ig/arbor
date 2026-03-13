"use client";

import { AppCard } from "@/components/design-system";
import { AlertCircle } from "lucide-react";
import {
  useQaSessions,
  useQaEvaluations,
  useQaPatches,
} from "@/hooks/api/useQa";
import { QualityTrendChart } from "./QualityTrendChart";
import { DimensionTrendChart } from "./DimensionTrendChart";
import { FailureHeatmap } from "./FailureHeatmap";
import { PatchHistoryTable } from "./PatchHistoryTable";
import { KBGapDetector } from "./KBGapDetector";

/* ── Skeleton ────────────────────────────────────────────── */

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      {/* Top card skeleton */}
      <AppCard variant="flat" className="overflow-hidden">
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-40 bg-[var(--color-gray-200)] rounded" />
          <div className="h-[180px] bg-[var(--color-gray-100)] rounded" />
        </div>
      </AppCard>

      {/* Side-by-side skeletons */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AppCard variant="flat" className="overflow-hidden">
          <div className="animate-pulse space-y-3">
            <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded" />
            <div className="h-[160px] bg-[var(--color-gray-100)] rounded" />
          </div>
        </AppCard>
        <AppCard variant="flat" className="overflow-hidden">
          <div className="animate-pulse space-y-3">
            <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded" />
            <div className="h-[160px] bg-[var(--color-gray-100)] rounded" />
          </div>
        </AppCard>
      </div>

      {/* Bottom side-by-side skeletons */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AppCard variant="flat" className="overflow-hidden">
          <div className="animate-pulse space-y-3">
            <div className="h-4 w-36 bg-[var(--color-gray-200)] rounded" />
            {Array.from({ length: 4 }, (_, i) => (
              <div key={i} className="h-4 bg-[var(--color-gray-200)] rounded" />
            ))}
          </div>
        </AppCard>
        <AppCard variant="flat" className="overflow-hidden">
          <div className="animate-pulse space-y-3">
            <div className="h-4 w-36 bg-[var(--color-gray-200)] rounded" />
            {Array.from({ length: 3 }, (_, i) => (
              <div
                key={i}
                className="h-10 bg-[var(--color-gray-200)] rounded"
              />
            ))}
          </div>
        </AppCard>
      </div>
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────── */

export function QAMetricsDashboard() {
  /*
   * Fetch all three data sources. Each hook is a separate component concern,
   * but for a dashboard that cross-references all three, we co-locate them
   * and pass data down to pure-presentational child components.
   */
  const sessionsQuery = useQaSessions(undefined, 1, 1000);
  const evaluationsQuery = useQaEvaluations();
  const patchesQuery = useQaPatches();

  /* ── Loading ─────────────────────────────────────────────── */
  const isLoading =
    sessionsQuery.isLoading ||
    evaluationsQuery.isLoading ||
    patchesQuery.isLoading;

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            QA Metrics Dashboard
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Loading quality metrics...
          </p>
        </div>
        <DashboardSkeleton />
      </div>
    );
  }

  /* ── Error ──────────────────────────────────────────────── */
  const firstError =
    sessionsQuery.error ?? evaluationsQuery.error ?? patchesQuery.error;

  if (firstError) {
    return (
      <AppCard
        variant="flat"
        className="border-l-4 border-l-[var(--color-risk-red)]"
      >
        <div className="flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-[var(--color-risk-red)]" />
          <div>
            <p className="text-sm font-medium text-[var(--color-gray-900)]">
              Failed to load QA metrics
            </p>
            <p className="text-xs text-[var(--color-gray-500)]">
              {firstError.message}
            </p>
          </div>
        </div>
      </AppCard>
    );
  }

  /* ── Data ───────────────────────────────────────────────── */
  const sessions = sessionsQuery.data?.sessions ?? [];
  const evaluations = evaluationsQuery.data?.evaluations ?? [];
  const patches = patchesQuery.data?.patches ?? [];

  const completedSessions = sessions.filter((s) => s.status === "completed");
  const totalEvaluations = evaluations.length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
          QA Metrics Dashboard
        </h3>
        <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
          {completedSessions.length} completed session
          {completedSessions.length !== 1 ? "s" : ""} &middot;{" "}
          {totalEvaluations} evaluation{totalEvaluations !== 1 ? "s" : ""}{" "}
          &middot; {patches.length} patch
          {patches.length !== 1 ? "es" : ""}
        </p>
      </div>

      {/* Row 1: Quality trend (full width) */}
      <QualityTrendChart sessions={sessions} />

      {/* Row 2: Dimension trends + Failure heatmap (side by side) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DimensionTrendChart sessions={sessions} />
        <FailureHeatmap evaluations={evaluations} patches={patches} />
      </div>

      {/* Row 3: Patch history + KB gap detector (side by side) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <PatchHistoryTable patches={patches} />
        <KBGapDetector evaluations={evaluations} />
      </div>
    </div>
  );
}
