"use client";

/* P2-LD-5 (obayashi): Certifications page with expiry alerts. */

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ShieldCheck, Plus, Loader2, AlertTriangle } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import { trainingApi, type Certification } from "@/services/api/training";
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

const today = () => new Date().toISOString().split("T")[0];

export default function CertificationsPage() {
  const [certs, setCerts] = useState<Certification[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [empId, setEmpId] = useState<number | "">("");
  const [name, setName] = useState("");
  const [issuer, setIssuer] = useState("");
  const [issued, setIssued] = useState("");
  const [expires, setExpires] = useState("");

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, e] = await Promise.all([
        trainingApi.listCertifications(),
        employeesApi.list(),
      ]);
      setCerts(c.certifications);
      setEmployees(e.employees ?? []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load certifications.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const employeeName = (id: number) => {
    const e = employees.find((x) => x.id === id);
    return e?.name || "—";
  };

  const buckets = useMemo(() => {
    const today_ = today();
    const cutoff30 = new Date(Date.now() + 30 * 86400000)
      .toISOString()
      .split("T")[0];
    const expired: Certification[] = [];
    const expiringSoon: Certification[] = [];
    const active: Certification[] = [];
    for (const c of certs) {
      if (!c.expires_at) {
        active.push(c);
        continue;
      }
      if (c.expires_at < today_) expired.push(c);
      else if (c.expires_at <= cutoff30) expiringSoon.push(c);
      else active.push(c);
    }
    return { expired, expiringSoon, active };
  }, [certs]);

  const submit = async () => {
    if (!empId || !name.trim()) return;
    setSubmitting(true);
    try {
      await trainingApi.createCertification({
        employee_id: Number(empId),
        certification_name: name.trim(),
        issuing_body: issuer.trim(),
        issued_date: issued,
        expires_at: expires,
      });
      setShowForm(false);
      setEmpId("");
      setName("");
      setIssuer("");
      setIssued("");
      setExpires("");
      await fetchAll();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not save the certification.",
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
            <ShieldCheck
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Certifications
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                First-aid, professional licences, mandatory training certs.
                Expiring rows surface here 30 days ahead.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-primary)] text-white px-4 py-2 text-sm font-medium hover:opacity-90"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New certification
          </button>
        </header>

        <TrainingTabs active="certifications" />

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-4 shadow-sm">
            <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)]">
              Expired
            </p>
            <p className="mt-1 text-2xl font-bold text-red-600 tabular-nums">
              {buckets.expired.length}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-4 shadow-sm">
            <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)]">
              Expiring in 30 days
            </p>
            <p className="mt-1 text-2xl font-bold text-amber-600 tabular-nums">
              {buckets.expiringSoon.length}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-4 shadow-sm">
            <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)]">
              Active
            </p>
            <p className="mt-1 text-2xl font-bold text-emerald-600 tabular-nums">
              {buckets.active.length}
            </p>
          </div>
        </div>

        {showForm && (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
              Log a certification
            </h2>
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
                Certification name
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="e.g. First Aid Certificate"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Issuing body
                <input
                  type="text"
                  value={issuer}
                  onChange={(e) => setIssuer(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="e.g. Singapore Red Cross"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Issued date
                <input
                  type="date"
                  value={issued}
                  onChange={(e) => setIssued(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Expires (optional)
                <input
                  type="date"
                  value={expires}
                  onChange={(e) => setExpires(e.target.value)}
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
                disabled={submitting || !empId || !name.trim()}
                className="rounded-md bg-[var(--color-primary)] text-white px-3 py-1.5 text-xs font-medium hover:opacity-90 disabled:opacity-50"
              >
                {submitting ? "Saving…" : "Save certification"}
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
          ) : certs.length === 0 ? (
            <div className="p-8 text-center text-sm text-[var(--color-gray-500)]">
              No certifications recorded yet.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-surface-page)]">
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Employee
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Certification
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Issued
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Expires
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {[...certs]
                  .sort((a, b) =>
                    (a.expires_at || "9999").localeCompare(
                      b.expires_at || "9999",
                    ),
                  )
                  .map((c) => {
                    const today_ = today();
                    let status: { label: string; cls: string };
                    if (!c.expires_at) {
                      status = {
                        label: "No expiry",
                        cls: "bg-[var(--color-gray-100)] text-[var(--color-gray-700)]",
                      };
                    } else if (c.expires_at < today_) {
                      status = {
                        label: "Expired",
                        cls: "bg-red-50 text-red-700",
                      };
                    } else if (
                      c.expires_at <=
                      new Date(Date.now() + 30 * 86400000)
                        .toISOString()
                        .split("T")[0]
                    ) {
                      status = {
                        label: "Expiring",
                        cls: "bg-amber-50 text-amber-700",
                      };
                    } else {
                      status = {
                        label: "Active",
                        cls: "bg-emerald-50 text-emerald-700",
                      };
                    }
                    return (
                      <tr
                        key={c.id}
                        className="border-b border-[var(--color-gray-100)] last:border-0"
                      >
                        <td className="py-2 px-4">
                          {employeeName(c.employee_id)}
                        </td>
                        <td className="py-2 px-4">
                          <div className="font-medium text-[var(--color-gray-900)]">
                            {c.certification_name}
                          </div>
                          {c.issuing_body && (
                            <div className="text-xs text-[var(--color-gray-500)]">
                              {c.issuing_body}
                            </div>
                          )}
                        </td>
                        <td className="py-2 px-4">{c.issued_date || "—"}</td>
                        <td className="py-2 px-4">{c.expires_at || "—"}</td>
                        <td className="py-2 px-4">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${status.cls}`}
                          >
                            {status.label === "Expired" ||
                            status.label === "Expiring" ? (
                              <AlertTriangle
                                className="h-3 w-3"
                                aria-hidden="true"
                              />
                            ) : null}
                            {status.label}
                          </span>
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
