"use client";

/* P3-1 (obayashi): Workforce plan authoring page. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, Plus, Loader2, ArrowRight } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  strategyDepthApi,
  type WorkforcePlan,
} from "@/services/api/strategy-depth";

function StrategyTabs({ active }: { active: string }) {
  const tabs = [
    { key: "lifecycle", label: "Lifecycle", href: "/strategy/lifecycle" },
    { key: "plan", label: "Workforce plan", href: "/strategy/plan" },
    { key: "retention", label: "Retention risk", href: "/strategy/retention" },
    { key: "equity", label: "Pay equity", href: "/strategy/pay-equity" },
  ];
  return (
    <nav
      className="flex gap-1 border-b border-[var(--color-gray-200)]"
      role="tablist"
    >
      {tabs.map((t) => (
        <Link
          key={t.key}
          href={t.href}
          role="tab"
          aria-selected={active === t.key}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            active === t.key
              ? "border-[var(--color-primary)] text-[var(--color-primary)]"
              : "border-transparent text-[var(--color-gray-600)] hover:text-[var(--color-gray-900)]"
          }`}
        >
          {t.label}
        </Link>
      ))}
    </nav>
  );
}

export default function PlanPage() {
  const [plans, setPlans] = useState<WorkforcePlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [narrative, setNarrative] = useState("");

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await strategyDepthApi.listPlans();
      setPlans(r.plans);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load plans.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const submit = async () => {
    if (!name.trim() || !start || !end) return;
    setSubmitting(true);
    try {
      await strategyDepthApi.createPlan({
        name: name.trim(),
        period_start: start,
        period_end: end,
        narrative,
        status: "draft",
      });
      setShowForm(false);
      setName("");
      setStart("");
      setEnd("");
      setNarrative("");
      await fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the plan.");
    } finally {
      setSubmitting(false);
    }
  };

  const publish = async (id: number) => {
    try {
      await strategyDepthApi.updatePlan(id, { status: "published" });
      await fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not publish.");
    }
  };

  return (
    <AdminGuard>
      <div className="max-w-5xl mx-auto space-y-5 pb-12">
        <header className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <Sparkles
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Workforce plan
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Author the period's strategic intent — headcount, skills,
                retention focus.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-primary)] text-white px-4 py-2 text-sm font-medium hover:opacity-90"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New plan
          </button>
        </header>

        <StrategyTabs active="plan" />

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            {error}
          </div>
        )}

        {showForm && (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="text-xs text-[var(--color-gray-600)] sm:col-span-2">
                Plan name
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="e.g. FY2026 H1 Workforce Plan"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Period start
                <input
                  type="date"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Period end
                <input
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)] sm:col-span-2">
                Narrative
                <textarea
                  value={narrative}
                  onChange={(e) => setNarrative(e.target.value)}
                  rows={4}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="What's the headline strategy this period? What changes?"
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
                onClick={submit}
                disabled={submitting || !name.trim() || !start || !end}
                className="rounded-md bg-[var(--color-primary)] text-white px-3 py-1.5 text-xs font-medium hover:opacity-90 disabled:opacity-50"
              >
                {submitting ? "Saving…" : "Save draft"}
              </button>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {loading ? (
            <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-8 text-center text-sm text-[var(--color-gray-500)]">
              <Loader2
                className="h-4 w-4 animate-spin inline-block mr-2"
                aria-hidden="true"
              />
              Loading…
            </div>
          ) : plans.length === 0 ? (
            <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-8 text-center text-sm text-[var(--color-gray-500)]">
              No workforce plan authored yet — start one above.
            </div>
          ) : (
            plans.map((p) => (
              <div
                key={p.id}
                className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
                      {p.name}
                    </h2>
                    <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                      {p.period_start} → {p.period_end}
                    </p>
                  </div>
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${
                      p.status === "published"
                        ? "bg-emerald-50 text-emerald-700"
                        : p.status === "draft"
                          ? "bg-amber-50 text-amber-700"
                          : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {p.status}
                  </span>
                </div>
                {p.narrative && (
                  <p className="mt-3 text-sm text-[var(--color-gray-700)] whitespace-pre-line">
                    {p.narrative}
                  </p>
                )}
                {p.status === "draft" && (
                  <div className="mt-4 flex justify-end">
                    <button
                      type="button"
                      onClick={() => publish(p.id)}
                      className="inline-flex items-center gap-1 rounded-md bg-[var(--color-primary)] text-white px-3 py-1 text-xs font-medium hover:opacity-90"
                    >
                      Publish plan
                      <ArrowRight className="h-3 w-3" aria-hidden="true" />
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </AdminGuard>
  );
}
