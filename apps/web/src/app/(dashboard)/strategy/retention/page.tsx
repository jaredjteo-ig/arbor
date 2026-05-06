"use client";

/* P3-4 (obayashi): Retention risk read-only view. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldAlert, Loader2 } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  strategyDepthApi,
  type RetentionRow,
} from "@/services/api/strategy-depth";
import { employeesApi, type Employee } from "@/services/api/employees";

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

export default function RetentionPage() {
  const [rows, setRows] = useState<RetentionRow[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([strategyDepthApi.retentionRisk(), employeesApi.list()])
      .then(([r, e]) => {
        setRows(r.rows);
        setEmployees(e.employees ?? []);
      })
      .catch((err) =>
        setError(
          err instanceof Error ? err.message : "Could not load retention data.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  const employeeName = (id: number) =>
    employees.find((e) => e.id === id)?.name || "—";

  const colorFor = (score: number) =>
    score >= 70
      ? "bg-red-50 text-red-700"
      : score >= 50
        ? "bg-amber-50 text-amber-700"
        : "bg-emerald-50 text-emerald-700";

  return (
    <AdminGuard>
      <div className="max-w-5xl mx-auto space-y-5 pb-12">
        <header className="flex items-center gap-3">
          <ShieldAlert
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Retention risk
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Read-only score derived from tenure, recent promotions, leave
              usage, and latest appraisal. Never persisted.
            </p>
          </div>
        </header>

        <StrategyTabs active="retention" />

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            {error}
          </div>
        )}

        {loading ? (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-8 text-center text-sm text-[var(--color-gray-500)]">
            <Loader2
              className="h-4 w-4 animate-spin inline-block mr-2"
              aria-hidden="true"
            />
            Computing risk scores…
          </div>
        ) : (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-surface-page)]">
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Employee
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Score
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Drivers
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Recommendation
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.employee_id}
                    className="border-b border-[var(--color-gray-100)] last:border-0 align-top"
                  >
                    <td className="py-2 px-4 font-medium text-[var(--color-gray-900)]">
                      {employeeName(r.employee_id)}
                    </td>
                    <td className="py-2 px-4">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium tabular-nums ${colorFor(r.score)}`}
                      >
                        {r.score}
                      </span>
                    </td>
                    <td className="py-2 px-4 text-xs text-[var(--color-gray-700)]">
                      {r.drivers.length === 0 ? "—" : r.drivers.join(" · ")}
                    </td>
                    <td className="py-2 px-4 text-xs text-[var(--color-gray-700)]">
                      {r.recommendation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminGuard>
  );
}
