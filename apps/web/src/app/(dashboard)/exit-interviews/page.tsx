"use client";

/* P2-EX-3 (obayashi): Admin view for exit interviews — list + theme tally. */

import { useEffect, useState } from "react";
import { DoorOpen, Loader2, Send } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  exitInterviewsApi,
  type ExitInterview,
  type ThemeRow,
} from "@/services/api/exit-interviews";
import { employeesApi, type Employee } from "@/services/api/employees";

type TabKey = "list" | "themes";

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
                    return (
                      <tr
                        key={iv.id}
                        className="border-b border-[var(--color-gray-100)] last:border-0"
                      >
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
