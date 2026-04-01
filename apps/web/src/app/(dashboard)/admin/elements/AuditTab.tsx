"use client";

import { AppCard, RiskTierBadge } from "@/components/design-system";
import type { RiskTierLevel } from "@/components/design-system";
import { Shield, FileText, AlertCircle } from "lucide-react";
import { useAdminMetrics, useAdminRecommendations } from "@/hooks/api/useAdmin";

/* ── Loading skeletons ───────────────────────────────────── */

function SummarySkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse flex flex-wrap items-center gap-6">
        <div className="space-y-1">
          <div className="h-3 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-6 w-16 bg-[var(--color-gray-200)] rounded" />
        </div>
        <div className="h-8 w-px bg-[var(--color-gray-200)]" />
        <div className="space-y-1">
          <div className="h-3 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-6 w-16 bg-[var(--color-gray-200)] rounded" />
        </div>
      </div>
    </AppCard>
  );
}

function CardSkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse space-y-3">
        <div className="flex justify-between">
          <div className="h-6 w-20 bg-[var(--color-gray-200)] rounded-full" />
          <div className="h-4 w-12 bg-[var(--color-gray-200)] rounded" />
        </div>
        <div className="h-4 w-full bg-[var(--color-gray-200)] rounded" />
        <div className="h-4 w-3/4 bg-[var(--color-gray-200)] rounded" />
      </div>
    </AppCard>
  );
}

/* ── Priority to risk tier mapping ───────────────────────── */

function priorityToTier(priority: string): RiskTierLevel {
  if (priority === "critical" || priority === "high") return "red";
  if (priority === "medium") return "amber";
  return "green";
}

/* ── Recommendation card ─────────────────────────────────── */

function RecommendationCard({
  title,
  description,
  priority,
  type,
  status,
  evidenceCount,
  affectedDomains,
}: {
  title: string;
  description: string;
  priority: string;
  type: string;
  status: string;
  evidenceCount: number;
  affectedDomains: string[];
}) {
  const tier = priorityToTier(priority);

  return (
    <AppCard variant="flat" className="hover:shadow-md transition-shadow">
      <div className="space-y-3">
        {/* Header: risk tier + status */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <RiskTierBadge tier={tier} />
          <span className="text-xs font-medium text-[var(--color-gray-500)] uppercase">
            {(status || "pending").replace(/_/g, " ")}
          </span>
        </div>

        {/* Title + type */}
        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <Shield className="h-3.5 w-3.5 text-[var(--color-gray-400)]" />
            <span className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
              {type.replace(/_/g, " ")}
            </span>
          </div>
          <p className="text-sm font-medium text-[var(--color-gray-900)]">
            {title}
          </p>
        </div>

        {/* Description */}
        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <FileText className="h-3.5 w-3.5 text-[var(--color-gray-400)]" />
            <span className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
              Description
            </span>
          </div>
          <p className="text-sm text-[var(--color-gray-700)] leading-relaxed">
            {description}
          </p>
        </div>

        {/* Metadata */}
        <div className="flex flex-wrap gap-4 text-xs text-[var(--color-gray-500)]">
          <span>{evidenceCount} supporting evidence</span>
          {affectedDomains.length > 0 && (
            <span>Affects: {affectedDomains.join(", ")}</span>
          )}
        </div>
      </div>
    </AppCard>
  );
}

/* ── Audit Tab ────────────────────────────────────────────── */

export function AuditTab() {
  const { data: metrics, isLoading: metricsLoading } = useAdminMetrics();
  const {
    data: recsData,
    isLoading: recsLoading,
    error: recsError,
  } = useAdminRecommendations();

  const isLoading = metricsLoading || recsLoading;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <SummarySkeleton />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (recsError) {
    return (
      <AppCard
        variant="flat"
        className="border-l-4 border-l-[var(--color-risk-red)]"
      >
        <div className="flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-[var(--color-risk-red)]" />
          <div>
            <p className="text-sm font-medium text-[var(--color-gray-900)]">
              Failed to load audit data
            </p>
            <p className="text-xs text-[var(--color-gray-500)]">
              {recsError.message}
            </p>
          </div>
        </div>
      </AppCard>
    );
  }

  const recommendations = recsData?.recommendations ?? [];
  const avgConfidence = metrics ? Math.round(metrics.avg_confidence * 100) : 0;
  const riskDist = metrics?.risk_distribution ?? {};

  return (
    <div className="space-y-6">
      {/* Summary */}
      <AppCard variant="flat">
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
              Recommendations
            </p>
            <p className="text-xl font-bold text-[var(--color-gray-900)] mt-0.5">
              {recommendations.length} total
            </p>
          </div>
          <div className="h-8 w-px bg-[var(--color-gray-200)]" />
          <div>
            <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
              Avg Confidence
            </p>
            <p className="text-xl font-bold text-[var(--color-gray-900)] mt-0.5">
              {avgConfidence}%
            </p>
          </div>
          <div className="h-8 w-px bg-[var(--color-gray-200)]" />
          <div className="flex items-center gap-3">
            {(["green", "amber", "red"] as const).map((tier) => (
              <div key={tier} className="flex items-center gap-1.5">
                <RiskTierBadge tier={tier} className="text-xs" />
                <span className="text-sm font-medium text-[var(--color-gray-700)]">
                  {riskDist[tier] ?? 0}
                </span>
              </div>
            ))}
          </div>
        </div>
      </AppCard>

      {/* Recommendations list */}
      <div>
        <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
          Improvement Recommendations
        </h3>
        {recommendations.length === 0 ? (
          <AppCard variant="flat">
            <p className="text-sm text-[var(--color-gray-500)] text-center py-4">
              No recommendations from the learning pipeline yet. Recommendations
              will appear here as usage patterns are analyzed.
            </p>
          </AppCard>
        ) : (
          <div className="space-y-4">
            {recommendations.map((rec) => (
              <RecommendationCard
                key={rec.recommendation_id}
                title={rec.title}
                description={rec.description}
                priority={rec.priority}
                type={rec.type}
                status={rec.status}
                evidenceCount={rec.evidence_count}
                affectedDomains={rec.affected_domains}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
