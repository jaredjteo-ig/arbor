"use client";

/* P2-LD-6 (obayashi): Mandatory training tracker. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { ListChecks, Plus, Loader2, AlertTriangle } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  trainingApi,
  type MandatoryRequirement,
  type CoverageResponse,
} from "@/services/api/training";
import { employeesApi, type Employee } from "@/services/api/employees";

function TrainingTabs({ active }: { active: string }) {
  const tabs = [
    { key: "records", label: "Records", href: "/training/records" },
    {
      key: "certifications",
      label: "Certifications",
      href: "/training/certifications",
    },
    { key: "mandatory", label: "Mandatory", href: "/training/mandatory" },
    {
      key: "skillsfuture",
      label: "SkillsFuture",
      href: "/training/skillsfuture",
    },
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

export default function MandatoryPage() {
  const [reqs, setReqs] = useState<MandatoryRequirement[]>([]);
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState("");
  const [certName, setCertName] = useState("");
  const [applicableTo, setApplicableTo] = useState("all");
  const [days, setDays] = useState<number>(90);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, c, e] = await Promise.all([
        trainingApi.listMandatory(),
        trainingApi.mandatoryCoverage(),
        employeesApi.list(),
      ]);
      setReqs(r.requirements);
      setCoverage(c);
      setEmployees(e.employees ?? []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load mandatory requirements.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const employeeName = (id: number) =>
    employees.find((e) => e.id === id)?.name || `#${id}`;

  const submit = async () => {
    if (!name.trim() || !certName.trim()) return;
    setSubmitting(true);
    try {
      await trainingApi.createMandatory({
        requirement_name: name.trim(),
        required_certification_name: certName.trim(),
        applicable_to: applicableTo,
        due_within_days_of_hire: days,
      });
      setShowForm(false);
      setName("");
      setCertName("");
      setApplicableTo("all");
      setDays(90);
      await fetchAll();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save the requirement.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const totals = coverage?.totals;

  return (
    <AdminGuard>
      <div className="max-w-6xl mx-auto space-y-5 pb-12">
        <header className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <ListChecks
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Mandatory training
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Define rules — &quot;every employee in dept X must hold cert
                Y&quot; — and track who&apos;s compliant.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-primary)] text-white px-4 py-2 text-sm font-medium hover:opacity-90"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New requirement
          </button>
        </header>

        <TrainingTabs active="mandatory" />

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            {error}
          </div>
        )}

        {totals && (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm">
            <div className="flex items-baseline justify-between gap-3 flex-wrap">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)]">
                  Overall compliance
                </p>
                <p className="mt-1 text-3xl font-bold text-[var(--color-gray-900)] tabular-nums">
                  {Math.round(totals.rate * 100)}%
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">
                  {totals.compliant_pairs} of {totals.total_pairs} employee ×
                  requirement pairs satisfied
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Round-2 redteam L finding: a stark "0/N compliant" tile is a
            dead-end — give the user a one-click path to the catalogue
            and a clear next step. */}
        {totals &&
          totals.total_pairs > 0 &&
          totals.compliant_pairs < totals.total_pairs && (
            <div className="rounded-[8px] border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 flex items-start gap-3">
              <AlertTriangle
                className="h-4 w-4 flex-shrink-0 mt-0.5"
                aria-hidden="true"
              />
              <div className="flex-1">
                <p className="font-medium">
                  {totals.total_pairs - totals.compliant_pairs} requirement
                  {totals.total_pairs - totals.compliant_pairs === 1
                    ? ""
                    : "s"}{" "}
                  not yet covered
                </p>
                <p className="mt-0.5 text-amber-800">
                  Browse SkillsFuture for grant-eligible courses (e.g. WSH
                  First-Aid, fire safety) to close the gap.
                </p>
              </div>
              <Link
                href="/training/skillsfuture"
                className="flex-shrink-0 rounded-md bg-amber-900 text-white px-3 py-1.5 text-xs font-medium hover:bg-amber-800 transition-colors"
              >
                Browse courses
              </Link>
            </div>
          )}

        {showForm && (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
              New mandatory requirement
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="text-xs text-[var(--color-gray-600)] sm:col-span-2">
                Requirement name
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="e.g. WSH First-Aider per workplace"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Required certification name
                <input
                  type="text"
                  value={certName}
                  onChange={(e) => setCertName(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="must match Certification.certification_name"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Applicable to
                <input
                  type="text"
                  value={applicableTo}
                  onChange={(e) => setApplicableTo(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="all | department:Operations | pass_type:wp | role:Driver"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Due within days of hire
                <input
                  type="number"
                  min={0}
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
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
                disabled={submitting || !name.trim() || !certName.trim()}
                className="rounded-md bg-[var(--color-primary)] text-white px-3 py-1.5 text-xs font-medium hover:opacity-90 disabled:opacity-50"
              >
                {submitting ? "Saving…" : "Save requirement"}
              </button>
            </div>
          </div>
        )}

        <div className="rounded-xl border border-[var(--color-gray-200)] bg-white shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-sm text-[var(--color-gray-500)]">
              <Loader2
                className="h-4 w-4 animate-spin inline-block mr-2"
                aria-hidden="true"
              />
              Loading…
            </div>
          ) : reqs.length === 0 ? (
            <div className="p-8 text-center text-sm text-[var(--color-gray-500)]">
              No mandatory training requirements yet.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-surface-page)]">
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Requirement
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Required cert
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Applies to
                  </th>
                  <th className="text-right py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Coverage
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Non-compliant
                  </th>
                </tr>
              </thead>
              <tbody>
                {reqs.map((r) => {
                  const cov = coverage?.coverage.find(
                    (c) => c.requirement_id === r.id,
                  );
                  const compliantPct =
                    cov && cov.applicable_count > 0
                      ? Math.round(
                          (cov.compliant_count / cov.applicable_count) * 100,
                        )
                      : 100;
                  return (
                    <tr
                      key={r.id}
                      className="border-b border-[var(--color-gray-100)] last:border-0 align-top"
                    >
                      <td className="py-2 px-4 font-medium text-[var(--color-gray-900)]">
                        {r.requirement_name}
                      </td>
                      <td className="py-2 px-4 text-[var(--color-gray-700)]">
                        {r.required_certification_name}
                      </td>
                      <td className="py-2 px-4 text-[var(--color-gray-700)]">
                        {r.applicable_to}
                      </td>
                      <td className="py-2 px-4 text-right tabular-nums">
                        {cov
                          ? `${cov.compliant_count} / ${cov.applicable_count} (${compliantPct}%)`
                          : "—"}
                      </td>
                      <td className="py-2 px-4 text-xs">
                        {!cov || cov.non_compliant_employee_ids.length === 0 ? (
                          <span className="text-emerald-700">
                            All compliant
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-red-700">
                            <AlertTriangle
                              className="h-3 w-3"
                              aria-hidden="true"
                            />
                            {cov.non_compliant_employee_ids
                              .slice(0, 3)
                              .map(employeeName)
                              .join(", ")}
                            {cov.non_compliant_employee_ids.length > 3
                              ? ` +${cov.non_compliant_employee_ids.length - 3} more`
                              : ""}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AdminGuard>
  );
}
