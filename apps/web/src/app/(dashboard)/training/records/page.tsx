"use client";

/* P2-LD-4 (obayashi): Training records — admin + employee views.
   Tabs at the top of the route family link Records / Certifications /
   Mandatory / SkillsFuture catalogue.
*/

import { useEffect, useState } from "react";
import Link from "next/link";
import { GraduationCap, Plus, Archive, Loader2 } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import { trainingApi, type TrainingRecord } from "@/services/api/training";
import { employeesApi, type Employee } from "@/services/api/employees";

const COURSE_TYPES = [
  { value: "internal", label: "Internal" },
  { value: "external", label: "External" },
  { value: "skillsfuture", label: "SkillsFuture" },
];

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

export default function TrainingRecordsPage() {
  const [records, setRecords] = useState<TrainingRecord[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [empId, setEmpId] = useState<number | "">("");
  const [courseName, setCourseName] = useState("");
  const [courseProvider, setCourseProvider] = useState("");
  const [courseType, setCourseType] = useState("internal");
  const [hours, setHours] = useState<number | "">("");
  const [completion, setCompletion] = useState("");

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, e] = await Promise.all([
        trainingApi.listRecords(),
        employeesApi.list(),
      ]);
      setRecords(r.records);
      setEmployees(e.employees ?? []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load training records.",
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
    return e?.name || `#${id}`;
  };

  const submit = async () => {
    if (!empId || !courseName.trim()) return;
    setSubmitting(true);
    try {
      await trainingApi.createRecord({
        employee_id: Number(empId),
        course_name: courseName.trim(),
        course_provider: courseProvider.trim(),
        course_type: courseType as TrainingRecord["course_type"],
        hours: typeof hours === "number" ? hours : 0,
        completion_date: completion,
      });
      setShowForm(false);
      setEmpId("");
      setCourseName("");
      setCourseProvider("");
      setHours("");
      setCompletion("");
      await fetchAll();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save the record.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const archive = async (id: number) => {
    try {
      await trainingApi.archiveRecord(id);
      await fetchAll();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not archive the record.",
      );
    }
  };

  return (
    <AdminGuard>
      <div className="max-w-6xl mx-auto space-y-5 pb-12">
        <header className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <GraduationCap
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Training records
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Internal courses, external providers, SkillsFuture grants —
                logged per employee.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-primary)] text-white px-4 py-2 text-sm font-medium hover:opacity-90"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New record
          </button>
        </header>

        <TrainingTabs active="records" />

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            {error}
          </div>
        )}

        {showForm && (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
              Log a training event
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
                Course type
                <select
                  value={courseType}
                  onChange={(e) => setCourseType(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                >
                  {COURSE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-[var(--color-gray-600)] sm:col-span-2">
                Course name
                <input
                  type="text"
                  value={courseName}
                  onChange={(e) => setCourseName(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="e.g. Effective Workplace Communication"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Provider
                <input
                  type="text"
                  value={courseProvider}
                  onChange={(e) => setCourseProvider(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="e.g. NTUC LearningHub"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Hours
                <input
                  type="number"
                  min={0}
                  step={0.5}
                  value={hours}
                  onChange={(e) =>
                    setHours(
                      e.target.value === "" ? "" : Number(e.target.value),
                    )
                  }
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                />
              </label>
              <label className="text-xs text-[var(--color-gray-600)]">
                Completion date
                <input
                  type="date"
                  value={completion}
                  onChange={(e) => setCompletion(e.target.value)}
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
                disabled={submitting || !empId || !courseName.trim()}
                className="rounded-md bg-[var(--color-primary)] text-white px-3 py-1.5 text-xs font-medium hover:opacity-90 disabled:opacity-50"
              >
                {submitting ? "Saving…" : "Save record"}
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
          ) : records.length === 0 ? (
            <div className="p-8 text-center text-sm text-[var(--color-gray-500)]">
              No training records yet. Use “New record” above to log your first
              one.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-surface-page)]">
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Employee
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Course
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Type
                  </th>
                  <th className="text-right py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Hours
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Completed
                  </th>
                  <th className="text-right py-2 px-4 font-medium text-[var(--color-gray-600)]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-[var(--color-gray-100)] last:border-0"
                  >
                    <td className="py-2 px-4">{employeeName(r.employee_id)}</td>
                    <td className="py-2 px-4">
                      <div className="font-medium text-[var(--color-gray-900)]">
                        {r.course_name}
                      </div>
                      {r.course_provider && (
                        <div className="text-xs text-[var(--color-gray-500)]">
                          {r.course_provider}
                        </div>
                      )}
                    </td>
                    <td className="py-2 px-4 capitalize">{r.course_type}</td>
                    <td className="py-2 px-4 text-right tabular-nums">
                      {r.hours.toFixed(1)}
                    </td>
                    <td className="py-2 px-4">{r.completion_date || "—"}</td>
                    <td className="py-2 px-4 text-right">
                      <button
                        type="button"
                        onClick={() => archive(r.id)}
                        className="inline-flex items-center gap-1 text-xs text-[var(--color-gray-500)] hover:text-[var(--color-gray-900)]"
                        aria-label="Archive training record"
                      >
                        <Archive className="h-3.5 w-3.5" aria-hidden="true" />
                        Archive
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AdminGuard>
  );
}
