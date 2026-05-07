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
import { useAuth } from "@/contexts/AuthContext";

export default function ManagerEngagementPage() {
  const { user, isLoading: authLoading } = useAuth();
  const [data, setData] = useState<TeamAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    /* Plain employees never have direct reports — short-circuit before
       the network round-trip (Bug #69: removes 2-3s loading flicker). */
    if (user && user.role === "employee") {
      setAccessDenied(true);
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const r = await engagementApi.getTeamAggregate();
        setData(r);
      } catch (err) {
        const status = (err as { status?: number }).status;
        if (status === 403 || status === 404) {
          setAccessDenied(true);
        } else if (status !== 401) {
          setError((err as Error).message || "Failed to load team aggregate");
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [authLoading, user]);

  /* 403/404 short-circuit — skip the loading spinner, show access-denied
     copy immediately. (Bug #69: previously flashed "Loading…" for 2-3s
     before settling on this state.) */
  if (accessDenied) {
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
        <p className="text-sm text-rose-600 mb-2">
          Couldn&apos;t load your team&apos;s engagement.
        </p>
        <p className="text-xs text-[var(--color-gray-400)]">{error}</p>
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

          {data.by_question && data.by_question.length > 0 && (
            <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5">
              <h3 className="font-medium mb-1">
                Where your team scores lowest
              </h3>
              <p className="text-xs text-[var(--color-gray-500)] mb-3">
                Sorted ascending — the questions to discuss in your next 1:1.
              </p>
              <ul className="space-y-2">
                {data.by_question.slice(0, 5).map((q) => (
                  <li
                    key={q.question_id}
                    className="flex items-center justify-between gap-3"
                  >
                    <span className="text-sm text-[var(--color-gray-700)] flex-1">
                      {q.question_text}
                    </span>
                    <div className="flex items-center gap-2 shrink-0">
                      <div className="w-24 h-1.5 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            q.avg < 3
                              ? "bg-rose-500"
                              : q.avg < 4
                                ? "bg-amber-500"
                                : "bg-emerald-500"
                          }`}
                          style={{ width: `${(q.avg / 5) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-[var(--color-gray-900)] tabular-nums w-12 text-right">
                        {q.avg.toFixed(2)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.trend && data.trend.length >= 2 && (
            <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-medium">Your team&apos;s trend</h3>
                <span className="text-xs text-[var(--color-gray-500)]">
                  {data.trend.length}-pulse
                </span>
              </div>
              <p className="text-xs text-[var(--color-gray-500)] mb-3">
                Avg engagement across the most recent pulses.
              </p>
              <ManagerTrendChart
                points={data.trend.map((p) => ({
                  label: p.survey_name,
                  value: p.avg_likert,
                  n: p.n,
                }))}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ManagerTrendChart({
  points,
}: {
  points: { label: string; value: number | null; n: number }[];
}) {
  const valid = points.filter(
    (p): p is { label: string; value: number; n: number } => p.value !== null,
  );
  if (valid.length < 2) {
    return (
      <p className="text-xs text-[var(--color-gray-400)]">
        Need at least 2 closed pulses with enough responses to draw a trend.
      </p>
    );
  }
  const w = 480;
  const h = 80;
  const pad = 6;
  const maxV = 5;
  const minV = 1;
  const stepX = (w - pad * 2) / (valid.length - 1);
  const yFor = (v: number) =>
    h - pad - ((v - minV) / (maxV - minV)) * (h - pad * 2);
  const path = valid
    .map((p, i) => `${i === 0 ? "M" : "L"} ${pad + i * stepX} ${yFor(p.value)}`)
    .join(" ");
  const first = valid[0].value;
  const last = valid[valid.length - 1].value;
  const delta = Number((last - first).toFixed(1));
  return (
    <div>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        className="w-full h-20"
        role="img"
        aria-label="Manager engagement trend"
      >
        <line
          x1={pad}
          y1={yFor(3)}
          x2={w - pad}
          y2={yFor(3)}
          stroke="var(--color-gray-200)"
          strokeDasharray="2 2"
        />
        <path d={path} fill="none" stroke="#e11d48" strokeWidth="2" />
        {valid.map((p, i) => (
          <circle
            key={i}
            cx={pad + i * stepX}
            cy={yFor(p.value)}
            r={3}
            fill="#e11d48"
          >
            <title>
              {p.label}: {p.value.toFixed(2)} (n={p.n})
            </title>
          </circle>
        ))}
      </svg>
      <div className="flex items-center justify-between text-xs text-[var(--color-gray-500)] mt-1">
        <span>
          {valid[0].label}: {first.toFixed(2)}
        </span>
        <span
          className={
            delta > 0
              ? "text-emerald-600"
              : delta < 0
                ? "text-rose-600"
                : "text-[var(--color-gray-500)]"
          }
        >
          {delta > 0 ? "+" : ""}
          {delta.toFixed(1)} over {valid.length} pulses
        </span>
        <span>
          {valid[valid.length - 1].label}: {last.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

/* Stat extracted to /components/engagement/Stat.tsx (C1). */
