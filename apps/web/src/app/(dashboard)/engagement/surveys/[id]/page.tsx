"use client";

/**
 * /engagement/surveys/[id] — survey detail page with action panel (T46).
 *
 * Tabs: Aggregated | By cohort | Responses.
 * Bottom: Action panel with 3 suggested actions + accept-and-create-goal.
 */

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Lightbulb, Loader2, Lock, Send, X } from "lucide-react";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  engagementApi,
  formatAnonymityTierLabel,
  type EngagementSurvey,
  type AggregateResponse,
  type EngagementResponseRow,
  type SuggestedActionsResponse,
  type EngagementAction,
} from "@/services/api/engagement";
import { LikertDistributionBar } from "@/components/surveys";
import { Stat } from "@/components/engagement/Stat";

type DetailTab = "aggregated" | "by_cohort" | "responses";

export default function SurveyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const surveyId = Number(id);
  const [tab, setTab] = useState<DetailTab>("aggregated");
  const [survey, setSurvey] = useState<EngagementSurvey | null>(null);
  const [aggregate, setAggregate] = useState<AggregateResponse | null>(null);
  const [responses, setResponses] = useState<EngagementResponseRow[]>([]);
  const [responsesTier, setResponsesTier] = useState<string>("identified");
  const [suggested, setSuggested] = useState<SuggestedActionsResponse | null>(
    null,
  );
  const [actions, setActions] = useState<EngagementAction[]>([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const [s, agg, resp, sug, acts] = await Promise.all([
        engagementApi.getSurvey(surveyId),
        engagementApi.getAggregate(surveyId),
        engagementApi.listResponses(surveyId),
        engagementApi.getSuggestedActions(surveyId),
        engagementApi.listActions(surveyId),
      ]);
      setSurvey(s.survey);
      setAggregate(agg);
      setResponses(resp.responses);
      setResponsesTier(resp.anonymity_tier);
      setSuggested(sug);
      setActions(acts.actions);
    } catch (err) {
      console.error("Failed to load survey detail", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (Number.isFinite(surveyId) && surveyId > 0) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [surveyId]);

  async function closeSurvey() {
    if (!confirm("Close this survey? No new responses can be submitted.")) {
      return;
    }
    await engagementApi.closeSurvey(surveyId);
    refresh();
  }

  if (loading || !survey || !aggregate) {
    return (
      <AdminGuard>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 text-center text-[var(--color-gray-400)]">
          <Loader2 className="h-5 w-5 animate-spin inline mr-2" />
          Loading…
        </div>
      </AdminGuard>
    );
  }

  return (
    <AdminGuard>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Link
          href="/engagement"
          className="inline-flex items-center text-sm text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] mb-4"
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back to Engagement
        </Link>

        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-6 flex-wrap">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-gray-900)]">
              {survey.name}
            </h1>
            <div className="text-sm text-[var(--color-gray-500)] mt-1">
              {formatAnonymityTierLabel(survey.anonymity_tier)} ·{" "}
              {survey.target_count} recipients · {survey.response_count ?? 0}{" "}
              submitted
              {survey.target_count > 0 &&
                ` (${Math.round(((survey.response_count ?? 0) / survey.target_count) * 100)}%)`}
            </div>
            <div className="text-xs text-[var(--color-gray-400)] mt-0.5">
              Launched {survey.launched_at?.slice(0, 10)} · Closes{" "}
              {survey.closes_at?.slice(0, 10)}
              {survey.closed_at && (
                <span className="ml-2 text-rose-600">
                  · Closed {survey.closed_at.slice(0, 10)}
                </span>
              )}
            </div>
          </div>
          {!survey.closed_at && (
            <button
              onClick={closeSurvey}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-md border border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
            >
              <Lock className="h-4 w-4" />
              Close survey
            </button>
          )}
        </div>

        {/* Tabs */}
        <div className="border-b border-[var(--color-gray-200)] mb-6">
          <div className="flex gap-1">
            {(
              [
                { v: "aggregated", label: "Aggregated" },
                { v: "by_cohort", label: "By cohort" },
                { v: "responses", label: "Responses" },
              ] as const
            ).map(({ v, label }) => (
              <button
                key={v}
                onClick={() => setTab(v as DetailTab)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${tab === v ? "border-rose-600 text-rose-600" : "border-transparent text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        {tab === "aggregated" && <AggregatedView aggregate={aggregate} />}
        {tab === "by_cohort" && <ByCohortView aggregate={aggregate} />}
        {tab === "responses" && (
          <ResponsesView responses={responses} tier={responsesTier} />
        )}

        {/* Action panel */}
        <div className="mt-12 border-t border-[var(--color-gray-200)] pt-6">
          <h2 className="text-lg font-semibold text-[var(--color-gray-900)] flex items-center gap-2 mb-4">
            <Lightbulb className="h-5 w-5 text-amber-500" />
            Action panel
          </h2>
          <ActionPanel
            surveyId={surveyId}
            suggested={suggested}
            actions={actions}
            onAccept={refresh}
          />
        </div>
      </div>
    </AdminGuard>
  );
}

/* ── Tab views ─────────────────────────────────────────────── */

function AggregatedView({ aggregate }: { aggregate: AggregateResponse }) {
  if (aggregate.submitted_count === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] p-12 text-center text-sm text-[var(--color-gray-500)]">
        Waiting for first responses.
      </div>
    );
  }
  return (
    <div className="space-y-6">
      {!aggregate.is_anonymity_safe && (
        <div className="rounded-md bg-amber-50 border border-amber-200 text-amber-800 text-sm p-3">
          ⚠ Fewer than 5 responses received. Distributions are suppressed until
          n reaches 5.
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Stat
          label="Submitted"
          value={String(aggregate.submitted_count)}
          variant="card"
        />
        {aggregate.overall_avg_likert !== null && (
          <Stat
            label="Average Likert"
            value={`${aggregate.overall_avg_likert.toFixed(2)} / 5`}
            variant="card"
          />
        )}
        {aggregate.enps_score !== null && (
          <Stat
            label="eNPS"
            value={`${aggregate.enps_score > 0 ? "+" : ""}${aggregate.enps_score.toFixed(0)}`}
            variant="card"
          />
        )}
      </div>

      {aggregate.is_anonymity_safe && aggregate.by_question.length > 0 && (
        <div className="bg-white rounded-xl border border-[var(--color-gray-200)] p-5">
          <h3 className="font-medium mb-3">Per-question distribution</h3>
          <div className="space-y-3">
            {aggregate.by_question
              .filter((q) => q.is_anonymity_safe && q.distribution)
              .map((q) => (
                <div key={q.question_id}>
                  <div className="text-sm text-[var(--color-gray-700)] mb-1">
                    {q.question_id}
                  </div>
                  <LikertDistributionBar
                    distribution={q.distribution || {}}
                    avg={q.avg ?? null}
                    n={q.n}
                  />
                </div>
              ))}
          </div>
        </div>
      )}

      {aggregate.themes_tally.length > 0 && (
        <div className="bg-white rounded-xl border border-[var(--color-gray-200)] p-5">
          <h3 className="font-medium mb-3">Top themes</h3>
          <div className="flex flex-wrap gap-2">
            {aggregate.themes_tally.map((t) => (
              <span
                key={t.theme}
                className="inline-flex items-center gap-1 text-xs rounded-full bg-rose-50 text-rose-700 px-3 py-1"
              >
                {t.theme}
                <span className="text-rose-400">×{t.count}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ByCohortView({ aggregate }: { aggregate: AggregateResponse }) {
  if (aggregate.by_cohort.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] p-12 text-center text-sm text-[var(--color-gray-500)]">
        No cohort breakdowns yet.
      </div>
    );
  }
  return (
    <div className="bg-white rounded-xl border border-[var(--color-gray-200)] overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-[var(--color-gray-50)] text-[var(--color-gray-500)] uppercase text-xs">
          <tr>
            <th className="text-left px-4 py-3">Cohort</th>
            <th className="text-right px-4 py-3">n</th>
            <th className="text-right px-4 py-3">Avg Likert</th>
            <th className="text-left px-4 py-3">Top themes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-gray-100)]">
          {aggregate.by_cohort.map((c) => (
            <tr key={c.label}>
              <td className="px-4 py-3 font-medium">{c.label}</td>
              <td className="px-4 py-3 text-right">{c.n}</td>
              <td className="px-4 py-3 text-right">
                {c.is_anonymity_safe &&
                c.avg_likert !== null &&
                c.avg_likert !== undefined
                  ? c.avg_likert.toFixed(2)
                  : `n=${c.n} (suppressed)`}
              </td>
              <td className="px-4 py-3">
                {c.is_anonymity_safe && c.themes && c.themes.length > 0
                  ? c.themes.map((t) => `${t.theme} (${t.count})`).join(", ")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResponsesView({
  responses,
  tier,
}: {
  responses: EngagementResponseRow[];
  tier: string;
}) {
  if (responses.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] p-12 text-center text-sm text-[var(--color-gray-500)]">
        No responses yet.
      </div>
    );
  }
  return (
    <div className="bg-white rounded-xl border border-[var(--color-gray-200)] overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-[var(--color-gray-50)] text-[var(--color-gray-500)] uppercase text-xs">
          <tr>
            <th className="text-left px-4 py-3">Respondent</th>
            <th className="text-left px-4 py-3">Submitted</th>
            <th className="text-left px-4 py-3">Themes</th>
            {tier === "identified" && (
              <th className="text-left px-4 py-3">Email</th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-gray-100)]">
          {responses.map((r) => {
            let themes: string[] = [];
            try {
              const parsed = JSON.parse(r.themes || "[]");
              themes = Array.isArray(parsed) ? parsed : [];
            } catch {
              /* ignore */
            }
            return (
              <tr key={r.id}>
                <td className="px-4 py-3 font-medium">
                  {r.employee_name || "—"}
                </td>
                <td className="px-4 py-3 text-[var(--color-gray-500)]">
                  {r.submitted_at
                    ? r.submitted_at.slice(0, 19).replace("T", " ")
                    : "Pending"}
                </td>
                <td className="px-4 py-3">
                  {themes.length > 0 ? themes.join(", ") : "—"}
                </td>
                {tier === "identified" && (
                  <td className="px-4 py-3 text-[var(--color-gray-500)]">
                    {r.employee_email || "—"}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ── Action panel ──────────────────────────────────────────── */

function ActionPanel({
  surveyId,
  suggested,
  actions,
  onAccept,
}: {
  surveyId: number;
  suggested: SuggestedActionsResponse | null;
  actions: EngagementAction[];
  onAccept: () => void;
}) {
  const [acceptingIdx, setAcceptingIdx] = useState<number | null>(null);
  const [showGoalModal, setShowGoalModal] = useState<{
    text: string;
    cohort: string;
    theme: string;
  } | null>(null);

  if (!suggested || suggested.reason === "insufficient_cohort_size") {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] p-6 text-center text-sm text-[var(--color-gray-500)]">
        Action suggestions need at least 5 responses in a cohort. They&apos;ll
        appear once your team grows.
      </div>
    );
  }

  const accepted = actions.filter((a) => a.status === "accepted");

  return (
    <div className="space-y-6">
      {suggested.suggestions && suggested.suggestions.length > 0 && (
        <div>
          <p className="text-sm text-[var(--color-gray-600)] mb-3">
            Lowest-scoring cohort:{" "}
            <span className="font-medium">{suggested.cohort_label}</span> scored{" "}
            <span className="font-medium text-rose-600">
              {suggested.score?.toFixed(2)}
            </span>{" "}
            on theme <em>{suggested.theme}</em>. Suggested actions:
          </p>
          <div className="grid gap-3 md:grid-cols-3">
            {suggested.suggestions.map((s, i) => (
              <div
                key={i}
                className="rounded-lg border border-[var(--color-gray-200)] bg-white p-4 flex flex-col"
              >
                <p className="text-sm flex-1">{s.text}</p>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() =>
                      setShowGoalModal({
                        text: s.text,
                        cohort: suggested.cohort_label || "",
                        theme: suggested.theme || "",
                      })
                    }
                    disabled={acceptingIdx !== null}
                    className="flex-1 text-xs py-1.5 rounded bg-rose-600 hover:bg-rose-700 text-white disabled:opacity-50"
                  >
                    Accept
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {accepted.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[var(--color-gray-700)] mb-2">
            Already accepted
          </h3>
          <div className="space-y-2">
            {accepted.map((a) => (
              <div
                key={a.id}
                className="rounded-md bg-[var(--color-gray-50)] p-3 text-sm"
              >
                <div className="font-medium">{a.suggested_action_text}</div>
                {a.cohort_label && (
                  <div className="text-xs text-[var(--color-gray-500)] mt-0.5">
                    For: {a.cohort_label}
                  </div>
                )}
                {a.linked_goal_id > 0 && (
                  <Link
                    href={`/goals/${a.linked_goal_id}`}
                    className="inline-block mt-1 text-xs text-rose-600 hover:underline"
                  >
                    → View linked Goal #{a.linked_goal_id}
                  </Link>
                )}
                {a.next_pulse_question && (
                  <div className="text-xs text-[var(--color-gray-500)] mt-1 italic">
                    Next pulse will ask: &ldquo;{a.next_pulse_question}&rdquo;
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {showGoalModal && (
        <CreateActionModal
          surveyId={surveyId}
          actionText={showGoalModal.text}
          cohort={showGoalModal.cohort}
          theme={showGoalModal.theme}
          onClose={() => setShowGoalModal(null)}
          onCreated={() => {
            setShowGoalModal(null);
            onAccept();
          }}
        />
      )}
    </div>
  );
}

function CreateActionModal({
  surveyId,
  actionText,
  cohort,
  theme,
  onClose,
  onCreated,
}: {
  surveyId: number;
  actionText: string;
  cohort: string;
  theme: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [createGoal, setCreateGoal] = useState(true);
  const [editedText, setEditedText] = useState(actionText);
  const [nextPulseQuestion, setNextPulseQuestion] = useState("");
  // D2 (red-team Phase 2): default the goal title to a concise,
  // demo-friendly format ("<Cohort>: <theme> action") rather than the
  // verbose "Engagement: Launch L&D pilot with a per-head learning..."
  // that auto-derived from the full action text. HR can edit before
  // submit so the linked Goal title looks good in the Goals module.
  const defaultGoalTitle = `${cohort || "Company"}: ${
    theme ? `${theme} action` : "engagement action"
  }`;
  const [goalTitle, setGoalTitle] = useState(defaultGoalTitle);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await engagementApi.createAction(surveyId, {
        cohort_label: cohort,
        finding_summary: `${cohort} scored low on theme: ${theme}`,
        suggested_action_text: editedText,
        /* D4: pass the suggestion's theme through so the loop-closing
           card matches it exactly instead of substring-fishing in
           finding_summary. */
        theme: theme,
        next_pulse_question: nextPulseQuestion,
        status: "accepted",
        create_linked_goal: createGoal,
        goal_title: createGoal
          ? goalTitle.trim() || defaultGoalTitle
          : undefined,
      });
      onCreated();
    } catch (err) {
      setError((err as Error).message || "Failed to create action");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Accept action</h3>
          <button onClick={onClose}>
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>

        <label className="block text-sm font-medium mb-1">Action</label>
        <textarea
          value={editedText}
          onChange={(e) => setEditedText(e.target.value)}
          rows={3}
          className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 text-sm mb-3"
        />

        <label className="block text-sm font-medium mb-1">
          Next pulse will ask (optional)
        </label>
        <input
          type="text"
          value={nextPulseQuestion}
          onChange={(e) => setNextPulseQuestion(e.target.value)}
          placeholder="e.g. How clear is your career path here?"
          className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 text-sm mb-4"
        />

        <label className="flex items-center gap-2 text-sm mb-3">
          <input
            type="checkbox"
            checked={createGoal}
            onChange={(e) => setCreateGoal(e.target.checked)}
          />
          Track this as a Goal in the Goals module
        </label>

        {createGoal && (
          <div className="mb-4 pl-6 border-l-2 border-rose-100">
            <label className="block text-xs font-medium text-[var(--color-gray-700)] mb-1">
              Goal title (shown in /goals)
            </label>
            <input
              type="text"
              value={goalTitle}
              onChange={(e) => setGoalTitle(e.target.value)}
              placeholder={defaultGoalTitle}
              className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 text-sm"
            />
          </div>
        )}

        {error && (
          <div className="rounded-md bg-red-50 text-red-700 text-sm p-2 mb-3">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-md border border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting || !editedText.trim()}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-md bg-rose-600 hover:bg-rose-700 text-white disabled:opacity-50"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            <Send className="h-3.5 w-3.5" />
            Accept
          </button>
        </div>
      </div>
    </div>
  );
}

/* Stat extracted to /components/engagement/Stat.tsx (C1).
   Detail page uses variant="card" — wrapped in white card. */
