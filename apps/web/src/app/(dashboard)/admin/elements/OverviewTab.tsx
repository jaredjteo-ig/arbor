"use client";

import { AppCard, RiskTierBadge } from "@/components/design-system";
import type { RiskTierLevel } from "@/components/design-system";
import {
  Users,
  MessageSquare,
  TrendingUp,
  BookOpen,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useAdminMetrics } from "@/hooks/api/useAdmin";

/* ── Skeleton placeholder ────────────────────────────────── */

function MetricSkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse space-y-2">
        <div className="h-3 w-20 bg-[var(--color-gray-200)] rounded" />
        <div className="h-7 w-12 bg-[var(--color-gray-200)] rounded" />
      </div>
    </AppCard>
  );
}

function ChartSkeleton() {
  return (
    <AppCard
      header={
        <div className="h-4 w-40 bg-[var(--color-gray-200)] rounded animate-pulse" />
      }
    >
      <div className="animate-pulse space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="h-6 w-[120px] bg-[var(--color-gray-200)] rounded-full" />
            <div className="flex-1 h-6 bg-[var(--color-gray-100)] rounded-full" />
            <div className="h-4 w-10 bg-[var(--color-gray-200)] rounded" />
          </div>
        ))}
      </div>
    </AppCard>
  );
}

/* ── Risk distribution bar ────────────────────────────────── */

const RISK_COLORS: Record<RiskTierLevel, string> = {
  green: "var(--color-risk-green)",
  amber: "var(--color-risk-amber)",
  red: "var(--color-risk-red)",
};

function RiskDistributionChart({
  distribution,
}: {
  distribution: Record<string, number>;
}) {
  const tiers: RiskTierLevel[] = ["green", "amber", "red"];
  const total = tiers.reduce((sum, t) => sum + (distribution[t] ?? 0), 0);

  return (
    <AppCard
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Risk Tier Distribution
          </h3>
          <span className="text-xs text-[var(--color-gray-500)]">
            {total} total queries
          </span>
        </div>
      }
    >
      <div className="space-y-3">
        {tiers.map((tier) => {
          const count = distribution[tier] ?? 0;
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          return (
            <div key={tier} className="flex items-center gap-3">
              <RiskTierBadge tier={tier} className="w-[120px] justify-center" />
              <div className="flex-1 h-6 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: RISK_COLORS[tier],
                  }}
                />
              </div>
              <span className="text-sm font-medium text-[var(--color-gray-700)] w-10 text-right">
                {count}
              </span>
            </div>
          );
        })}
      </div>
    </AppCard>
  );
}

/* ── Summary stats card ──────────────────────────────────── */

function SummaryStatsCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  icon: typeof Users;
  color: string;
}) {
  return (
    <AppCard variant="flat">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            {label}
          </p>
          <p className="text-2xl font-bold text-[var(--color-gray-900)] mt-1">
            {value}
          </p>
        </div>
        <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
          <Icon className="h-5 w-5" style={{ color }} />
        </div>
      </div>
    </AppCard>
  );
}

/* ── Overview Tab ─────────────────────────────────────────── */

export function OverviewTab() {
  const { data: metrics, isLoading, error } = useAdminMetrics();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <MetricSkeleton key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
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
          <div>
            <p className="text-sm font-medium text-[var(--color-gray-900)]">
              Failed to load dashboard metrics
            </p>
            <p className="text-xs text-[var(--color-gray-500)]">
              {error.message}
            </p>
          </div>
        </div>
      </AppCard>
    );
  }

  if (!metrics) return null;

  const avgConfidencePct = Math.round(metrics.avg_confidence * 100);

  return (
    <div className="space-y-6">
      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryStatsCard
          label="Queries Tracked"
          value={metrics.queries_tracked.toLocaleString()}
          icon={MessageSquare}
          color="var(--color-primary)"
        />
        <SummaryStatsCard
          label="Avg Confidence"
          value={`${avgConfidencePct}%`}
          icon={TrendingUp}
          color="var(--color-risk-green)"
        />
        <SummaryStatsCard
          label="KB Provisions"
          value={metrics.kb_provisions.toLocaleString()}
          icon={BookOpen}
          color="var(--color-primary)"
        />
        <SummaryStatsCard
          label="Feedback Count"
          value={metrics.feedback_count.toLocaleString()}
          icon={Users}
          color="var(--color-primary)"
        />
      </div>

      {/* Pending updates callout */}
      {metrics.pending_updates > 0 && (
        <AppCard
          variant="flat"
          className="border-l-4 border-l-[var(--color-risk-amber)]"
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold text-[var(--color-risk-amber)]">
              {metrics.pending_updates}
            </span>
            <div>
              <p className="text-sm font-medium text-[var(--color-gray-900)]">
                Pending Regulatory{" "}
                {metrics.pending_updates === 1 ? "Update" : "Updates"}
              </p>
              <p className="text-xs text-[var(--color-gray-500)]">
                Awaiting review before{" "}
                {metrics.pending_updates === 1 ? "it" : "they"} can be published
                to the knowledge base
              </p>
            </div>
          </div>
        </AppCard>
      )}

      {/* Risk distribution + KB health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RiskDistributionChart distribution={metrics.risk_distribution} />

        {/* KB health summary */}
        <AppCard
          header={
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Knowledge Base Health
            </h3>
          }
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--color-gray-600)]">
                Domains
              </span>
              <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                {metrics.kb_domains}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--color-gray-600)]">
                Acts Covered
              </span>
              <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                {metrics.kb_acts}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--color-gray-600)]">
                KB Gaps Detected
              </span>
              <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                {metrics.kb_gaps}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--color-gray-600)]">
                Pending Recommendations
              </span>
              <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                {metrics.pending_recommendations}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--color-gray-600)]">
                Published Updates
              </span>
              <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                {metrics.published_updates}
              </span>
            </div>
          </div>
        </AppCard>
      </div>
    </div>
  );
}
