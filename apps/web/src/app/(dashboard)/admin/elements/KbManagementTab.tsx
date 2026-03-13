"use client";

import { AppCard } from "@/components/design-system";
import { BookOpen, AlertTriangle, AlertCircle } from "lucide-react";
import {
  useAdminMetrics,
  useStalenessSummary,
  useAdminKbGaps,
} from "@/hooks/api/useAdmin";

/* ── Staleness dot ────────────────────────────────────────── */

type StalenessLevel = "current" | "review-soon" | "stale";

const STALENESS_CONFIG: Record<
  StalenessLevel,
  { color: string; label: string }
> = {
  current: { color: "var(--color-risk-green)", label: "Current" },
  "review-soon": { color: "var(--color-risk-amber)", label: "Review soon" },
  stale: { color: "var(--color-risk-red)", label: "Stale" },
};

function StalenessDot({ staleness }: { staleness: StalenessLevel }) {
  const { color, label } = STALENESS_CONFIG[staleness];
  return (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span
        className="h-2.5 w-2.5 rounded-full shrink-0"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />
      <span className="text-[var(--color-gray-600)]">{label}</span>
    </span>
  );
}

/* ── Loading skeletons ────────────────────────────────────── */

function SummarySkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse flex flex-wrap items-center gap-6">
        <div className="space-y-1">
          <div className="h-3 w-32 bg-[var(--color-gray-200)] rounded" />
          <div className="h-6 w-16 bg-[var(--color-gray-200)] rounded" />
        </div>
        <div className="h-8 w-px bg-[var(--color-gray-200)]" />
        <div className="h-5 w-20 bg-[var(--color-gray-200)] rounded" />
        <div className="h-5 w-20 bg-[var(--color-gray-200)] rounded" />
      </div>
    </AppCard>
  );
}

function DomainCardSkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse space-y-3">
        <div className="flex items-start justify-between">
          <div className="h-9 w-9 bg-[var(--color-gray-200)] rounded-lg" />
          <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded" />
        </div>
        <div className="h-4 w-28 bg-[var(--color-gray-200)] rounded" />
        <div className="flex justify-between">
          <div className="h-3 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-3 w-24 bg-[var(--color-gray-200)] rounded" />
        </div>
      </div>
    </AppCard>
  );
}

/* ── Staleness Summary (from API) ─────────────────────────── */

function StalenessSummaryBar() {
  const { data: staleness, isLoading, error } = useStalenessSummary();
  const { data: metrics } = useAdminMetrics();

  if (isLoading) return <SummarySkeleton />;

  if (error) {
    return (
      <AppCard
        variant="flat"
        className="border-l-4 border-l-[var(--color-risk-red)]"
      >
        <div className="flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-[var(--color-risk-red)]" />
          <p className="text-sm text-[var(--color-gray-700)]">
            Failed to load staleness data: {error.message}
          </p>
        </div>
      </AppCard>
    );
  }

  const totalProvisions = metrics?.kb_provisions ?? staleness?.total ?? 0;
  const staleCount = staleness?.stale ?? 0;
  const reviewSoonCount = staleness?.review_soon ?? 0;

  return (
    <AppCard variant="flat">
      <div className="flex flex-wrap items-center gap-6">
        <div>
          <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Total Provisions Tracked
          </p>
          <p className="text-xl font-bold text-[var(--color-gray-900)] mt-0.5">
            {totalProvisions}
          </p>
        </div>
        <div className="h-8 w-px bg-[var(--color-gray-200)]" />
        <div className="flex items-center gap-2">
          <span
            className="h-3 w-3 rounded-full shrink-0"
            style={{ backgroundColor: "var(--color-risk-red)" }}
          />
          <div>
            <p className="text-sm font-semibold text-[var(--color-risk-red)]">
              {staleCount} stale
            </p>
            <p className="text-xs text-[var(--color-gray-500)]">
              Past review date
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="h-3 w-3 rounded-full shrink-0"
            style={{ backgroundColor: "var(--color-risk-amber)" }}
          />
          <div>
            <p className="text-sm font-semibold text-[var(--color-risk-amber)]">
              {reviewSoonCount} upcoming
            </p>
            <p className="text-xs text-[var(--color-gray-500)]">
              Review within 30 days
            </p>
          </div>
        </div>
      </div>
    </AppCard>
  );
}

/* ── KB Gaps Grid ─────────────────────────────────────────── */

function KbGapsGrid() {
  const { data: gapsData, isLoading, error } = useAdminKbGaps();
  const { data: metrics } = useAdminMetrics();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <DomainCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <AppCard
        variant="flat"
        className="border-l-4 border-l-[var(--color-risk-red)]"
      >
        <div className="flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-[var(--color-risk-red)]" />
          <p className="text-sm text-[var(--color-gray-700)]">
            Failed to load KB data: {error.message}
          </p>
        </div>
      </AppCard>
    );
  }

  // If we have KB gaps, show them as domain-style cards
  const gaps = gapsData?.gaps ?? [];
  const kbDomains = metrics?.kb_domains ?? 0;

  if (gaps.length === 0) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Show a summary card with domain count from metrics */}
        <AppCard variant="flat" className="hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between mb-3">
            <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
              <BookOpen className="h-5 w-5 text-[var(--color-primary)]" />
            </div>
            <StalenessDot staleness="current" />
          </div>
          <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
            All Domains
          </h4>
          <div className="mt-2 flex items-center justify-between">
            <p className="text-xs text-[var(--color-gray-500)]">
              {kbDomains} domains covered
            </p>
            <p className="text-xs text-[var(--color-gray-400)]">
              {metrics?.kb_provisions ?? 0} provisions
            </p>
          </div>
        </AppCard>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {gaps.map((gap) => {
        const staleness: StalenessLevel =
          gap.priority === "critical" || gap.priority === "high"
            ? "stale"
            : gap.priority === "medium"
              ? "review-soon"
              : "current";

        return (
          <AppCard
            key={gap.gap_id}
            variant="flat"
            className="hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
                <BookOpen className="h-5 w-5 text-[var(--color-primary)]" />
              </div>
              <StalenessDot staleness={staleness} />
            </div>
            <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
              {gap.domains.join(", ") || "General"}
            </h4>
            <p className="text-xs text-[var(--color-gray-500)] mt-1 line-clamp-2">
              {gap.description}
            </p>
            <div className="mt-2 flex items-center justify-between">
              <p className="text-xs text-[var(--color-gray-500)]">
                {gap.evidence_query_count} queries
              </p>
              <p className="text-xs text-[var(--color-gray-400)]">
                {gap.negative_feedback_count} negative feedback
              </p>
            </div>
            {staleness === "stale" && (
              <div className="mt-3 flex items-center gap-1.5 text-xs text-[var(--color-risk-red)]">
                <AlertTriangle className="h-3.5 w-3.5" />
                <span>Needs immediate attention</span>
              </div>
            )}
          </AppCard>
        );
      })}
    </div>
  );
}

/* ── KB Management Tab ────────────────────────────────────── */

export function KbManagementTab() {
  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <StalenessSummaryBar />

      {/* Domain / gaps grid */}
      <div>
        <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
          Knowledge Base Gaps
        </h3>
        <KbGapsGrid />
      </div>
    </div>
  );
}
