"use client";

/* P2-EX-3 (obayashi): Admin view for exit interviews — list + theme tally. */

import { Fragment, useEffect, useState } from "react";
import { ChevronDown, ChevronUp, DoorOpen, Loader2, Send } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  exitInterviewsApi,
  type ExitInterview,
  type ThemeRow,
} from "@/services/api/exit-interviews";
import { employeesApi, type Employee } from "@/services/api/employees";

type TabKey = "list" | "themes";

/* Survey reason chips — must match the public exit-survey page. */
const REASON_LABELS: Record<string, string> = {
  comp: "Compensation",
  growth: "Career growth",
  manager: "Manager / leadership",
  role: "Role / scope fit",
  location: "Location / commute",
  family: "Family",
  retirement: "Retirement",
  workload: "Workload / burnout",
  culture: "Culture / environment",
  other: "Other",
};

interface SurveyPayload {
  q1_overall?: number;
  q2_fairness?: number;
  q3_reasons?: string[];
  q4_what_worked?: string;
  q5_what_to_change?: string;
  q6_recommend_why?: string;
}

function parsePayload(raw: string | null | undefined): SurveyPayload | null {
  if (!raw) return null;
  try {
    const obj = JSON.parse(raw);
    return obj && typeof obj === "object" ? (obj as SurveyPayload) : null;
  } catch {
    return null;
  }
}

function ScoreBar({ score }: { score: number }) {
  const cells = [1, 2, 3, 4, 5];
  return (
    <div className="flex items-center gap-1">
      {cells.map((n) => (
        <div
          key={n}
          className={`h-2 w-6 rounded-full ${
            n <= score
              ? "bg-[var(--color-primary)]"
              : "bg-[var(--color-gray-200)]"
          }`}
        />
      ))}
      <span className="ml-1 text-xs tabular-nums text-[var(--color-gray-600)]">
        {score}/5
      </span>
    </div>
  );
}

