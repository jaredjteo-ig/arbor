"use client";

/* P2-GO-3 (obayashi): Goals page — kanban-by-status with in-line check-in. */

import { useEffect, useMemo, useState } from "react";
import {
  TrendingUp,
  Plus,
  Loader2,
  MessageCircle,
  History,
} from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  goalsApi,
  type Goal,
  type GoalCheckIn,
  type GoalStatus,
} from "@/services/api/goals";
import { employeesApi, type Employee } from "@/services/api/employees";

const STATUS_ORDER: GoalStatus[] = [
  "draft",
  "active",
  "at_risk",
  "done",
  "cancelled",
];

const STATUS_STYLES: Record<
  GoalStatus,
  { bg: string; text: string; label: string }
> = {
  draft: { bg: "bg-gray-50", text: "text-gray-700", label: "Draft" },
  active: { bg: "bg-blue-50", text: "text-blue-700", label: "Active" },
  at_risk: { bg: "bg-amber-50", text: "text-amber-700", label: "At risk" },
  done: { bg: "bg-emerald-50", text: "text-emerald-700", label: "Done" },
  cancelled: {
    bg: "bg-gray-100",
    text: "text-gray-500",
    label: "Cancelled",
  },
};

export default function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [showForm, setShowForm] = useState(false);
  const [empId, setEmpId] = useState<number | "">("");
  const [title, setTitle] = useState("");
  const [metric, setMetric] = useState("");
  const [dueDate, setDueDate] = useState("");

  const [checkinFor, setCheckinFor] = useState<number | null>(null);
  const [checkinPct, setCheckinPct] = useState<number>(0);
  const [checkinNote, setCheckinNote] = useState("");

  const [historyFor, setHistoryFor] = useState<number | null>(null);
  const [historyByGoal, setHistoryByGoal] = useState<
    Record<number, GoalCheckIn[]>
  >({});
  const [historyLoading, setHistoryLoading] = useState<number | null>(null);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [g, e] = await Promise.all([goalsApi.list(), employeesApi.list()]);
      // Red-team C6 / O4: live walk turned up a duplicate Q2 Engineering
      // L&D card. Defence-in-depth dedupe by goal id so a backend join
      // that returns the same row twice can't render the same goal
      // twice. The backend join is also being audited separately.
      const seen = new Map<number, Goal>();
      for (const goal of g.goals) {
        if (!seen.has(goal.id)) seen.set(goal.id, goal);
      }
      setGoals(Array.from(seen.values()));
      setEmployees(e.employees ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load goals.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const employeeName = (id: number) =>
    employees.find((e) => e.id === id)?.name || "—";

  const grouped = useMemo(() => {
    const map: Record<GoalStatus, Goal[]> = {
      draft: [],
      active: [],
      at_risk: [],
      done: [],
      cancelled: [],
    };
    for (const g of goals) {
      map[g.status]?.push(g);
    }
    return map;
  }, [goals]);

  const submitNew = async () => {
    if (!empId || !title.trim()) return;
    setSubmitting(true);
    try {
      await goalsApi.create({
        employee_id: Number(empId),
        title: title.trim(),
        metric: metric.trim(),
        due_date: dueDate,
        status: "active",
      });
      setShowForm(false);
      setEmpId("");
      setTitle("");
      setMetric("");
      setDueDate("");
      await fetchAll();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create the goal.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const submitCheckin = async (goalId: number) => {
    setSubmitting(true);
    try {
      await goalsApi.addCheckin(goalId, {
        progress_pct: checkinPct,
        note: checkinNote.trim(),
      });
      setCheckinFor(null);
      setCheckinPct(0);
      setCheckinNote("");
      // Invalidate cached history so the new check-in shows up next time.
      setHistoryByGoal((prev) => {
        const next = { ...prev };
        delete next[goalId];
        return next;
      });
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save check-in.");
    } finally {
      setSubmitting(false);
    }
  };

  const toggleHistory = async (goalId: number) => {
    if (historyFor === goalId) {
      setHistoryFor(null);
      return;
    }
    setHistoryFor(goalId);
    if (historyByGoal[goalId]) return; // cached
    setHistoryLoading(goalId);
    try {
      const resp = await goalsApi.listCheckins(goalId);
      setHistoryByGoal((prev) => ({ ...prev, [goalId]: resp.checkins }));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load check-in history.",
      );
    } finally {
      setHistoryLoading(null);
    }
  };

  return (
    <AdminGuard>
      <div className="max-w-7xl mx-auto space-y-5 pb-12">
        <header className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <TrendingUp
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Goals
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Set goals, log check-ins, see progress before the appraisal
                cycle closes.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-primary)] text-white px-4 py-2 text-sm font-medium hover:opacity-90"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New goal
          </button>
        </header>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            {error}
          </div>
        )}

        {showForm && (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="text-xs text-[var(--color-gray-600)]">
                Employee
                <select
                  value={empId}
                  onChange={(e) =>
                    setEmpId(
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
              <label className="text-xs text-[var(--color-gray-600)]">
                Due date
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)] sm:col-span-2">
                Title
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="e.g. Reduce time-to-hire by 30% this half"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)] sm:col-span-2">
                Key result / metric
                <input
                  type="text"
                  value={metric}
                  onChange={(e) => setMetric(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="e.g. Avg days to offer ≤ 17 (from 24)"
                />
              </label>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-md border border-[var(--color-gray-300)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--color-gray-700)] hover:bg-[var(--color-gray-50)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={submitNew}
                disabled={submitting || !empId || !title.trim()}
                className="rounded-md bg-[var(--color-primary)] text-white px-3 py-1.5 text-xs font-medium hover:opacity-90 disabled:opacity-50"
              >
                {submitting ? "Saving…" : "Save goal"}
              </button>
            </div>
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
        ) : goals.length === 0 ? (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-8 text-center text-sm text-[var(--color-gray-500)]">
            No goals yet — create the first one above.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {STATUS_ORDER.map((status) => {
              const style = STATUS_STYLES[status];
              const items = grouped[status];
              return (
                <div key={status} className="space-y-2">
                  <div
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium ${style.bg} ${style.text}`}
                  >
                    {style.label}
                    <span className="ml-2 tabular-nums">({items.length})</span>
                  </div>
                  {items.map((g) => (
                    <div
                      key={g.id}
                      className="rounded-lg border border-[var(--color-gray-200)] bg-white p-3 shadow-sm space-y-2"
                    >
                      <div>
                        <p className="text-sm font-medium text-[var(--color-gray-900)] line-clamp-2">
                          {g.title}
                        </p>
                        <p className="text-[11px] text-[var(--color-gray-500)] mt-0.5">
                          {employeeName(g.employee_id)}
                          {g.due_date ? ` · due ${g.due_date}` : ""}
                        </p>
                      </div>
                      {g.metric && (
                        <p className="text-[11px] text-[var(--color-gray-600)] italic">
                          {g.metric}
                        </p>
                      )}
                      <div className="h-1.5 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            g.status === "done"
                              ? "bg-emerald-500"
                              : g.status === "at_risk"
                                ? "bg-amber-500"
                                : "bg-[var(--color-primary)]"
                          }`}
                          style={{ width: `${g.progress_pct}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-[var(--color-gray-500)] tabular-nums">
                        <span>{g.progress_pct}% progress</span>
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            onClick={() => toggleHistory(g.id)}
                            className="inline-flex items-center gap-1 text-[var(--color-gray-600)] hover:text-[var(--color-gray-900)] hover:underline"
                          >
                            <History className="h-3 w-3" aria-hidden="true" />
                            {historyFor === g.id ? "Hide history" : "History"}
                          </button>
                          {g.status !== "done" && g.status !== "cancelled" && (
                            <button
                              type="button"
                              onClick={() => {
                                setCheckinFor(g.id);
                                setCheckinPct(g.progress_pct);
                                setCheckinNote("");
                              }}
                              className="inline-flex items-center gap-1 text-[var(--color-primary)] hover:underline"
                            >
                              <MessageCircle
                                className="h-3 w-3"
                                aria-hidden="true"
                              />
                              Check in
                            </button>
                          )}
                        </div>
                      </div>
                      {historyFor === g.id && (
                        <div className="border-t border-[var(--color-gray-100)] pt-2 space-y-2">
                          {historyLoading === g.id ? (
                            <p className="text-[10px] text-[var(--color-gray-500)] italic">
                              Loading history…
                            </p>
                          ) : (historyByGoal[g.id] ?? []).length === 0 ? (
                            <p className="text-[10px] text-[var(--color-gray-500)] italic">
                              No check-ins recorded yet.
                            </p>
                          ) : (
                            <ul className="space-y-2">
                              {(historyByGoal[g.id] ?? []).map((c) => (
                                <li
                                  key={c.id}
                                  className="text-[11px] text-[var(--color-gray-700)] border-l-2 border-[var(--color-primary)]/30 pl-2"
                                >
                                  <div className="flex items-baseline justify-between gap-2">
                                    <span className="font-medium tabular-nums">
                                      {c.progress_pct}% ·{" "}
                                      <span className="font-normal text-[var(--color-gray-600)]">
                                        {c.actor_name || "—"}
                                      </span>
                                    </span>
                                    <span className="text-[10px] text-[var(--color-gray-400)]">
                                      {c.created_at
                                        ? new Date(
                                            c.created_at,
                                          ).toLocaleDateString("en-SG", {
                                            day: "2-digit",
                                            month: "short",
                                            year: "numeric",
                                          })
                                        : "—"}
                                    </span>
                                  </div>
                                  {c.note && (
                                    <p className="mt-0.5 text-[var(--color-gray-700)] whitespace-pre-wrap">
                                      {c.note}
                                    </p>
                                  )}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                      {checkinFor === g.id && (
                        <div className="border-t border-[var(--color-gray-100)] pt-2 space-y-2">
                          <label className="text-[10px] text-[var(--color-gray-600)]">
                            Progress (%)
                            <input
                              type="number"
                              min={0}
                              max={100}
                              value={checkinPct}
                              onChange={(e) =>
                                setCheckinPct(Number(e.target.value))
                              }
                              className="mt-0.5 block w-full rounded-md border border-[var(--color-gray-300)] px-2 py-1 text-xs"
                            />
                          </label>
                          <label className="text-[10px] text-[var(--color-gray-600)]">
                            Note
                            <textarea
                              value={checkinNote}
                              onChange={(e) => setCheckinNote(e.target.value)}
                              rows={2}
                              className="mt-0.5 block w-full rounded-md border border-[var(--color-gray-300)] px-2 py-1 text-xs"
                            />
                          </label>
                          <div className="flex justify-end gap-1">
                            <button
                              type="button"
                              onClick={() => setCheckinFor(null)}
                              className="rounded-md border border-[var(--color-gray-300)] px-2 py-0.5 text-[10px] hover:bg-[var(--color-gray-50)]"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={() => submitCheckin(g.id)}
                              disabled={submitting}
                              className="rounded-md bg-[var(--color-primary)] text-white px-2 py-0.5 text-[10px] hover:opacity-90 disabled:opacity-50"
                            >
                              Save
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AdminGuard>
  );
}
