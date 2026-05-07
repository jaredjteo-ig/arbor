"use client";

/**
 * /my-engagement-surveys — employee landing page (M5 T50).
 *
 * Round-3 layout (top to bottom):
 *  1. Loop-closing card — "Last pulse you said X. Action taken: Y."
 *  2. Pending check-ins (cards with Start button)
 *  3. History (collapsed accordion, identified-tier surveys only)
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Loader2,
  MessageSquareHeart,
  ChevronDown,
  ChevronUp,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import {
  engagementApi,
  type LoopClosingPayload,
  type PendingResponse,
  type HistoryEntry,
} from "@/services/api/engagement";

export default function MyEngagementSurveysPage() {
  const [loopPayload, setLoopPayload] = useState<LoopClosingPayload | null>(
    null,
  );
  const [pending, setPending] = useState<PendingResponse[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [lc, p, h] = await Promise.all([
          engagementApi.myLoopClosing(),
          engagementApi.myPending(),
          engagementApi.myHistory(),
        ]);
        setLoopPayload(lc.payload);
        setPending(p.pending);
        setHistory(h.history);
      } catch (err) {
        setError((err as Error).message || "Failed to load engagement data");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center text-[var(--color-gray-400)]">
        <Loader2 className="h-5 w-5 animate-spin inline mr-2" />
        Loading…
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center gap-2 mb-6">
        <MessageSquareHeart className="h-6 w-6 text-rose-500" />
        <h1 className="text-2xl font-semibold text-[var(--color-gray-900)]">
          My Engagement
        </h1>
      </div>

      {/* Loop-closing card */}
      {loopPayload && <LoopClosingCard payload={loopPayload} />}

      {/* Pending check-ins */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-[var(--color-gray-900)] mb-3">
          Pending check-ins
        </h2>
        {pending.length === 0 ? (
          <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] bg-white p-8 text-center text-sm text-[var(--color-gray-500)]">
            No pending check-ins. We&apos;ll let you know when your team has a
            new pulse.
          </div>
        ) : (
          <div className="space-y-3">
            {pending.map((p) => (
              <PendingCard key={p.response_id} pending={p} />
            ))}
          </div>
        )}
      </section>

      {/* History (collapsed) */}
      <section>
        <button
          onClick={() => setShowHistory((v) => !v)}
          className="flex items-center gap-2 text-sm font-medium text-[var(--color-gray-700)] hover:text-[var(--color-gray-900)]"
          aria-expanded={showHistory}
        >
          {showHistory ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
          History
          <span className="text-[var(--color-gray-400)]">
            ({history.length})
          </span>
        </button>
        {showHistory && (
          <div className="mt-3">
            {history.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] bg-white p-6 text-sm text-[var(--color-gray-500)]">
                Your past responses appear here once you submit. Anonymous
                surveys are never shown — there&apos;s no trail back to you.
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-[var(--color-gray-200)] divide-y divide-[var(--color-gray-100)]">
                {history.map((h) => (
                  <div
                    key={h.response_id}
                    className="p-4 text-sm flex items-start justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <div className="font-medium text-[var(--color-gray-900)]">
                        {h.survey_name}
                      </div>
                      <div className="text-xs text-[var(--color-gray-500)] mt-0.5">
                        Submitted {h.submitted_at?.slice(0, 10) ?? "—"}
                        {h.anonymity_tier === "pseudonymous" && (
                          <span className="ml-2 text-blue-700">
                            · Pseudonymous (HR sees only your pseudonym)
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {error && (
        <div className="mt-6 rounded-md bg-red-50 text-red-700 text-sm p-3">
          {error}
        </div>
      )}
    </div>
  );
}

function LoopClosingCard({ payload }: { payload: LoopClosingPayload }) {
  /* D3 (red-team Phase 2): three states.
     - "action_taken"  → "HR did <headline>" + linked goal
     - "under_review"  → "HR is reviewing this" (an admin has opened it)
     - "notified"      → "HR has been notified" (no admin view yet)

     The original copy "HR has seen this — actions in progress" was
     factually wrong when no admin had actually opened the dashboard.
     The new states stay verifiable. */
  const status =
    payload.status ?? (payload.action_taken ? "action_taken" : "notified");
  return (
    <div className="rounded-xl bg-gradient-to-br from-rose-50 to-amber-50 border border-rose-200 p-5 mb-8">
      <div className="flex items-start gap-3">
        <Sparkles className="h-5 w-5 text-rose-500 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--color-gray-900)] mb-1">
            Last pulse, your team raised{" "}
            <span className="font-semibold text-rose-700">
              {payload.top_theme || "engagement themes"}
            </span>
            .
          </p>
          {status === "action_taken" && payload.action_taken ? (
            <>
              <p className="text-sm text-[var(--color-gray-700)] mt-2">
                <span className="font-medium">HR did:</span>{" "}
                {payload.action_taken.headline}
              </p>
              {payload.action_taken.linked_goal_label && (
                <p className="text-xs text-[var(--color-gray-500)] mt-1">
                  → Linked to:{" "}
                  <span className="italic">
                    {payload.action_taken.linked_goal_label}
                  </span>
                </p>
              )}
            </>
          ) : status === "under_review" ? (
            <p className="text-sm text-[var(--color-gray-700)] mt-2">
              HR is reviewing this. An action will appear here once it&apos;s
              decided.
            </p>
          ) : (
            <p className="text-sm text-[var(--color-gray-700)] mt-2">
              HR has been notified. They&apos;ll see this on their engagement
              dashboard.
            </p>
          )}
          {payload.next_pulse_anchored_question && (
            <p className="text-xs text-[var(--color-gray-600)] mt-3 italic">
              Next pulse will ask: &ldquo;
              {payload.next_pulse_anchored_question}&rdquo;
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function PendingCard({ pending }: { pending: PendingResponse }) {
  const closesIn = pending.closes_at
    ? daysBetween(new Date(), new Date(pending.closes_at))
    : null;
  return (
    <div className="rounded-xl bg-white border border-[var(--color-gray-200)] p-5 flex items-center justify-between gap-4">
      <div className="min-w-0">
        <h3 className="font-medium text-[var(--color-gray-900)] truncate">
          {pending.survey_name}
        </h3>
        <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
          About 90 seconds
          {closesIn !== null &&
            ` · closes in ${closesIn} day${closesIn === 1 ? "" : "s"}`}
        </p>
      </div>
      <Link
        href={`/my-engagement-surveys/${pending.response_id}/respond`}
        className="inline-flex items-center gap-1 px-4 py-2 rounded-md bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium flex-shrink-0"
      >
        Start
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}

function daysBetween(a: Date, b: Date): number {
  return Math.max(0, Math.ceil((b.getTime() - a.getTime()) / 86400000));
}