function ResponseDetail({
  interview,
  payload,
}: {
  interview: ExitInterview;
  payload: SurveyPayload | null;
}) {
  if (!interview.submitted_at) {
    return (
      <div className="px-4 py-4 text-sm text-[var(--color-gray-500)] italic">
        Survey not yet submitted — the leaver hasn&apos;t opened the link.
      </div>
    );
  }
  if (!payload) {
    return (
      <div className="px-4 py-4 text-sm text-[var(--color-gray-500)] italic">
        Submitted, but the response payload couldn&apos;t be parsed. The
        underlying record may be corrupt.
      </div>
    );
  }
  const reasons = (payload.q3_reasons ?? []).filter(Boolean);
  return (
    <div className="px-4 py-4 space-y-4 bg-[var(--color-surface-page)]">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)] mb-1">
            Overall experience
          </p>
          {typeof payload.q1_overall === "number" && payload.q1_overall > 0 ? (
            <ScoreBar score={payload.q1_overall} />
          ) : (
            <span className="text-sm text-[var(--color-gray-400)]">—</span>
          )}
        </div>
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)] mb-1">
            Fairness
          </p>
          {typeof payload.q2_fairness === "number" &&
          payload.q2_fairness > 0 ? (
            <ScoreBar score={payload.q2_fairness} />
          ) : (
            <span className="text-sm text-[var(--color-gray-400)]">—</span>
          )}
        </div>
      </div>

      <div>
        <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)] mb-1.5">
          Reasons for leaving
        </p>
        {reasons.length === 0 ? (
          <span className="text-sm text-[var(--color-gray-400)]">—</span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {reasons.map((r) => (
              <span
                key={r}
                className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-[var(--color-primary-bg)] text-[var(--color-primary)] border border-[var(--color-primary)]/20"
              >
                {REASON_LABELS[r] ?? r}
              </span>
            ))}
          </div>
        )}
      </div>

      {(
        [
          ["What worked well", payload.q4_what_worked],
          ["What they would change", payload.q5_what_to_change],
          ["Would they recommend us", payload.q6_recommend_why],
        ] as const
      ).map(([label, value]) => (
        <div key={label}>
          <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)] mb-1">
            {label}
          </p>
          {value && value.trim() ? (
            <p className="text-sm text-[var(--color-gray-800)] whitespace-pre-wrap leading-relaxed">
              {value}
            </p>
          ) : (
            <span className="text-sm text-[var(--color-gray-400)]">
              No comment.
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function ExitInterviewsPage() {
  const [tab, setTab] = useState<TabKey>("list");
  const [interviews, setInterviews] = useState<ExitInterview[]>([]);
  const [themes, setThemes] = useState<ThemeRow[]>([]);
  const [responseRate, setResponseRate] = useState(0);
  const [submittedCount, setSubmittedCount] = useState(0);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showTrigger, setShowTrigger] = useState(false);
  const [triggerEmpId, setTriggerEmpId] = useState<number | "">("");
  const [triggerAnonymous, setTriggerAnonymous] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [lastToken, setLastToken] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const employeeName = (id: number) => {
    if (id === 0) return "Anonymous";
    return employees.find((e) => e.id === id)?.name || "—";
  };

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [list, themeData, empData] = await Promise.all([
        exitInterviewsApi.list(),
        exitInterviewsApi.themes(),
        employeesApi.list(),
      ]);
      setInterviews(list.interviews);
      setThemes(themeData.tally);
      setResponseRate(themeData.response_rate);
      setSubmittedCount(themeData.submitted_count);
      setEmployees(empData.employees ?? []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load exit interview data.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const triggerNew = async () => {
    if (!triggerEmpId) return;
    setSubmitting(true);
    try {
      const resp = await exitInterviewsApi.trigger({
        employee_id: Number(triggerEmpId),
        is_anonymous: triggerAnonymous,
      });
      setLastToken(resp.submit_token);
      setShowTrigger(false);
      setTriggerEmpId("");
      setTriggerAnonymous(false);
      await fetchAll();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not trigger the interview.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AdminGuard>
      <div className="max-w-6xl mx-auto space-y-5 pb-12">
        <header className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <DoorOpen
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Exit interviews
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Send a private survey link when someone leaves and group their
                answers into themes so you can see why people quit.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowTrigger((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-primary)] text-white px-4 py-2 text-sm font-medium hover:opacity-90"
          >
            <Send className="h-4 w-4" aria-hidden="true" />
            Trigger interview
          </button>
        </header>

        <nav
          className="flex gap-1 border-b border-[var(--color-gray-200)]"
          role="tablist"
        >
          {(["list", "themes"] as TabKey[]).map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === t
                  ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                  : "border-transparent text-[var(--color-gray-600)] hover:text-[var(--color-gray-900)]"
              }`}
            >
              {t === "list" ? "Interviews" : "Themes"}
            </button>
          ))}
        </nav>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            {error}
          </div>
        )}

        {showTrigger && (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="text-xs text-[var(--color-gray-600)]">
                Employee
                <select
                  value={triggerEmpId}
                  onChange={(e) =>
                    setTriggerEmpId(
                      e.target.value === "" ? "" : Number(e.target.value),
                    )
                  }
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                >
                  <option value="">Select an employee</option>
                  {employees.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-[var(--color-gray-700)] flex items-center gap-2 sm:col-span-2">
                <input
                  type="checkbox"
                  checked={triggerAnonymous}
                  onChange={(e) => setTriggerAnonymous(e.target.checked)}
                />
                Anonymous mode (employee_id zeroed in admin views)
              </label>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowTrigger(false)}
                className="rounded-md border border-[var(--color-gray-300)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--color-gray-700)] hover:bg-[var(--color-gray-50)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={triggerNew}
                disabled={submitting || !triggerEmpId}
                className="rounded-md bg-[var(--color-primary)] text-white px-3 py-1.5 text-xs font-medium hover:opacity-90 disabled:opacity-50"
              >
                {submitting ? "Triggering…" : "Trigger interview"}
              </button>
            </div>
          </div>
        )}

        {lastToken && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
            <p className="font-semibold mb-1">Survey link generated</p>
            <p className="text-xs break-all">
              Send the leaver this URL: <br />
              <code className="bg-white px-1.5 py-0.5 rounded text-[11px]">
                /exit-survey/{lastToken}
              </code>
            </p>
          </div>
        )}

        {loading ? (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-8 text-center text-sm text-[var(--color-gray-500)]">
            <Loader2
              className="h-4 w-4 animate-spin inline-block mr-2"
              aria-hidden="true"
            />
            Loading…
          </div>
        ) : tab === "list" ? (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white shadow-sm overflow-hidden">
            {interviews.length === 0 ? (
              <div className="p-8 text-center text-sm text-[var(--color-gray-500)]">
                No exit interviews triggered yet.
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-surface-page)]">
                    <th className="w-8 py-2 px-2"></th>
                    <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                      Employee
                    </th>
                    <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                      Triggered
                    </th>
                    <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                      Submitted
                    </th>
                    <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                      Anonymous
                    </th>
                    <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                      Themes
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {interviews.map((iv) => {
                    let themeChips: string[] = [];
                    try {
                      themeChips = iv.themes ? JSON.parse(iv.themes) : [];
                    } catch {
                      themeChips = [];
                    }
                    const isExpanded = expandedId === iv.id;
                    const payload = isExpanded
                      ? parsePayload(iv.survey_payload)
                      : null;
                    return (
                      <Fragment key={iv.id}>
                        <tr
                          className="border-b border-[var(--color-gray-100)] hover:bg-[var(--color-gray-50)] transition-colors cursor-pointer"
                          onClick={() =>
                            setExpandedId(isExpanded ? null : iv.id)
                          }
                        >
                          <td className="py-2 px-2 align-middle">
                            {isExpanded ? (
                              <ChevronUp
                                className="h-3.5 w-3.5 text-[var(--color-gray-400)]"
                                aria-hidden="true"
                              />
                            ) : (
                              <ChevronDown
                                className="h-3.5 w-3.5 text-[var(--color-gray-400)]"
                                aria-hidden="true"
                              />
                            )}
                          </td>
                          <td className="py-2 px-4">
                            {employeeName(iv.employee_id)}
                          </td>
                          <td className="py-2 px-4">
                            {iv.triggered_at
                              ? new Date(iv.triggered_at).toLocaleDateString(
                                  "en-SG",
                                )
                              : "—"}
                          </td>
                          <td className="py-2 px-4">
                            {iv.submitted_at
                              ? new Date(iv.submitted_at).toLocaleDateString(
                                  "en-SG",
                                )
                              : "Pending"}
                          </td>
                          <td className="py-2 px-4">
                            {iv.is_anonymous ? "Yes" : "No"}
                          </td>
                          <td className="py-2 px-4">
                            <div className="flex flex-wrap gap-1">
                              {themeChips.length === 0 ? (
                                <span className="text-xs text-[var(--color-gray-400)]">
                                  —
                                </span>
                              ) : (
                                themeChips.map((t) => (
                                  <span
                                    key={t}
                                    className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-700)] capitalize"
                                  >
                                    {t}
                                  </span>
                                ))
                              )}
                            </div>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="border-b border-[var(--color-gray-100)]">
                            <td colSpan={6} className="p-0">
                              <ResponseDetail
                                interview={iv}
                                payload={payload}
                              />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        ) : (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm">
            <div className="flex items-baseline justify-between gap-3 flex-wrap mb-4">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)]">
                  Response rate
                </p>
                <p className="mt-1 text-3xl font-bold text-[var(--color-gray-900)] tabular-nums">
                  {Math.round(responseRate * 100)}%
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">
                  {submittedCount} of {interviews.length} interviews submitted
                </p>
              </div>
            </div>
            {themes.length === 0 ? (
              <p className="text-sm text-[var(--color-gray-500)] text-center py-6">
                No submitted interviews yet — themes appear as responses come
                in.
              </p>
            ) : (
              <ul className="space-y-2">
                {themes.map((t) => (
                  <li
                    key={t.theme}
                    className="flex items-center gap-3 text-sm text-[var(--color-gray-700)]"
                  >
                    <span className="capitalize w-32">{t.theme}</span>
                    <div className="flex-1 h-2 rounded-full bg-[var(--color-gray-100)] overflow-hidden">
                      <div
                        className="h-full bg-[var(--color-primary)]"
                        style={{
                          width: `${Math.min(100, (t.count / Math.max(1, themes[0].count)) * 100)}%`,
                        }}
                      />
                    </div>
                    <span className="w-8 text-right tabular-nums">
                      {t.count}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </AdminGuard>
  );
}
