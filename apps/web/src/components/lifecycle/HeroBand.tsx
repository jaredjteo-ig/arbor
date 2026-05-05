"use client";

/* Hero band — workforce strategy summary at the top of the lifecycle page.
   "Edit Plan" is disabled in Phase 1 (WorkforcePlan ships in Phase 3).
*/

import { Sparkles, Lock } from "lucide-react";
import type { LifecycleHero } from "@/services/api/strategy";

interface Props {
  hero: LifecycleHero;
}

function trendArrow(delta: number): string {
  if (delta === 0) return "→";
  return delta > 0 ? "↑" : "↓";
}

export function HeroBand({ hero }: Props) {
  const delta = hero.headcount_actual - hero.headcount_target;

  return (
    <div className="rounded-xl border border-[var(--color-gray-200)] bg-gradient-to-br from-white to-[var(--color-surface-page)] p-5 sm:p-6 shadow-sm">
      <div className="flex items-start justify-between gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Sparkles
            className="h-4 w-4 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
            Workforce strategy
          </h2>
          <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-400)]">
            Live
          </span>
        </div>
        <button
          type="button"
          disabled
          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-gray-200)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--color-gray-400)] cursor-not-allowed"
          title="Plan authoring ships in a future release"
        >
          <Lock className="h-3 w-3" aria-hidden="true" />
          Edit plan (coming soon)
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)]">
            Headcount
          </p>
          <p className="mt-1 text-2xl font-bold text-[var(--color-gray-900)] tabular-nums">
            {hero.headcount_actual}
            <span className="text-sm font-normal text-[var(--color-gray-400)]">
              {" / "}
              {hero.headcount_target}
            </span>
          </p>
          <p className="mt-0.5 text-[11px] text-[var(--color-gray-500)] tabular-nums">
            {trendArrow(delta)} {Math.abs(delta)} vs target
          </p>
        </div>
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)]">
            Open roles
          </p>
          <p className="mt-1 text-2xl font-bold text-[var(--color-gray-900)] tabular-nums">
            {hero.open_jobs}
          </p>
          <p className="mt-0.5 text-[11px] text-[var(--color-gray-500)] tabular-nums">
            {hero.stale_jobs > 0
              ? `${hero.stale_jobs} stale (≥14d)`
              : "all fresh"}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)]">
            Critical roles at risk
          </p>
          <p className="mt-1 text-2xl font-bold text-[var(--color-gray-900)] tabular-nums">
            {hero.critical_roles_at_risk}
          </p>
          <p className="mt-0.5 text-[11px] text-[var(--color-gray-500)]">
            Succession plan ships later
          </p>
        </div>
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)]">
            Churn YTD
          </p>
          <p className="mt-1 text-2xl font-bold text-[var(--color-gray-900)] tabular-nums">
            {hero.churn_ytd_pct.toFixed(1)}%
          </p>
          <p className="mt-0.5 text-[11px] text-[var(--color-gray-500)] tabular-nums">
            {hero.churn_yoy_delta === 0
              ? "flat YoY"
              : `${hero.churn_yoy_delta > 0 ? "+" : ""}${hero.churn_yoy_delta.toFixed(1)} ppt YoY`}
          </p>
        </div>
      </div>
    </div>
  );
}
