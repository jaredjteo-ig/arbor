"use client";

import { useState } from "react";
import { AppButton, AppCard, AppInput } from "@/components/design-system";
import { AlertCircle, Info } from "lucide-react";
import { useSubmitEvaluation } from "@/hooks/api/useQa";
import type {
  CitationFlag,
  CitationFlagStatus,
  QAFailureCategoryValue,
  QAAffectedAgent,
  ProvisionCited,
} from "@/types/api";

/* ── Constants ───────────────────────────────────────────── */

interface RubricDimension {
  key: string;
  label: string;
  hint: string;
}

const RUBRIC_DIMENSIONS: RubricDimension[] = [
  {
    key: "score_legal_accuracy",
    label: "Legal Accuracy",
    hint: "Is the legal information factually correct and up-to-date?",
  },
  {
    key: "score_contextual_relevance",
    label: "Contextual Relevance",
    hint: "Does the response address the user's specific situation?",
  },
  {
    key: "score_coherence",
    label: "Conversational Coherence",
    hint: "Does the response flow logically from the conversation context?",
  },
  {
    key: "score_actionability",
    label: "Actionability",
    hint: "Can the user take concrete steps based on this advice?",
  },
  {
    key: "score_risk_awareness",
    label: "Risk Awareness",
    hint: "Are risks, caveats, and edge cases appropriately flagged?",
  },
  {
    key: "score_citation_quality",
    label: "Citation Quality",
    hint: "Are legal provisions cited correctly and completely?",
  },
  {
    key: "score_language",
    label: "Language Understanding",
    hint: "Does the response correctly interpret the user's intent and language?",
  },
  {
    key: "score_completeness",
    label: "Completeness",
    hint: "Does the response cover all relevant aspects of the question?",
  },
];

const FAILURE_CATEGORIES: { value: QAFailureCategoryValue; label: string }[] = [
  { value: "wrong_law_cited", label: "Wrong law cited" },
  {
    value: "correct_law_wrong_interpretation",
    label: "Correct law, wrong interpretation",
  },
  { value: "missed_critical_nuance", label: "Missed critical nuance" },
  { value: "ignored_company_context", label: "Ignored company context" },
  { value: "lost_conversation_context", label: "Lost conversation context" },
  { value: "overly_generic", label: "Overly generic" },
  { value: "wrong_domain_routing", label: "Wrong domain routing" },
  { value: "fabricated_citation", label: "Fabricated citation" },
  { value: "other", label: "Other" },
];

const AFFECTED_AGENTS: { value: QAAffectedAgent; label: string }[] = [
  { value: "employment_act_specialist", label: "Employment Act Specialist" },
  { value: "cpf_specialist", label: "CPF Specialist" },
  {
    value: "foreign_manpower_specialist",
    label: "Foreign Manpower Specialist",
  },
  { value: "fair_employment_specialist", label: "Fair Employment Specialist" },
  { value: "tax_specialist", label: "Tax Specialist" },
  { value: "wsh_specialist", label: "WSH Specialist" },
  { value: "pdpa_specialist", label: "PDPA Specialist" },
  { value: "query_analyzer", label: "Query Analyzer" },
  { value: "orchestrator", label: "Orchestrator" },
  { value: "response_synthesizer", label: "Response Synthesizer" },
];

const SCORE_VALUES = [1, 2, 3, 4, 5] as const;

/* ── Props ───────────────────────────────────────────────── */

interface EvaluationFormProps {
  sessionId: number;
  conversationId: string;
  turnNumber: number;
  provisions: ProvisionCited[];
  onSubmitted: () => void;
}

/* ── Score radio group ───────────────────────────────────── */

function ScoreRadioGroup({
  dimension,
  value,
  onChange,
}: {
  dimension: RubricDimension;
  value: number;
  onChange: (score: number) => void;
}) {
  const [showHint, setShowHint] = useState(false);

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-2 py-2">
      <div className="flex items-center gap-1.5 sm:w-52 shrink-0">
        <span className="text-sm font-medium text-[var(--color-gray-700)]">
          {dimension.label}
        </span>
        <button
          type="button"
          className="p-0.5 rounded hover:bg-[var(--color-gray-100)] transition-colors"
          onMouseEnter={() => setShowHint(true)}
          onMouseLeave={() => setShowHint(false)}
          onFocus={() => setShowHint(true)}
          onBlur={() => setShowHint(false)}
          aria-label={`Hint: ${dimension.hint}`}
        >
          <Info className="h-3.5 w-3.5 text-[var(--color-gray-400)]" />
        </button>
        {showHint && (
          <span className="text-xs text-[var(--color-gray-500)] italic">
            {dimension.hint}
          </span>
        )}
      </div>
      <div className="flex items-center gap-1">
        {SCORE_VALUES.map((score) => (
          <label
            key={score}
            className={`flex items-center justify-center w-9 h-9 rounded-full border text-sm font-medium cursor-pointer transition-colors ${
              value === score
                ? "bg-[var(--color-primary)] text-white border-[var(--color-primary)]"
                : "bg-[var(--color-surface-card)] text-[var(--color-gray-700)] border-[var(--color-gray-300)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary)]"
            }`}
          >
            <input
              type="radio"
              name={dimension.key}
              value={score}
              checked={value === score}
              onChange={() => onChange(score)}
              className="sr-only"
            />
            {score}
          </label>
        ))}
      </div>
    </div>
  );
}

