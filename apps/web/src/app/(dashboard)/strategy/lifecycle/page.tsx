"use client";

/* Strategy → Lifecycle dashboard.
   The Cox 8-stage Employee Lifecycle as the platform's organising surface.
   Spec: workspaces/obayashi/02-plans/02-lifecycle-dashboard-spec.md
*/

import { useEffect, useState } from "react";
import { Sparkles, RefreshCw, AlertCircle } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import { useAuth } from "@/contexts/AuthContext";
import {
  strategyApi,
  type LifecycleDashboardResponse,
  type LifecycleStageKey,
} from "@/services/api/strategy";
import { StageGrid } from "@/components/lifecycle/StageGrid";
import { StageDetailPanel } from "@/components/lifecycle/StageDetailPanel";
import { DiSnapshotTile } from "@/components/lifecycle/DiSnapshotTile";
import { ActivityFeed } from "@/components/lifecycle/ActivityFeed";
import { HeroBand } from "@/components/lifecycle/HeroBand";
import { LifecycleTour } from "@/components/lifecycle/LifecycleTour";

export default function LifecyclePage() {
  const { user } = useAuth();
  const [data, setData] = useState<LifecycleDashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeStage, setActiveStage] = useState<LifecycleStageKey | null>(
    "strategy",
  );

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await strategyApi.getLifecycleDashboard();
      setData(res);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not load the lifecycle dashboard right now.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Tour: show only on the very first visit (Company.feature_flags.seen_lifecycle_tour
  // is the durable record). The user object exposes feature_flags via useAuth.
  const featureFlags =
    (user as unknown as { feature_flags?: Record<string, unknown> })
      ?.feature_flags ?? {};
  const hasSeenTour = Boolean(
    (featureFlags as Record<string, unknown>).seen_lifecycle_tour,
  );

  return (
    <AdminGuard>
      <div className="max-w-7xl mx-auto space-y-5 sm:space-y-6 pb-12 px-1">
        {/* Page header */}
        <header className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <Sparkles
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Lifecycle
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5 max-w-2xl">
                Workforce strategy across the 8 stages of the employee lifecycle
                — Strategy, Attract, Recruit, Onboard, Learning, Reward,
                Progression, Retain. Click any stage for KPIs.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={fetchData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-gray-200)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--color-gray-700)] hover:bg-[var(--color-gray-50)] disabled:opacity-50"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            Refresh
          </button>
        </header>

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900 flex items-start gap-2"
          >
            <AlertCircle
              className="h-4 w-4 mt-0.5 shrink-0"
              aria-hidden="true"
            />
            <p>{error}</p>
          </div>
        )}

        {loading && !data && (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-8 text-center text-sm text-[var(--color-gray-500)]">
            Loading lifecycle data…
          </div>
        )}

        {data && (
          <>
            <HeroBand hero={data.hero} />

            <StageGrid
              stages={data.stages}
              activeStage={activeStage}
              onSelect={(s) =>
                setActiveStage((prev) => (prev === s ? null : s))
              }
            />

            {activeStage && data.stages[activeStage] && (
              <StageDetailPanel
                stageKey={activeStage}
                stage={data.stages[activeStage]}
                hero={data.hero}
              />
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-2">
                <DiSnapshotTile snapshot={data.di_snapshot} />
              </div>
              <ActivityFeed activity={data.activity} />
            </div>
          </>
        )}

        {!hasSeenTour && data && <LifecycleTour initialOpen />}
      </div>
    </AdminGuard>
  );
}
