"use client";

/**
 * /engagement — HR overview page (M4 T41).
 *
 * Round-3 hero: 6-pulse trend chart + cohort dropdown.
 * Tabs: Surveys (default) | Templates | Cohorts.
 * Launch wizard opens as a modal stack on top.
 */

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  Loader2,
  MessageSquareHeart,
  Plus,
  TrendingDown,
  TrendingUp as TrendingUpIcon,
  Minus,
} from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import { useAuth } from "@/contexts/AuthContext";
import {
  engagementApi,
  type EngagementSurvey,
  type EngagementTemplate,
  type EngagementCohortRow,
  type TrendPoint,
} from "@/services/api/engagement";
import { LaunchWizard } from "@/components/engagement/LaunchWizard";
import { TrendChart } from "@/components/engagement/TrendChart";
import { TemplatesTab } from "@/components/engagement/TemplatesTab";
import { CohortsTab } from "@/components/engagement/CohortsTab";
import { SurveysTab } from "@/components/engagement/SurveysTab";
import { Stat } from "@/components/engagement/Stat";

type TabKey = "surveys" | "templates" | "cohorts";

export default function EngagementPage() {
  const { user } = useAuth();
  const isAdmin = user !== null && user.role !== "employee";

  const [tab, setTab] = useState<TabKey>("surveys");
  const [trendCohort, setTrendCohort] = useState<string>("all");
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [trendLoading, setTrendLoading] = useState(true);

  const [surveys, setSurveys] = useState<EngagementSurvey[]>([]);
  const [templates, setTemplates] = useState<EngagementTemplate[]>([]);
  const [cohorts, setCohorts] = useState<EngagementCohortRow[]>([]);
  const [departmentOptions, setDepartmentOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [showLaunch, setShowLaunch] = useState(false);

  async function refreshAll() {
    setLoading(true);
    try {
      const [s, t, c] = await Promise.all([
        engagementApi.listSurveys(),
        engagementApi.listTemplates(),
        engagementApi.listCohorts(),
      ]);
      setSurveys(s.surveys);
      setTemplates(t.templates);
      setCohorts(c.cohorts);
    } catch (err) {
      const status = (err as { status?: number }).status;
      if (status !== 403 && status !== 401) {
        console.error("Failed to load engagement data", err);
      }
    } finally {
      setLoading(false);
    }
  }

  async function refreshTrend(cohort: string) {
    setTrendLoading(true);
    try {
      const r = await engagementApi.getTrend(cohort, 6);
      setTrend(r.points);
    } catch (err) {
      const status = (err as { status?: number }).status;
      if (status !== 403 && status !== 401) {
        console.error("Failed to load trend", err);
      }
      setTrend([]);
    } finally {
      setTrendLoading(false);
    }
  }

  useEffect(() => {
    if (!isAdmin) return;
    refreshAll();
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin) return;
    refreshTrend(trendCohort);
  }, [trendCohort, isAdmin]);

  /* Build the cohort dropdown — All + departments derived from cohorts.
     Real department list would come from a separate endpoint; for v1
     we infer from saved cohorts' filter_specs. */
  useEffect(() => {
    const departments = new Set<string>();
    for (const c of cohorts) {
      try {
        const spec = JSON.parse(c.filter_spec || "{}");
        for (const d of spec.departments || []) departments.add(d);
      } catch {
        /* ignore */
      }
    }
    setDepartmentOptions(Array.from(departments).sort());
  }, [cohorts]);

  const latestPoint = trend[trend.length - 1];
  const trendDelta = useMemo(() => {
    if (trend.length < 2) return null;
    const first = trend[0]?.avg_likert;
    const last = trend[trend.length - 1]?.avg_likert;
    if (
      first === null ||
      first === undefined ||
      last === null ||
      last === undefined
    ) {
      return null;
    }
    return Number((last - first).toFixed(1));
  }, [trend]);

  return (
    <AdminGuard>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-gray-900)] flex items-center gap-2">
              <MessageSquareHeart className="h-6 w-6 text-rose-500" />
              Engagement
            </h1>
            <p className="text-sm text-[var(--color-gray-600)] mt-1">
              Pulse surveys take 90 seconds for employees and surface engagement
              signals long before they show up in exits.
            </p>
          </div>
          <button
            onClick={() => setShowLaunch(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            Launch survey
          </button>
        </div>

        {/* ── Trend hero ────────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-[var(--color-gray-200)] p-6 mb-6">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              6-pulse trend
            </h2>
            <select
              value={trendCohort}
              onChange={(e) => setTrendCohort(e.target.value)}
              className="text-sm border border-[var(--color-gray-200)] rounded-md px-3 py-1.5 bg-white"
            >
              <option value="all">All staff</option>
              {departmentOptions.map((d) => (
                <option key={d} value={`department:${d}`}>
                  Department: {d}
                </option>
              ))}
            </select>
          </div>
          {trendLoading ? (
            <div className="h-48 flex items-center justify-center text-[var(--color-gray-400)]">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              Loading trend…
            </div>
          ) : trend.length === 0 ? (
            <div className="h-48 flex flex-col items-center justify-center text-center">
              <p className="text-[var(--color-gray-500)] mb-3">
                Trend appears after your first pulse closes.
              </p>
              <button
                onClick={() => setShowLaunch(true)}
                className="text-sm font-medium text-rose-600 hover:text-rose-700"
              >
                Launch your first pulse →
              </button>
            </div>
          ) : (
            <div>
              <TrendChart points={trend} />
              <div className="flex flex-wrap gap-6 mt-4 text-sm">
                {latestPoint && (
                  <Stat
                    label="Latest"
                    value={
                      latestPoint.avg_likert !== null
                        ? `${latestPoint.avg_likert.toFixed(1)} / 5`
                        : "—"
                    }
                  />
                )}
                {latestPoint && (
                  <Stat label="Latest n" value={String(latestPoint.n)} />
                )}
                {latestPoint && latestPoint.enps !== null && (
                  <Stat
                    label="eNPS"
                    value={`${latestPoint.enps > 0 ? "+" : ""}${latestPoint.enps.toFixed(0)}`}
                  />
                )}
                {trendDelta !== null && (
                  <Stat
                    label={`6-pulse Δ`}
                    value={
                      <span className="inline-flex items-center gap-1">
                        {trendDelta > 0 ? (
                          <TrendingUpIcon className="h-4 w-4 text-green-600" />
                        ) : trendDelta < 0 ? (
                          <TrendingDown className="h-4 w-4 text-red-600" />
                        ) : (
                          <Minus className="h-4 w-4 text-gray-500" />
                        )}
                        {trendDelta > 0 ? "+" : ""}
                        {trendDelta.toFixed(1)}
                      </span>
                    }
                  />
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Tabs ──────────────────────────────────────────── */}
        <div className="border-b border-[var(--color-gray-200)] mb-6">
          <div className="flex gap-1">
            {(["surveys", "templates", "cohorts"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`
                  px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
                  ${
                    tab === t
                      ? "border-rose-600 text-rose-600"
                      : "border-transparent text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"
                  }
                `}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* ── Tab content ───────────────────────────────────── */}
        {loading ? (
          <div className="flex items-center justify-center py-16 text-[var(--color-gray-400)]">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            Loading…
          </div>
        ) : (
          <>
            {tab === "surveys" && (
              <SurveysTab
                surveys={surveys}
                onLaunchClick={() => setShowLaunch(true)}
              />
            )}
            {tab === "templates" && (
              <TemplatesTab templates={templates} onChange={refreshAll} />
            )}
            {tab === "cohorts" && (
              <CohortsTab cohorts={cohorts} onChange={refreshAll} />
            )}
          </>
        )}

        {showLaunch && (
          <LaunchWizard
            templates={templates}
            cohorts={cohorts}
            onClose={() => setShowLaunch(false)}
            onLaunched={(surveyId) => {
              setShowLaunch(false);
              refreshAll();
              window.location.href = `/engagement/surveys/${surveyId}`;
            }}
          />
        )}
      </div>
    </AdminGuard>
  );
}

/* Stat extracted to /components/engagement/Stat.tsx (C1). */
