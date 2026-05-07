"use client";

/**
 * /my-engagement-surveys/[response_id]/respond — in-app form (M5 T51).
 *
 * Round-3: in-app only at v1 (no public tokenised route).
 * Anonymity badge with revised Z41 copy.
 * Disabled-with-help-text submit gating (P43).
 */

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, ChevronLeft, Loader2, ShieldAlert } from "lucide-react";
import {
  engagementApi,
  parseSections,
  describeAnonymityTier,
  type RenderResponse,
  type SurveySection,
  type SurveyQuestion,
  type AnonymityTier,
} from "@/services/api/engagement";
import { Likert5, EnpsScale, ChipMultiSelect } from "@/components/surveys";

interface FormState {
  [questionId: string]: number | string | string[];
}

export default function RespondPage() {
  const router = useRouter();
  const { response_id } = useParams<{ response_id: string }>();
  const responseId = Number(response_id);

  const [render, setRender] = useState<RenderResponse | null>(null);
  const [sections, setSections] = useState<SurveySection[]>([]);
  const [form, setForm] = useState<FormState>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(responseId) || responseId <= 0) {
      setRenderError("Invalid response link.");
      return;
    }
    (async () => {
      try {
        const r = await engagementApi.renderMyResponse(responseId);
        setRender(r);
        setSections(parseSections(r.template_sections_snapshot));
      } catch (err) {
        const msg = (err as Error).message || "Could not load this survey";
        setRenderError(msg);
      }
    })();
  }, [responseId]);

  const allQuestions: SurveyQuestion[] = sections.flatMap(
    (s) => s.questions ?? [],
  );
  const requiredQuestions = allQuestions.filter((q) => q.is_required);
  const missingRequired = requiredQuestions.filter((q) => {
    const v = form[q.id];
    if (q.type === "multi") return !Array.isArray(v) || v.length === 0;
    if (q.type === "short_text" || q.type === "long_text") {
      return typeof v !== "string" || !v.trim();
    }
    return v === undefined || v === null;
  });

  function setValue(qid: string, value: number | string | string[]) {
    setForm((prev) => ({ ...prev, [qid]: value }));
  }

  function toggleMulti(qid: string, option: string) {
    setForm((prev) => {
      const current = (prev[qid] as string[] | undefined) ?? [];
      const next = current.includes(option)
        ? current.filter((x) => x !== option)
        : [...current, option];
      return { ...prev, [qid]: next };
    });
  }

  async function submit() {
    if (missingRequired.length > 0 || !render) return;
    setSubmitting(true);
    setError(null);
    try {
      await engagementApi.submitMyResponse(responseId, form);
      setSubmitted(true);
    } catch (err) {
      setError((err as Error).message || "Submit failed");
    } finally {
      setSubmitting(false);
    }
  }

  /* ── Empty / error states ──────────────────────────────────── */

  if (renderError) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <ShieldAlert className="h-12 w-12 text-[var(--color-gray-400)] mx-auto mb-4" />
        <h1 className="text-xl font-semibold text-[var(--color-gray-900)] mb-2">
          Can&apos;t open this survey
        </h1>
        <p className="text-sm text-[var(--color-gray-500)] mb-6">
          {renderError}
        </p>
        <Link
          href="/my-engagement-surveys"
          className="text-sm text-rose-600 hover:underline"
        >
          Back to My Engagement
        </Link>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-4" />
        <h1 className="text-xl font-semibold text-[var(--color-gray-900)] mb-2">
          Thank you
        </h1>
        <p className="text-sm text-[var(--color-gray-500)] mb-6">
          Your response has been recorded. HR sees aggregated trends — never
          individual responses for pseudonymous or anonymous surveys.
        </p>
        <Link
          href="/my-engagement-surveys"
          className="inline-block px-4 py-2 text-sm rounded-md bg-rose-600 hover:bg-rose-700 text-white"
        >
          Back to My Engagement
        </Link>
      </div>
    );
  }

  if (!render) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12 text-center text-[var(--color-gray-400)]">
        <Loader2 className="h-5 w-5 animate-spin inline mr-2" />
        Loading…
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6">
      <Link
        href="/my-engagement-surveys"
        className="inline-flex items-center text-sm text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] mb-3"
      >
        <ChevronLeft className="h-4 w-4 mr-1" />
        Back
      </Link>

      <h1 className="text-2xl font-semibold text-[var(--color-gray-900)] mb-2">
        {render.survey_name}
      </h1>

      {/* Anonymity badge — Z41 revised copy */}
      <AnonymityBadge tier={render.anonymity_tier} />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="space-y-8 mt-6"
      >
        {sections.map((section, sIdx) => (
          <section
            key={sIdx}
            className="bg-white rounded-xl border border-[var(--color-gray-200)] p-5 space-y-5"
          >
            {section.title && (
              <h2 className="font-semibold text-[var(--color-gray-900)]">
                {section.title}
              </h2>
            )}
            {section.questions.map((q) => (
              <QuestionRenderer
                key={q.id}
                question={q}
                value={form[q.id]}
                onChange={(v) => setValue(q.id, v)}
                onToggleMulti={(option) => toggleMulti(q.id, option)}
              />
            ))}
          </section>
        ))}

        {error && (
          <div className="rounded-md bg-red-50 text-red-700 text-sm p-3">
            {error}
          </div>
        )}

        <div className="sticky bottom-0 bg-white border-t border-[var(--color-gray-200)] py-3 mt-6 -mx-4 px-4">
          {missingRequired.length > 0 && (
            <p className="text-xs text-[var(--color-gray-500)] mb-2">
              {missingRequired.length} more question
              {missingRequired.length === 1 ? "" : "s"} to answer.
            </p>
          )}
          <button
            type="submit"
            disabled={submitting || missingRequired.length > 0}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-md bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Submit response
          </button>
        </div>
      </form>
    </div>
  );
}