/* ── Citation flag row ───────────────────────────────────── */

function CitationFlagRow({
  provisionId,
  status,
  onChange,
}: {
  provisionId: string;
  status: CitationFlagStatus;
  onChange: (status: CitationFlagStatus) => void;
}) {
  const statuses: { value: CitationFlagStatus; label: string }[] = [
    { value: "correct", label: "Correct" },
    { value: "incorrect", label: "Incorrect" },
    { value: "missing", label: "Missing" },
  ];

  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="text-sm text-[var(--color-gray-700)] w-32 shrink-0 truncate font-mono">
        {provisionId}
      </span>
      <div className="flex items-center gap-2">
        {statuses.map((s) => (
          <label
            key={s.value}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border cursor-pointer transition-colors ${
              status === s.value
                ? s.value === "correct"
                  ? "bg-[var(--color-risk-green-bg)] text-[var(--color-risk-green)] border-[var(--color-risk-green)]"
                  : s.value === "incorrect"
                    ? "bg-[var(--color-risk-red-bg)] text-[var(--color-risk-red)] border-[var(--color-risk-red)]"
                    : "bg-[var(--color-risk-amber-bg)] text-[var(--color-risk-amber)] border-[var(--color-risk-amber)]"
                : "bg-[var(--color-surface-card)] text-[var(--color-gray-500)] border-[var(--color-gray-300)]"
            }`}
          >
            <input
              type="radio"
              name={`citation-${provisionId}`}
              value={s.value}
              checked={status === s.value}
              onChange={() => onChange(s.value)}
              className="sr-only"
            />
            {s.label}
          </label>
        ))}
      </div>
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────── */

export function EvaluationForm({
  sessionId,
  conversationId,
  turnNumber,
  provisions,
  onSubmitted,
}: EvaluationFormProps) {
  const submitEvaluation = useSubmitEvaluation();

  /* Score state: keyed by dimension key */
  const [scores, setScores] = useState<Record<string, number>>({});

  /* Citation flags */
  const [citationFlags, setCitationFlags] = useState<CitationFlag[]>(
    provisions.map((p) => ({
      provision_id: p.provision_id,
      status: "correct" as CitationFlagStatus,
    })),
  );

  /* Material correction */
  const [hasMaterialCorrection, setHasMaterialCorrection] = useState(false);
  const [correctionText, setCorrectionText] = useState("");
  const [failureCategory, setFailureCategory] = useState<
    QAFailureCategoryValue | ""
  >("");
  const [affectedAgent, setAffectedAgent] = useState<QAAffectedAgent | "">("");

  /* Validation */
  const [validationError, setValidationError] = useState<string | null>(null);

  function updateScore(key: string, value: number) {
    setScores((prev) => ({ ...prev, [key]: value }));
  }

  function updateCitationFlag(provisionId: string, status: CitationFlagStatus) {
    setCitationFlags((prev) =>
      prev.map((f) => (f.provision_id === provisionId ? { ...f, status } : f)),
    );
  }

  function handleSubmit() {
    setValidationError(null);

    /* Validate all 8 scores provided */
    const missingScores = RUBRIC_DIMENSIONS.filter((d) => !scores[d.key]);
    if (missingScores.length > 0) {
      setValidationError(
        `Please rate all dimensions. Missing: ${missingScores.map((d) => d.label).join(", ")}`,
      );
      return;
    }

    /* Validate material correction fields */
    if (hasMaterialCorrection) {
      if (!failureCategory) {
        setValidationError("Please select a failure category.");
        return;
      }
      if (!affectedAgent) {
        setValidationError("Please select the affected agent.");
        return;
      }
    }

    submitEvaluation.mutate(
      {
        session_id: sessionId,
        conversation_id: conversationId,
        turn_number: turnNumber,
        score_legal_accuracy: scores["score_legal_accuracy"],
        score_contextual_relevance: scores["score_contextual_relevance"],
        score_coherence: scores["score_coherence"],
        score_actionability: scores["score_actionability"],
        score_risk_awareness: scores["score_risk_awareness"],
        score_citation_quality: scores["score_citation_quality"],
        score_language: scores["score_language"],
        score_completeness: scores["score_completeness"],
        citation_flags: citationFlags.length > 0 ? citationFlags : null,
        has_material_correction: hasMaterialCorrection,
        correction_text: hasMaterialCorrection ? correctionText || null : null,
        failure_category:
          hasMaterialCorrection && failureCategory
            ? (failureCategory as QAFailureCategoryValue)
            : null,
        affected_agent:
          hasMaterialCorrection && affectedAgent
            ? (affectedAgent as QAAffectedAgent)
            : null,
      },
      {
        onSuccess: () => {
          /* Reset form */
          setScores({});
          setHasMaterialCorrection(false);
          setCorrectionText("");
          setFailureCategory("");
          setAffectedAgent("");
          setValidationError(null);
          setCitationFlags(
            provisions.map((p) => ({
              provision_id: p.provision_id,
              status: "correct" as CitationFlagStatus,
            })),
          );
          onSubmitted();
        },
      },
    );
  }

  return (
    <AppCard
      variant="flat"
      header={
        <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
          Evaluation
        </h4>
      }
    >
      <div className="space-y-5">
        {/* Rubric dimension scores */}
        <div>
          <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider mb-2">
            Score each dimension (1-5)
          </p>
          <div className="divide-y divide-[var(--color-gray-100)]">
            {RUBRIC_DIMENSIONS.map((dim) => (
              <ScoreRadioGroup
                key={dim.key}
                dimension={dim}
                value={scores[dim.key] ?? 0}
                onChange={(score) => updateScore(dim.key, score)}
              />
            ))}
          </div>
        </div>

        {/* Citation flags */}
        {provisions.length > 0 && (
          <div>
            <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider mb-2">
              Citation verification
            </p>
            <div className="space-y-1">
              {citationFlags.map((flag) => (
                <CitationFlagRow
                  key={flag.provision_id}
                  provisionId={flag.provision_id}
                  status={flag.status}
                  onChange={(status) =>
                    updateCitationFlag(flag.provision_id, status)
                  }
                />
              ))}
            </div>
          </div>
        )}

        {/* Material correction toggle */}
        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={hasMaterialCorrection}
              onChange={(e) => setHasMaterialCorrection(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
            />
            <span className="text-sm font-medium text-[var(--color-gray-700)]">
              Material correction needed
            </span>
          </label>

          {hasMaterialCorrection && (
            <div className="space-y-3 pl-7">
              <AppInput
                variant="textarea"
                label="Correction details"
                placeholder="Describe what should have been said differently..."
                value={correctionText}
                onChange={(e) =>
                  setCorrectionText((e.target as HTMLTextAreaElement).value)
                }
              />
              <AppInput
                variant="select"
                label="Failure category (required)"
                value={failureCategory}
                onChange={(e) =>
                  setFailureCategory(
                    (e.target as HTMLSelectElement).value as
                      | QAFailureCategoryValue
                      | "",
                  )
                }
                options={[
                  { value: "", label: "Select category..." },
                  ...FAILURE_CATEGORIES,
                ]}
              />
              <AppInput
                variant="select"
                label="Affected agent (required)"
                value={affectedAgent}
                onChange={(e) =>
                  setAffectedAgent(
                    (e.target as HTMLSelectElement).value as
                      | QAAffectedAgent
                      | "",
                  )
                }
                options={[
                  { value: "", label: "Select agent..." },
                  ...AFFECTED_AGENTS,
                ]}
              />
            </div>
          )}
        </div>

        {/* Validation error */}
        {validationError && (
          <div className="flex items-start gap-2 text-sm text-[var(--color-error)]">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{validationError}</span>
          </div>
        )}

        {/* Submit error */}
        {submitEvaluation.isError && (
          <div className="flex items-start gap-2 text-sm text-[var(--color-error)]">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{submitEvaluation.error.message}</span>
          </div>
        )}

        {/* Submit button */}
        <div className="flex justify-end pt-2">
          <AppButton
            size="sm"
            onClick={handleSubmit}
            loading={submitEvaluation.isPending}
          >
            Submit Evaluation
          </AppButton>
        </div>
      </div>
    </AppCard>
  );
}
