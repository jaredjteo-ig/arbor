"use client";

/**
 * /engagement/team — manager view (T44, pulled from P3 in round-3).
 *
 * Auth: any user with at least one direct report (resolved at the API
 * layer). NOT wrapped in AdminGuard — non-admin managers must reach this.
 * n>=5 enforced with self-exclusion (Z26).
 */

import { useEffect, useState } from "react";
import { Loader2, Users } from "lucide-react";
import { engagementApi, type TeamAggregate } from "@/services/api/engagement";
import { Stat } from "@/components/engagement/Stat";

export default function ManagerEngagementPage() {
  const [data, setData] = useState<TeamAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await engagementApi.getTeamAggregate();
        setData(r);
      } catch (err) {
        setError((err as Error).message || "Failed to load team aggregate");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center text-[var(--color-gray-400)]">
        <Loader2 className="h-5 w-5 animate-spin inline mr-2" />
        Loading…
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <p className="text-sm text-[var(--color-gray-500)] mb-2">
          You don&apos;t have access to the manager engagement view.
        </p>
        <p className="text-xs text-[var(--color-gray-400)]">
          This page is available to managers with at least one direct report.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center gap-2 mb-2">
        <Users className="h-6 w-6 text-rose-500" />
        <h1 className="text-2xl font-semibold text-[var(--color-gray-900)]">
          Your team&apos;s engagement
        </h1>
      </div>
      <p className="text-sm text-[var(--color-gray-500)] mb-6">
        Aggregated engagement scores for your direct + indirect reports.
        Individual responses are never visible.
      </p>

      {!data || !data.is_visible ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6">
          <h2 className="font-medium text-amber-900 mb-1">
            Not enough responses to show
          </h2>
          <p className="text-sm text-amber-800">
            {data?.message ??
              "Your team is too small to see aggregated engagement data without risk of identifying individual responses. Roll up to your skip-level manager for visibility."}
          </p>
          {data?.scope_size !== undefined && (
            <p className="text-xs text-amber-700 mt-2">
              Scope: {data.scope_size} report{data.scope_size === 1 ? "" : "s"}{" "}
              · {data.n ?? 0} submitted (need ≥3 for themes, ≥5 for scores)
            </p>
          )}
        </div>
      ) : data.is_limited ? (
        /* D1 (Phase 2): themes-only mode for n=3-4 teams. Friendly,
           still gives the manager a real artifact each pulse. */
        <div className="space-y-6">
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-5">
            <h2 className="font-medium text-blue-900 mb-1">
              Limited preview — themes only
            </h2>
            <p className="text-sm text-blue-800">
              {data.message ??
                "Themes only at this team size. Individual scores are hidden to protect anonymity."}
            </p>
            <p className="text-xs text-blue-700 mt-2">
              {data.n} response{data.n === 1 ? "" : "s"} from {data.scope_size}{" "}
              report
              {data.scope_size === 1 ? "" : "s"} · pulse&nbsp;
              <strong>{data.survey_name}</strong>
            </p>
          </div>

          {data.themes && data.themes.length > 0 ? (
            <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5">
              <h3 className="font-medium mb-3">Top themes from your team</h3>
              <div className="flex flex-wrap gap-2">
                {data.themes.map((t) => (
                  <span
                    key={t.theme}
                    className="inline-flex items-center gap-1 text-xs rounded-full bg-rose-50 text-rose-700 px-3 py-1"
                  >
                    {t.theme}
                    <span className="text-rose-400">×{t.count}</span>
                  </span>
                ))}
              </div>
              <p className="mt-3 text-xs text-[var(--color-gray-500)]">
                Themes are aggregated bucket names, not individual comments.
                Free-text responses are never shown.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] bg-white p-6 text-sm text-[var(--color-gray-500)]">
              No themes raised this pulse.
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5">
            <div className="text-sm text-[var(--color-gray-500)] mb-1">
              Latest pulse — {data.survey_name}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Stat
                label="Avg engagement"
                value={
                  data.avg_likert !== null && data.avg_likert !== undefined
                    ? `${data.avg_likert.toFixed(2)} / 5`
                    : "—"
                }
              />
              <Stat
                label="Responses (excludes you)"
                value={String(data.n ?? 0)}
              />
              {data.enps_score !== null && data.enps_score !== undefined && (
                <Stat
                  label="eNPS"
                  value={`${data.enps_score > 0 ? "+" : ""}${data.enps_score.toFixed(0)}`}
                />
              )}
            </div>
          </div>

          {data.themes && data.themes.length > 0 && (
            <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5">
              <h3 className="font-medium mb-3">Top themes from your team</h3>
              <div className="flex flex-wrap gap-2">
                {data.themes.map((t) => (
                  <span
                    key={t.theme}
                    className="inline-flex items-center gap-1 text-xs rounded-full bg-rose-50 text-rose-700 px-3 py-1"
                  >
                    {t.theme}
                    <span className="text-rose-400">×{t.count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* Stat extracted to /components/engagement/Stat.tsx (C1). */