function AnonymityBadge({ tier }: { tier: AnonymityTier }) {
  const colourCls =
    tier === "identified"
      ? "bg-amber-50 border-amber-200 text-amber-900"
      : tier === "pseudonymous"
        ? "bg-blue-50 border-blue-200 text-blue-900"
        : "bg-green-50 border-green-200 text-green-900";
  const label =
    tier === "identified"
      ? "Names visible"
      : tier === "pseudonymous"
        ? "Pseudonymous"
        : "Anonymous";
  return (
    <div role="note" className={`rounded-md border p-3 text-sm ${colourCls}`}>
      <span className="font-semibold">{label}.</span>{" "}
      <span>{describeAnonymityTier(tier)}</span>
    </div>
  );
}

function QuestionRenderer({
  question,
  value,
  onChange,
  onToggleMulti,
}: {
  question: SurveyQuestion;
  value: number | string | string[] | undefined;
  onChange: (v: number | string | string[]) => void;
  onToggleMulti: (option: string) => void;
}) {
  switch (question.type) {
    case "likert5":
      return (
        <Likert5
          value={typeof value === "number" ? value : null}
          onChange={(v) => onChange(v)}
          label={question.text}
          required={question.is_required}
          questionId={question.id}
        />
      );
    case "enps":
      return (
        <EnpsScale
          value={typeof value === "number" ? value : null}
          onChange={(v) => onChange(v)}
          label={question.text}
          required={question.is_required}
          questionId={question.id}
        />
      );
    case "multi":
      return (
        <ChipMultiSelect
          options={(question.options ?? []).map((o) => ({
            value: o,
            label: o,
          }))}
          selected={Array.isArray(value) ? value : []}
          onToggle={onToggleMulti}
          label={question.text}
          questionId={question.id}
        />
      );
    case "single":
      return (
        <fieldset>
          <legend className="text-sm font-medium text-[var(--color-gray-900)] mb-2">
            {question.text}
            {question.is_required && (
              <span className="text-[var(--color-error)] ml-1">*</span>
            )}
          </legend>
          <div className="space-y-2">
            {(question.options ?? []).map((opt) => (
              <label
                key={opt}
                className="flex items-center gap-2 cursor-pointer"
              >
                <input
                  type="radio"
                  name={question.id}
                  value={opt}
                  checked={value === opt}
                  onChange={() => onChange(opt)}
                />
                <span className="text-sm">{opt}</span>
              </label>
            ))}
          </div>
        </fieldset>
      );
    case "short_text":
      return (
        <div>
          <label
            htmlFor={`q-${question.id}`}
            className="block text-sm font-medium text-[var(--color-gray-900)] mb-2"
          >
            {question.text}
            {question.is_required && (
              <span className="text-[var(--color-error)] ml-1">*</span>
            )}
          </label>
          <input
            id={`q-${question.id}`}
            type="text"
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
            maxLength={question.max_length ?? 200}
            className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 text-sm"
          />
        </div>
      );
    case "long_text":
      return (
        <div>
          <label
            htmlFor={`q-${question.id}`}
            className="block text-sm font-medium text-[var(--color-gray-900)] mb-2"
          >
            {question.text}
            {question.is_required && (
              <span className="text-[var(--color-error)] ml-1">*</span>
            )}
          </label>
          <textarea
            id={`q-${question.id}`}
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
            maxLength={question.max_length ?? 2000}
            rows={4}
            className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 text-sm"
          />
        </div>
      );
    default:
      return null;
  }
}
