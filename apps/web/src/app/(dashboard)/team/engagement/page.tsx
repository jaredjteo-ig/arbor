"use client";

/* ── /team/engagement — Manager engagement view ──────────────
 *
 * Anonymity-protected aggregate of the latest closed engagement
 * pulse for the caller's direct reports. Backed by the existing
 * /engagement-surveys/team/aggregate endpoint which enforces:
 *
 *   - n ≥ 5 floor (refuses to render below that)
 *   - Z26 self-exclusion (manager's own response stripped)
 *   - HMAC pseudonym resolution for pseudonymous-tier surveys
 *   - Refusal for anonymous-tier surveys (no per-respondent ID)
 *
 * The manager sees four sections:
 *   1. Headline numbers — avg Likert + eNPS + n + scope
 *   2. By-question breakdown — sorted ascending so lowest scores
 *      surface first (the dimensions worth a conversation)
 *   3. Themes — free-text categorisation from /codify pipeline
 *   4. 6-pulse trend — same scope across the last six closed
 *      pulses (Likert avg only — compact)
 *
 * P50 privacy asymmetry: the manager NEVER sees individual
 * responses or per-respondent identifiers. They see distributions.
 *
 * Origin: workspaces/obayashi/04-validate/09-redteam-roles-2026-05-12.md
 * finding P1-A. P4-MG-5 in P4-MG-manager-role.md.
 */

import Link from "next/link";
import {
  ArrowLeft,
  Heart,
  Lock,
  Tag,
  TrendingUp,
  AlertCircle,
} from "lucide-react";
import { useTeamEngagement } from "@/hooks/api";
import { AppCard } from "@/components/design-system";

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-64 bg-[var(--color-gray-200)] rounded animate-pulse" />
      <div className="h-32 bg-[var(--color-gray-100)] rounded-2xl animate-pulse" />
      <div className="h-64 bg-[var(--color-gray-100)] rounded-2xl animate-pulse" />
    </div>
  );
}

