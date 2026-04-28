"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Sparkles, AlertTriangle } from "lucide-react";

import { toast } from "@/components/design-system";
import { recruitmentApi } from "@/services/api";
import type { Candidate, ScorecardTemplate } from "@/services/api/recruitment";

const AI_SCORECARD_TOGGLE_KEY = "arbor.ai-scorecards";

type Decision = "proceed" | "reject" | "further_interview";

interface AIScorecard {
  template_id: number | null;
  template_name: string;
  overall_fit: number;
  competency_ratings: Record<string, number>;
  strengths: string[];
  concerns: string[];
  recommended_decision: Decision;
  narrative: string;
  criteria: Array<{ name: string; weight: number }>;
}

/**
 * /recruitment/candidates/[id] — candidate detail page.
 *
 * Hosts the AI scorecard generator (T-R054). The placeholder
 * "Request AI scorecard" CTA is here and is gated by the
 * "AI scorecards (beta)" toggle on the recruitment settings page.
 */
export default function CandidateDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const candidateId = useMemo(() => Number(params?.id), [params?.id]);

  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [aiEnabled, setAiEnabled] = useState(false);
  const [templates, setTemplates] = useState<ScorecardTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | "">("");
  const [scorecard, setScorecard] = useState<AIScorecard | null>(null);
  const [scorecardDegraded, setScorecardDegraded] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Load the localStorage toggle and the candidate + templates.
  useEffect(() => {
    if (typeof window !== "undefined") {
      setAiEnabled(
        window.localStorage.getItem(AI_SCORECARD_TOGGLE_KEY) === "1",
      );
    }
  }, []);

  useEffect(() => {
    if (!Number.isFinite(candidateId) || candidateId <= 0) {
      setError("Invalid candidate ID");
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await recruitmentApi.getCandidate(candidateId);
        if (!cancelled) {
          setCandidate(res);
        }
      } catch (err) {
        console.warn("Failed to load candidate", err);
        if (!cancelled) {
          setError("Could not load candidate.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [candidateId]);

  const loadTemplates = useCallback(async () => {
    try {
      const res = await recruitmentApi.listScorecardTemplates();
      const list = res.templates ?? [];
      setTemplates(list);
      if (list.length > 0 && selectedTemplateId === "") {
        setSelectedTemplateId(list[0].id);
      }
    } catch (err) {
      console.warn("Failed to load scorecard templates", err);
      toast.error("Could not load scorecard templates");
    }
  }, [selectedTemplateId]);

  useEffect(() => {
    if (aiEnabled) {
      void loadTemplates();
    }
  }, [aiEnabled, loadTemplates]);

  const handleGenerate = useCallback(async () => {
    if (!candidate || !selectedTemplateId) {
      toast.error("Pick a scorecard template first.");
      return;
    }
    setGenerating(true);
    setScorecard(null);
    setScorecardDegraded(false);
    try {
      const res = await recruitmentApi.generateAIScorecard(candidate.id, {
        template_id: Number(selectedTemplateId),
      });
      setScorecard(res.scorecard);
      setScorecardDegraded(Boolean(res.degraded));
      if (res.degraded) {
        toast.warning(
          "AI scorecard generated with reduced confidence — please review carefully.",
        );
      } else {
        toast.success("AI scorecard ready");
      }
    } catch (err) {
      console.warn("Failed to generate AI scorecard", err);
      toast.error(
        "AI scorecard generation failed. Please try again or score manually.",
      );
    } finally {
      setGenerating(false);
    }
  }, [candidate, selectedTemplateId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--color-gray-500)]" />
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4">
        <button
          type="button"
          onClick={() => router.push("/recruitment")}
          className="inline-flex items-center gap-2 text-sm text-[var(--color-gray-500)] hover:text-[var(--color-gray-900)]"
        >
          <ArrowLeft className="h-4 w-4" /> Back to recruitment
        </button>
        <div className="mt-6 bg-white border border-[var(--color-gray-200)] rounded-lg p-6">
          <p className="text-sm text-[var(--color-gray-700)]">
            {error ?? "Candidate not found."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-8">
      <button
        type="button"
        onClick={() => router.push("/recruitment")}
        className="inline-flex items-center gap-2 text-sm text-[var(--color-gray-500)] hover:text-[var(--color-gray-900)]"
      >
        <ArrowLeft className="h-4 w-4" /> Back to recruitment
      </button>

      <header className="bg-white border border-[var(--color-gray-200)] rounded-lg p-6">
        <h1 className="text-2xl font-semibold text-[var(--color-gray-900)]">
          {candidate.name}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-gray-500)]">
          {candidate.email} · stage: {candidate.stage}
          {candidate.job_title ? ` · ${candidate.job_title}` : ""}
        </p>
      </header>

      <section className="bg-white border border-[var(--color-gray-200)] rounded-lg p-6">
        <div className="flex items-start gap-4">
          <div className="rounded-md bg-[var(--color-gray-100)] p-2">
            <Sparkles className="h-5 w-5 text-[var(--color-primary)]" />
          </div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              AI Scorecard
            </h2>
            <p className="mt-1 text-sm text-[var(--color-gray-500)]">
              Generate a structured scorecard from the candidate profile, the
              job requirements, the chosen template, and any interview feedback.
              Use it as a starting point — interviewers always make the final
              call.
            </p>

            {!aiEnabled ? (
              <p className="mt-4 inline-flex items-center gap-2 text-sm text-[var(--color-gray-500)] bg-[var(--color-gray-50)] border border-[var(--color-gray-200)] rounded-md px-3 py-2">
                <AlertTriangle className="h-4 w-4" />
                AI scorecards (beta) are disabled. Turn them on in Recruitment
                Settings.
              </p>
            ) : (
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <label
                  htmlFor="ai-template"
                  className="text-sm text-[var(--color-gray-700)]"
                >
                  Template
                </label>
                <select
                  id="ai-template"
                  value={selectedTemplateId === "" ? "" : selectedTemplateId}
                  onChange={(e) =>
                    setSelectedTemplateId(
                      e.target.value === "" ? "" : Number(e.target.value),
                    )
                  }
                  className="text-sm border border-[var(--color-gray-300)] rounded-md px-2 py-1 bg-white"
                  disabled={templates.length === 0 || generating}
                >
                  {templates.length === 0 ? (
                    <option value="">No templates configured</option>
                  ) : (
                    templates.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))
                  )}
                </select>
                <button
                  type="button"
                  onClick={handleGenerate}
                  disabled={
                    generating ||
                    templates.length === 0 ||
                    selectedTemplateId === ""
                  }
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md bg-[var(--color-primary)] text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {generating ? (
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Generating…
                    </span>
                  ) : (
                    "Generate AI Scorecard"
                  )}
                </button>
              </div>
            )}
          </div>
        </div>

        {scorecard ? (
          <div className="mt-6 border-t border-[var(--color-gray-200)] pt-6 space-y-5">
            {scorecardDegraded ? (
              <p className="inline-flex items-center gap-2 text-xs font-medium text-[var(--color-amber-700,#92400e)] bg-[var(--color-amber-50,#fffbeb)] border border-[var(--color-amber-200,#fde68a)] rounded-md px-2 py-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                Reduced confidence — please review carefully.
              </p>
            ) : null}

            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--color-gray-500)]">
                Overall fit
              </p>
              <p className="text-2xl font-semibold text-[var(--color-gray-900)]">
                {scorecard.overall_fit.toFixed(2)} / 5
              </p>
            </div>

            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--color-gray-500)] mb-2">
                Competency ratings
              </p>
              <ul className="space-y-1.5">
                {scorecard.criteria.map((c) => {
                  const rating = scorecard.competency_ratings[c.name] ?? null;
                  return (
                    <li
                      key={c.name}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="text-[var(--color-gray-700)]">
                        {c.name}{" "}
                        <span className="text-[var(--color-gray-400)] text-xs">
                          (weight {(c.weight * 100).toFixed(0)}%)
                        </span>
                      </span>
                      <span className="font-medium text-[var(--color-gray-900)]">
                        {rating === null ? "—" : `${rating} / 5`}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>

            {scorecard.strengths.length > 0 ? (
              <div>
                <p className="text-xs uppercase tracking-wide text-[var(--color-gray-500)] mb-2">
                  Strengths
                </p>
                <ul className="list-disc pl-5 space-y-1 text-sm text-[var(--color-gray-700)]">
                  {scorecard.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {scorecard.concerns.length > 0 ? (
              <div>
                <p className="text-xs uppercase tracking-wide text-[var(--color-gray-500)] mb-2">
                  Concerns
                </p>
                <ul className="list-disc pl-5 space-y-1 text-sm text-[var(--color-gray-700)]">
                  {scorecard.concerns.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--color-gray-500)] mb-1">
                Recommended decision
              </p>
              <p className="text-sm font-medium text-[var(--color-gray-900)] capitalize">
                {scorecard.recommended_decision.replace("_", " ")}
              </p>
            </div>

            {scorecard.narrative ? (
              <div>
                <p className="text-xs uppercase tracking-wide text-[var(--color-gray-500)] mb-1">
                  Summary
                </p>
                <p className="text-sm text-[var(--color-gray-700)]">
                  {scorecard.narrative}
                </p>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}
