"use client";

/* P2-RC-3 (obayashi): Recognition page — give kudos, see public feed,
   see kudos received. Tabs link the three views.
*/

import { useEffect, useMemo, useState } from "react";
import { Award, Plus, Loader2 } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  recognitionApi,
  type Recognition,
  type RecognitionCategory,
} from "@/services/api/recognition";
import { employeesApi, type Employee } from "@/services/api/employees";

type TabKey = "give" | "feed" | "received";

const CATEGORIES: { key: RecognitionCategory; label: string }[] = [
  { key: "above_and_beyond", label: "Above and Beyond" },
  { key: "teamwork", label: "Teamwork" },
  { key: "customer", label: "Customer Focus" },
  { key: "innovation", label: "Innovation" },
  { key: "values", label: "Lives the Values" },
];

const CATEGORY_BADGE: Record<RecognitionCategory, string> = {
  above_and_beyond: "bg-purple-50 text-purple-700",
  teamwork: "bg-blue-50 text-blue-700",
  customer: "bg-emerald-50 text-emerald-700",
  innovation: "bg-amber-50 text-amber-700",
  values: "bg-pink-50 text-pink-700",
};

export default function RecognitionPage() {
  const [tab, setTab] = useState<TabKey>("feed");
  const [feed, setFeed] = useState<Recognition[]>([]);
  const [received, setReceived] = useState<Recognition[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [toEmp, setToEmp] = useState<number | "">("");
  const [category, setCategory] =
    useState<RecognitionCategory>("above_and_beyond");
  const [message, setMessage] = useState("");
  const [isPublic, setIsPublic] = useState(true);

  const employeeName = (id: number) =>
    employees.find((e) => e.id === id)?.name || "—";

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [f, r, e] = await Promise.all([
        recognitionApi.feed(30),
        recognitionApi.received(),
        employeesApi.list(),
      ]);
      setFeed(f.feed);
      setReceived(r.recognition);
      setEmployees(e.employees ?? []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load recognition data.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const submit = async () => {
    if (!toEmp || !message.trim()) return;
    setSubmitting(true);
    try {
      await recognitionApi.give({
        to_employee_id: Number(toEmp),
        category,
        message: message.trim(),
        is_public: isPublic,
      });
      setToEmp("");
      setMessage("");
      setCategory("above_and_beyond");
      setIsPublic(true);
      setTab("feed");
      await fetchAll();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save recognition.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: "give", label: "Give kudos" },
    { key: "feed", label: "Public feed", count: feed.length },
    { key: "received", label: "Received by me", count: received.length },
  ];

  const renderCard = (r: Recognition) => (
    <div
      key={r.id}
      className="rounded-xl border border-[var(--color-gray-200)] bg-white p-4 shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-[var(--color-gray-700)]">
            <span className="font-medium text-[var(--color-gray-900)]">
              For {employeeName(r.to_employee_id)}
            </span>
          </p>
          <p className="mt-1 text-sm text-[var(--color-gray-700)] whitespace-pre-line">
            {r.message}
          </p>
          <div className="mt-2 flex items-center gap-2 text-[11px] text-[var(--color-gray-500)]">
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 font-medium ${CATEGORY_BADGE[r.category]}`}
            >
              {CATEGORIES.find((c) => c.key === r.category)?.label ??
                r.category}
            </span>
            <span>·</span>
            <span>
              {new Date(r.created_at).toLocaleDateString("en-SG", {
                day: "numeric",
                month: "short",
              })}
            </span>
            {!r.is_public && (
              <>
                <span>·</span>
                <span className="italic">private</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <AdminGuard>
      <div className="max-w-5xl mx-auto space-y-5 pb-12">
        <header className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <Award
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Recognition
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Give peer kudos and see who&apos;s been recognised across the
                team.
              </p>
            </div>
          </div>
        </header>

        <nav
          className="flex gap-1 border-b border-[var(--color-gray-200)]"
          role="tablist"
        >
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === t.key
                  ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                  : "border-transparent text-[var(--color-gray-600)] hover:text-[var(--color-gray-900)]"
              }`}
            >
              {t.label}
              {typeof t.count === "number" && (
                <span className="ml-2 text-[10px] text-[var(--color-gray-500)] tabular-nums">
                  ({t.count})
                </span>
              )}
            </button>
          ))}
        </nav>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            {error}
          </div>
        )}

        {tab === "give" && (
          <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 shadow-sm">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="text-xs text-[var(--color-gray-600)]">
                Recipient
                <select
                  value={toEmp}
                  onChange={(e) =>
                    setToEmp(
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
                Category
                <select
                  value={category}
                  onChange={(e) =>
                    setCategory(e.target.value as RecognitionCategory)
                  }
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c.key} value={c.key}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-[var(--color-gray-600)] sm:col-span-2">
                Message
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={4}
                  maxLength={1000}
                  className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-1.5 text-sm"
                  placeholder="What did they do that deserves recognition?"
                />
                <span className="text-[10px] text-[var(--color-gray-400)]">
                  {message.length}/1000
                </span>
              </label>
              <label className="text-xs text-[var(--color-gray-700)] flex items-center gap-2 sm:col-span-2">
                <input
                  type="checkbox"
                  checked={isPublic}
                  onChange={(e) => setIsPublic(e.target.checked)}
                />
                Show on the public feed
              </label>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={submit}
                disabled={submitting || !toEmp || !message.trim()}
                className="inline-flex items-center gap-1 rounded-md bg-[var(--color-primary)] text-white px-4 py-1.5 text-xs font-medium hover:opacity-90 disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                {submitting ? "Sending…" : "Send kudos"}
              </button>
            </div>
          </div>
        )}

        {tab !== "give" && (
          <div className="space-y-3">
            {loading ? (
              <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-8 text-center text-sm text-[var(--color-gray-500)]">
                <Loader2
                  className="h-4 w-4 animate-spin inline-block mr-2"
                  aria-hidden="true"
                />
                Loading…
              </div>
            ) : (tab === "feed" ? feed : received).length === 0 ? (
              <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-8 text-center text-sm text-[var(--color-gray-500)]">
                {tab === "feed"
                  ? "No public kudos in the last 30 days. Use the Give tab to start."
                  : "No kudos received yet."}
              </div>
            ) : (
              (tab === "feed" ? feed : received).map(renderCard)
            )}
          </div>
        )}
      </div>
    </AdminGuard>
  );
}
