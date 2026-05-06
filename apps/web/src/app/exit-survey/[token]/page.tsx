"use client";

/* P2-EX-2 (obayashi): Public exit-survey page — submit via tokenised link.
   Lives outside the dashboard route group (no AdminGuard, no sidebar).
*/

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

const REASON_OPTIONS = [
  "comp",
  "growth",
  "manager",
  "role",
  "location",
  "family",
  "retirement",
  "workload",
  "culture",
  "other",
];

const REASON_LABELS: Record<string, string> = {
  comp: "Compensation",
  growth: "Career growth",
  manager: "Manager / leadership",
  role: "Role / scope fit",
  location: "Location / commute",
  family: "Family",
  retirement: "Retirement",
  workload: "Workload / burnout",
  culture: "Culture / environment",
  other: "Other",
};

export default function ExitSurveyPage() {
  const params = useParams();
  const token = (params?.token as string) ?? "";

  const [overall, setOverall] = useState(0);
  const [fairness, setFairness] = useState(0);
  const [reasons, setReasons] = useState<string[]>([]);
  const [worked, setWorked] = useState("");
  const [change, setChange] = useState("");
  const [recommend, setRecommend] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Round-2 redteam L finding: preflight token check on mount so the
  // user sees the right empty state (gone, expired, already submitted)
  // before investing time filling the form.
  type Preflight =
    | { state: "loading" }
    | { state: "ok"; isAnonymous: boolean }
    | { state: "invalid" }
    | { state: "not_found" }
    | { state: "already_submitted"; submittedAt?: string }
    | { state: "network_error" };
  const [preflight, setPreflight] = useState<Preflight>({ state: "loading" });

  useEffect(() => {
    if (!token) return;
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(
          `${apiBase}/exit-interviews/public/${encodeURIComponent(token)}/validate`,
          { method: "GET" },
        );
        if (cancelled) return;
        if (!r.ok) {
          setPreflight({ state: "network_error" });
          return;
        }
        const body = await r.json();
        if (body?.ok) {
          setPreflight({ state: "ok", isAnonymous: !!body.is_anonymous });
        } else if (body?.reason === "already_submitted") {
          setPreflight({
            state: "already_submitted",
            submittedAt: body.submitted_at,
          });
        } else if (body?.reason === "not_found") {
          setPreflight({ state: "not_found" });
        } else {
          setPreflight({ state: "invalid" });
        }
      } catch {
        if (!cancelled) setPreflight({ state: "network_error" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const toggleReason = (r: string) => {
    setReasons((prev) =>
      prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r],
    );
  };

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const r = await fetch(
        `${apiBase}/exit-interviews/${encodeURIComponent(token)}/submit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            q1_overall: overall,
            q2_fairness: fairness,
            q3_reasons: reasons,
            q4_what_worked: worked,
            q5_what_to_change: change,
            q6_recommend_why: recommend,
          }),
        },
      );
      if (!r.ok) {
        const detail = await r.text();
        throw new Error(detail || `HTTP ${r.status}`);
      }
      setDone(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not submit.");
    } finally {
      setSubmitting(false);
    }
  };

  const Likert = ({
    value,
    onChange,
    label,
  }: {
    value: number;
    onChange: (n: number) => void;
    label: string;
  }) => (
    <fieldset className="space-y-1">
      <legend className="text-sm font-medium text-[var(--color-gray-900)]">
        {label}
      </legend>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((n) => (
          <label
            key={n}
            className={`flex-1 cursor-pointer rounded-md border py-2 text-center text-sm ${
              value === n
                ? "border-[var(--color-primary)] bg-[var(--color-primary-50)] text-[var(--color-primary)] font-semibold"
                : "border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
            }`}
          >
            <input
              type="radio"
              name={label}
              value={n}
              checked={value === n}
              onChange={() => onChange(n)}
              className="sr-only"
            />
            {n}
          </label>
        ))}
      </div>
      <div className="flex justify-between text-[10px] text-[var(--color-gray-400)] mt-0.5 px-1">
        <span>Poor</span>
        <span>Excellent</span>
      </div>
    </fieldset>
  );

  if (done || preflight.state === "already_submitted") {
    const submittedAt =
      preflight.state === "already_submitted" ? preflight.submittedAt : null;
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-surface-page)] p-6">
        <div className="max-w-md w-full rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center">
          <h1 className="text-xl font-semibold text-emerald-900">Thank you</h1>
          <p className="mt-2 text-sm text-emerald-800">
            {done
              ? "Your responses have been recorded. We appreciate the candour."
              : "This exit interview has already been submitted. Thank you for sharing earlier."}
          </p>
          {submittedAt && (
            <p className="mt-2 text-xs text-emerald-700">
              Submitted on {new Date(submittedAt).toLocaleDateString()}.
            </p>
          )}
        </div>
      </div>
    );
  }

  if (
    preflight.state === "invalid" ||
    preflight.state === "not_found" ||
    preflight.state === "network_error"
  ) {
    const copy =
      preflight.state === "not_found"
        ? "We couldn't find this exit interview. The link may have been revoked."
        : preflight.state === "network_error"
          ? "We couldn't reach the survey service. Please refresh in a moment."
          : "This survey link is invalid or has expired. Please reach out to your HR contact for a fresh link.";
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-surface-page)] p-6">
        <div className="max-w-md w-full rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
          <h1 className="text-xl font-semibold text-amber-900">
            Survey unavailable
          </h1>
          <p className="mt-2 text-sm text-amber-800">{copy}</p>
        </div>
      </div>
    );
  }

  if (preflight.state === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-surface-page)] p-6">
        <div className="text-sm text-[var(--color-gray-600)]">
          Loading your exit interview…
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-surface-page)] py-8 px-4 sm:px-6">
      <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-sm border border-[var(--color-gray-200)] p-6 space-y-6">
        <header>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Exit interview
          </h1>
          <p className="mt-1 text-sm text-[var(--color-gray-600)]">
            Thanks for taking five minutes to share what your time here was
            like. Your responses help us improve for the people who follow.
          </p>
        </header>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            {error}
          </div>
        )}

        <Likert
          value={overall}
          onChange={setOverall}
          label="How would you rate your overall experience?"
        />
        <Likert
          value={fairness}
          onChange={setFairness}
          label="How fairly were you treated?"
        />

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-[var(--color-gray-900)]">
            Reasons for leaving (pick any that apply)
          </legend>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {REASON_OPTIONS.map((r) => (
              <label
                key={r}
                className={`cursor-pointer rounded-md border px-3 py-1.5 text-xs ${
                  reasons.includes(r)
                    ? "border-[var(--color-primary)] bg-[var(--color-primary-50)] text-[var(--color-primary)] font-medium"
                    : "border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
                }`}
              >
                <input
                  type="checkbox"
                  checked={reasons.includes(r)}
                  onChange={() => toggleReason(r)}
                  className="sr-only"
                />
                {REASON_LABELS[r]}
              </label>
            ))}
          </div>
        </fieldset>

        <label className="block text-sm">
          <span className="font-medium text-[var(--color-gray-900)]">
            What worked well?
          </span>
          <textarea
            value={worked}
            onChange={(e) => setWorked(e.target.value)}
            rows={3}
            maxLength={2000}
            className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-[var(--color-gray-900)]">
            What would you change?
          </span>
          <textarea
            value={change}
            onChange={(e) => setChange(e.target.value)}
            rows={3}
            maxLength={2000}
            className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-[var(--color-gray-900)]">
            Would you recommend us as an employer? Why or why not?
          </span>
          <textarea
            value={recommend}
            onChange={(e) => setRecommend(e.target.value)}
            rows={3}
            maxLength={2000}
            className="mt-1 block w-full rounded-md border border-[var(--color-gray-300)] px-3 py-2 text-sm"
          />
        </label>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={submit}
            disabled={submitting || overall === 0 || fairness === 0}
            className="rounded-md bg-[var(--color-primary)] text-white px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Submit"}
          </button>
        </div>
      </div>
    </div>
  );
}