export default function TeamEngagementPage() {
  const { data, isLoading, error } = useTeamEngagement();

  if (isLoading) return <LoadingSkeleton />;

  if (error) {
    return (
      <div className="max-w-md mx-auto py-16 text-center">
        <p className="text-sm text-red-600">
          Couldn’t load engagement data. Try again.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header + back-link */}
      <div>
        <Link
          href="/team"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] mb-3"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to team
        </Link>
        <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
          Team engagement
        </h1>
        <p className="text-sm text-[var(--color-gray-500)] mt-1 max-w-2xl">
          Aggregated responses from your direct reports&apos; latest pulse
          survey. You see distributions only — individual responses are never
          shown to you. Requires at least 5 responses per question.
        </p>
      </div>

      {/* Hidden / privacy-floor state */}
      {data && !data.is_visible && (
        <AppCard variant="standard">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-[var(--color-gray-100)] flex items-center justify-center shrink-0">
              <Lock className="h-5 w-5 text-[var(--color-gray-500)]" />
            </div>
            <div>
              <p className="font-medium text-[var(--color-gray-900)]">
                Not yet available for your team
              </p>
              <p className="text-sm text-[var(--color-gray-600)] mt-1">
                {data.message ??
                  "Engagement aggregate not available right now."}
              </p>
              <p className="text-xs text-[var(--color-gray-500)] mt-3">
                Why this rule? Showing scores below 5 respondents would risk
                identifying a single person’s answers. You’ll see the aggregate
                as soon as enough reports respond to the next pulse.
              </p>
            </div>
          </div>
        </AppCard>
      )}

      {data?.is_visible && (
        <>
          {/* Headline numbers */}
          <AppCard variant="standard">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center shrink-0">
                <Heart className="h-5 w-5 text-rose-600" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
                    {data.survey_name}
                  </p>
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-700 bg-emerald-50 rounded-full px-2 py-0.5">
                    <Lock className="h-3 w-3" />n = {data.n} (of{" "}
                    {data.scope_size})
                  </span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-6 mt-4">
                  <div>
                    <p className="text-3xl font-bold text-[var(--color-gray-900)]">
                      {data.avg_likert?.toFixed(1) ?? "—"}
                    </p>
                    <p className="text-xs text-[var(--color-gray-500)] mt-1">
                      avg Likert (1–5)
                    </p>
                  </div>
                  {data.enps_score !== null && (
                    <div>
                      <p className="text-3xl font-bold text-[var(--color-gray-900)]">
                        {data.enps_score > 0 ? "+" : ""}
                        {data.enps_score}
                      </p>
                      <p className="text-xs text-[var(--color-gray-500)] mt-1">
                        eNPS
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-3xl font-bold text-[var(--color-gray-900)]">
                      {data.scope_size}
                    </p>
                    <p className="text-xs text-[var(--color-gray-500)] mt-1">
                      Reports in scope
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </AppCard>

          {/* By-question breakdown — sorted asc (lowest first) */}
          {data.by_question.length > 0 && (
            <AppCard variant="standard">
              <div className="flex items-center gap-2 mb-4">
                <AlertCircle className="h-4 w-4 text-amber-600" />
                <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
                  By question — weakest first
                </h2>
              </div>
              <p className="text-xs text-[var(--color-gray-500)] mb-4">
                Sorted ascending so the dimensions worth a conversation surface
                at the top.
              </p>
              <div className="space-y-2">
                {data.by_question.map((q) => (
                  <div
                    key={q.question_id}
                    className="flex items-center gap-3 py-2 border-b border-[var(--color-gray-100)] last:border-0"
                  >
                    <div className="flex-1 min-w-0 text-sm text-[var(--color-gray-800)]">
                      {q.question_text}
                    </div>
                    <div className="w-32 hidden md:block">
                      <div className="h-2 rounded-full bg-[var(--color-gray-100)] overflow-hidden">
                        <div
                          className={
                            q.avg < 3
                              ? "h-full bg-red-500"
                              : q.avg < 3.7
                                ? "h-full bg-amber-500"
                                : "h-full bg-emerald-500"
                          }
                          style={{ width: `${(q.avg / 5) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="text-sm font-semibold tabular-nums text-[var(--color-gray-900)] w-12 text-right">
                      {q.avg.toFixed(1)}
                    </div>
                    <div className="text-xs text-[var(--color-gray-500)] w-12 text-right">
                      n={q.n}
                    </div>
                  </div>
                ))}
              </div>
            </AppCard>
          )}

          {/* Themes — from free-text categorisation */}
          {data.themes.length > 0 && (
            <AppCard variant="standard">
              <div className="flex items-center gap-2 mb-3">
                <Tag className="h-4 w-4 text-violet-600" />
                <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
                  Themes
                </h2>
              </div>
              <p className="text-xs text-[var(--color-gray-500)] mb-3">
                Categories surfaced from free-text comments. Aggregated only —
                individual comments are never exposed to you.
              </p>
              <div className="flex flex-wrap gap-2">
                {data.themes.map((t) => (
                  <span
                    key={t.theme}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-violet-50 text-violet-800 rounded-full text-xs font-medium"
                  >
                    {t.theme}
                    <span className="text-violet-500">×{t.count}</span>
                  </span>
                ))}
              </div>
            </AppCard>
          )}

          {/* 6-pulse trend */}
          {data.trend.length > 0 && (
            <AppCard variant="standard">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="h-4 w-4 text-blue-600" />
                <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
                  6-pulse trend
                </h2>
              </div>
              <p className="text-xs text-[var(--color-gray-500)] mb-4">
                Likert average across the last {data.trend.length} pulses,
                scoped to your team. Same n ≥ 5 floor on every point — pulses
                without enough responses are flagged.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--color-gray-200)] text-left">
                      <th className="py-2 px-3 font-medium text-[var(--color-gray-500)] text-xs uppercase tracking-wider">
                        Pulse
                      </th>
                      <th className="py-2 px-3 font-medium text-[var(--color-gray-500)] text-xs uppercase tracking-wider">
                        Closed
                      </th>
                      <th className="py-2 px-3 font-medium text-[var(--color-gray-500)] text-xs uppercase tracking-wider text-right">
                        Avg Likert
                      </th>
                      <th className="py-2 px-3 font-medium text-[var(--color-gray-500)] text-xs uppercase tracking-wider text-right">
                        n
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.trend.map((p) => (
                      <tr
                        key={p.survey_id}
                        className="border-b border-[var(--color-gray-100)] last:border-0"
                      >
                        <td className="py-2 px-3 text-[var(--color-gray-800)]">
                          {p.name ?? `Pulse #${p.survey_id}`}
                        </td>
                        <td className="py-2 px-3 text-[var(--color-gray-500)] text-xs">
                          {p.closed_at?.slice(0, 10) ?? "—"}
                        </td>
                        <td className="py-2 px-3 text-right font-semibold tabular-nums text-[var(--color-gray-900)]">
                          {p.is_anonymity_safe && p.avg_likert !== null
                            ? p.avg_likert.toFixed(2)
                            : "—"}
                        </td>
                        <td className="py-2 px-3 text-right text-xs text-[var(--color-gray-500)]">
                          {p.is_anonymity_safe ? (
                            p.n
                          ) : (
                            <span title="Below the n ≥ 5 anonymity floor">
                              &lt; 5
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AppCard>
          )}
        </>
      )}
    </div>
  );
}
