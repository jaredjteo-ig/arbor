"use client";

/* P1-5 (obayashi): D&I cross-cutting tile.
   Derived from existing demographic fields only (gender, pass_type,
   nationality, date_of_birth). No new PII fields. Race opt-in only.
*/

import Link from "next/link";
import { Users, ArrowRight } from "lucide-react";
import type { DiSnapshot } from "@/services/api/strategy";

interface Props {
  snapshot: DiSnapshot;
}

const PASS_TYPE_LABELS: Record<string, string> = {
  citizen: "Local",
  pr: "PR",
  ep: "EP",
  sp: "SP",
  wp: "WP",
};

function topRow(buckets: Record<string, number> | undefined, total: number) {
  if (!buckets) return [];
  return Object.entries(buckets)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => ({
      label: PASS_TYPE_LABELS[k] ?? k,
      value: v,
      pct: total > 0 ? Math.round((v / total) * 100) : 0,
    }));
}

export function DiSnapshotTile({ snapshot }: Props) {
  const composition = snapshot?.composition ?? {};
  const completeness = snapshot?.completeness ?? {};
  const total = Object.values(composition.gender ?? {}).reduce(
    (a, b) => a + b,
    0,
  );

  const genderRows = topRow(composition.gender, total);
  const passRows = topRow(composition.pass_type, total);

  const fieldsToShow = [
    { key: "gender", label: "Gender" },
    { key: "pass_type", label: "Pass type" },
    { key: "nationality", label: "Nationality" },
    { key: "date_of_birth", label: "Date of birth" },
  ];

  return (
    <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 sm:p-6 shadow-sm">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <Users
            className="h-4 w-4 text-[var(--color-gray-500)]"
            aria-hidden="true"
          />
          <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
            Diversity &amp; Inclusion snapshot
          </h2>
        </div>
        <Link
          href="/analytics?tab=workforce"
          className="inline-flex items-center gap-1 text-xs font-medium text-[var(--color-primary)] hover:underline"
        >
          Full report
          <ArrowRight className="h-3 w-3" aria-hidden="true" />
        </Link>
      </div>

      <p className="text-xs text-[var(--color-gray-600)] mb-4">
        {snapshot?.headline ??
          "Demographic data will appear once employees are added."}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)] mb-2">
            Composition by gender
          </p>
          {genderRows.length === 0 ? (
            <p className="text-xs text-[var(--color-gray-400)]">No data yet</p>
          ) : (
            <ul className="space-y-1.5">
              {genderRows.map((r) => (
                <li
                  key={r.label}
                  className="flex items-center gap-2 text-xs text-[var(--color-gray-700)]"
                >
                  <span className="capitalize w-20">{r.label}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-[var(--color-gray-100)] overflow-hidden">
                    <div
                      className="h-full bg-[var(--color-primary)]"
                      style={{ width: `${r.pct}%` }}
                    />
                  </div>
                  <span className="w-12 text-right tabular-nums">
                    {r.value} · {r.pct}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)] mb-2">
            Composition by pass type
          </p>
          {passRows.length === 0 ? (
            <p className="text-xs text-[var(--color-gray-400)]">No data yet</p>
          ) : (
            <ul className="space-y-1.5">
              {passRows.map((r) => (
                <li
                  key={r.label}
                  className="flex items-center gap-2 text-xs text-[var(--color-gray-700)]"
                >
                  <span className="w-20">{r.label}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-[var(--color-gray-100)] overflow-hidden">
                    <div
                      className="h-full bg-emerald-500"
                      style={{ width: `${r.pct}%` }}
                    />
                  </div>
                  <span className="w-12 text-right tabular-nums">
                    {r.value} · {r.pct}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="mt-5 border-t border-[var(--color-gray-100)] pt-4">
        <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)] mb-2">
          Demographic completeness
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {fieldsToShow.map((f) => {
            const pct = Math.round((completeness[f.key] ?? 0) * 100);
            const dotColor =
              pct >= 90
                ? "bg-emerald-500"
                : pct >= 70
                  ? "bg-amber-500"
                  : "bg-red-500";
            return (
              <div
                key={f.key}
                className="flex items-center gap-2 text-xs text-[var(--color-gray-700)]"
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${dotColor}`}
                  aria-hidden="true"
                />
                <span className="text-[var(--color-gray-500)]">{f.label}</span>
                <span className="ml-auto font-medium tabular-nums">{pct}%</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
