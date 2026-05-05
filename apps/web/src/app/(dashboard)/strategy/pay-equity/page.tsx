"use client";

/* P3-5 (obayashi): Pay-equity dashboard. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { Scale, Loader2 } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  strategyDepthApi,
  type PayEquityBucket,
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

function BucketTable({
  title,
  rows,
}: {
  title: string;
  rows: PayEquityBucket[];
}) {
  return (
    <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
        {title}
      </h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--color-gray-200)] text-xs text-[var(--color-gray-500)]">
            <th className="text-left py-1.5 font-medium">Bucket</th>
            <th className="text-right py-1.5 font-medium">Count</th>
            <th className="text-right py-1.5 font-medium">Avg salary</th>
            <th className="text-right py-1.5 font-medium">Gap vs overall</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.bucket}
              className="border-b border-[var(--color-gray-100)] last:border-0"
            >
              <td className="py-1.5 capitalize">{r.bucket}</td>
              <td className="py-1.5 text-right tabular-nums">{r.count}</td>
              <td className="py-1.5 text-right tabular-nums">
                {typeof r.avg_salary === "number"
                  ? `$${r.avg_salary.toLocaleString("en-SG", {
                      maximumFractionDigits: 0,
                    })}`
                  : r.avg_salary}
              </td>
              <td className="py-1.5 text-right tabular-nums">
                {typeof r.gap_vs_overall_pct === "number"
                  ? `${r.gap_vs_overall_pct > 0 ? "+" : ""}${r.gap_vs_overall_pct}%`
                  : r.gap_vs_overall_pct}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PayEquityPage() {
  const [byGender, setByGender] = useState<PayEquityBucket[]>([]);
  const [byPass, setByPass] = useState<PayEquityBucket[]>([]);
  const [headcount, setHeadcount] = useState(0);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    strategyDepthApi
      .payEquity()
      .then((r) => {
        setByGender(r.by_gender);
        setByPass(r.by_pass_type);
        setHeadcount(r.headcount);
        setNote(r.note);
      })
      .catch((err) =>
        setError(
          err instanceof Error
            ? err.message
            : "Could not load pay-equity data.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <AdminGuard>
      <div className="max-w-5xl mx-auto space-y-5 pb-12">
        <header className="flex items-center gap-3">
          <Scale
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Pay equity
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Pay gap by gender + pass-type. Aggregated only — never individual
              salaries.
            </p>
          </div>
        </header>

        <StrategyTabs active="equity" />

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
            Computing buckets…
          </div>
        ) : (
          <>
            <p className="text-xs text-[var(--color-gray-500)]">
              Headcount: {headcount}. {note}
            </p>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <BucketTable title="By gender" rows={byGender} />
              <BucketTable title="By pass type" rows={byPass} />
            </div>
          </>
        )}
      </div>
    </AdminGuard>
  );
}
