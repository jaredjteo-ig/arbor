"use client";

/**
 * Launch wizard — three-step modal (T45).
 * 1. Pick template
 * 2. Pick cohort (saved or build inline)
 * 3. Configure (anonymity, name, closes_at)
 */

import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import {
  engagementApi,
  type EngagementTemplate,
  type EngagementCohortRow,
  type CohortFilterSpec,
  type AnonymityTier,
  type Methodology,
  type CohortPreviewResponse,
  describeAnonymityTier,
} from "@/services/api/engagement";

interface LaunchWizardProps {
  templates: EngagementTemplate[];
  cohorts: EngagementCohortRow[];
  onClose: () => void;
  onLaunched: (surveyId: number) => void;
}

type Step = 1 | 2 | 3;

const DEFAULT_TIER_BY_METHODOLOGY: Record<Methodology, AnonymityTier> = {
  pulse: "pseudonymous",
  gallup_q12: "identified",
  trust_index: "identified",
  enps: "pseudonymous",
  custom: "identified",
};

export function LaunchWizard({
  templates,
  cohorts,
  onClose,
  onLaunched,
}: LaunchWizardProps) {
  const [step, setStep] = useState<Step>(1);
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [cohortId, setCohortId] = useState<number | null>(null);
  const [adHocSpec, setAdHocSpec] = useState<CohortFilterSpec>({
    all_active: true,
  });
  const [useSavedCohort, setUseSavedCohort] = useState(true);

  const [name, setName] = useState("");
  const [anonymityTier, setAnonymityTier] =
    useState<AnonymityTier>("identified");
  const [closesAt, setClosesAt] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() + 14);
    return d.toISOString().slice(0, 16);
  });
  const [preview, setPreview] = useState<CohortPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overlapWarnings, setOverlapWarnings] = useState<unknown[]>([]);
  const [forceOverlap, setForceOverlap] = useState(false);
  const [forceAnonymity, setForceAnonymity] = useState(false);

  const selectedTemplate = templates.find((t) => t.id === templateId);

  /* Auto-suggest anonymity + default name when template chosen */
  useEffect(() => {
    if (selectedTemplate) {
      setAnonymityTier(
        DEFAULT_TIER_BY_METHODOLOGY[selectedTemplate.methodology] ??
          "identified",
      );
      const today = new Date().toISOString().slice(0, 10);
      setName(`${selectedTemplate.name} — ${today}`);
    }
  }, [selectedTemplate]);

  /* Refresh preview when cohort selection changes */
  useEffect(() => {
    if (step !== 3) return;
    refreshPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, cohortId, useSavedCohort, anonymityTier]);

  async function refreshPreview() {
    setPreviewLoading(true);
    try {
      const filter_spec = useSavedCohort
        ? cohorts.find((c) => c.id === cohortId)?.filter_spec
          ? JSON.parse(
              cohorts.find((c) => c.id === cohortId)!.filter_spec || "{}",
            )
          : { all_active: true }
        : adHocSpec;
      const r = await engagementApi.previewCohort({
        filter_spec,
        anonymity_tier: anonymityTier,
      });
      setPreview(r);
    } catch (err) {
      console.error("Preview failed", err);
    } finally {
      setPreviewLoading(false);
    }
  }

  async function launch() {
    if (!templateId || !name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const closesIso = new Date(closesAt).toISOString();
      const filter_spec = useSavedCohort ? undefined : adHocSpec;
      const result = await engagementApi.launchSurvey({
        template_id: templateId,
        cohort_id: useSavedCohort ? (cohortId ?? 0) : 0,
        cohort_filter_spec: filter_spec,
        name: name.trim(),
        anonymity_tier: anonymityTier,
        closes_at: closesIso,
        force_overlap_acknowledged: forceOverlap,
        force_anonymity_acknowledged: forceAnonymity,
      });
      if (result.ok === false) {
        setOverlapWarnings(result.warnings || []);
        setError(
          "These employees already have an open survey. Acknowledge below to launch anyway.",
        );
        return;
      }
      onLaunched(result.survey_id);
    } catch (err) {
      setError((err as Error).message || "Launch failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-[var(--color-gray-200)] px-6 py-4">
          <h2 className="text-lg font-semibold">Launch survey</h2>
          <button onClick={onClose} aria-label="Close">
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>

        {/* Stepper */}
        <div className="px-6 pt-4 pb-2 flex items-center gap-2">
          {([1, 2, 3] as const).map((s) => (
            <div
              key={s}
              className={`flex-1 h-1 rounded-full ${step >= s ? "bg-rose-500" : "bg-[var(--color-gray-200)]"}`}
            />
          ))}
        </div>
        <div className="px-6 pb-2 text-xs text-[var(--color-gray-500)]">
          Step {step} of 3 ·{" "}
          {step === 1
            ? "Pick template"
            : step === 2
              ? "Pick cohort"
              : "Configure"}
        </div>

        <div className="px-6 py-4">
          {step === 1 && (
            <div className="space-y-2 max-h-[60vh] overflow-y-auto">
              {templates.map((t) => (
                <label
                  key={t.id}
                  className={`
                    block rounded-lg border-2 p-3 cursor-pointer transition-colors
                    ${
                      templateId === t.id
                        ? "border-rose-500 bg-rose-50"
                        : "border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
                    }
                  `}
                >
                  <input
                    type="radio"
                    name="template"
                    checked={templateId === t.id}
                    onChange={() => setTemplateId(t.id)}
                    className="sr-only"
                  />
                  <div className="font-medium">{t.name}</div>
                  {t.description && (
                    <div className="text-xs text-[var(--color-gray-500)] mt-1">
                      {t.description}
                    </div>
                  )}
                </label>
              ))}
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="flex gap-2">
                <button
                  onClick={() => setUseSavedCohort(true)}
                  className={`flex-1 py-2 text-sm rounded-md border ${useSavedCohort ? "border-rose-500 bg-rose-50 text-rose-700" : "border-[var(--color-gray-200)]"}`}
                >
                  Use saved cohort
                </button>
                <button
                  onClick={() => setUseSavedCohort(false)}
                  className={`flex-1 py-2 text-sm rounded-md border ${!useSavedCohort ? "border-rose-500 bg-rose-50 text-rose-700" : "border-[var(--color-gray-200)]"}`}
                >
                  Build inline (preset)
                </button>
              </div>

              {useSavedCohort ? (
                cohorts.length === 0 ? (
                  <div className="text-sm text-[var(--color-gray-500)] text-center py-6">
                    No saved cohorts yet. Switch to <em>Build inline</em>.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[40vh] overflow-y-auto">
                    {cohorts.map((c) => (
                      <label
                        key={c.id}
                        className={`block rounded-lg border-2 p-3 cursor-pointer ${cohortId === c.id ? "border-rose-500 bg-rose-50" : "border-[var(--color-gray-200)]"}`}
                      >
                        <input
                          type="radio"
                          name="cohort"
                          checked={cohortId === c.id}
                          onChange={() => setCohortId(c.id)}
                          className="sr-only"
                        />
                        <div className="font-medium">{c.name}</div>
                      </label>
                    ))}
                  </div>
                )
              ) : (
                <fieldset>
                  <legend className="text-sm font-medium mb-2">
                    Quick preset
                  </legend>
                  {(
                    [
                      {
                        spec: { all_active: true },
                        label: "All active staff",
                      },
                      {
                        spec: { tenure_max_days: 90 },
                        label: "New joiners (under 90 days)",
                      },
                    ] as const
                  ).map(({ spec, label }) => (
                    <label
                      key={label}
                      className="flex items-center gap-2 mb-2 cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="adhoc"
                        checked={
                          JSON.stringify(adHocSpec) === JSON.stringify(spec)
                        }
                        onChange={() => setAdHocSpec(spec as CohortFilterSpec)}
                      />
                      <span className="text-sm">{label}</span>
                    </label>
                  ))}
                </fieldset>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Survey name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 text-sm"
                />
              </div>

              <fieldset>
                <legend className="text-sm font-medium mb-2">
                  Anonymity tier
                </legend>
                {(["identified", "pseudonymous", "anonymous"] as const).map(
                  (t) => (
                    <label
                      key={t}
                      className="flex items-start gap-2 mb-2 cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="tier"
                        checked={anonymityTier === t}
                        onChange={() => setAnonymityTier(t)}
                        className="mt-1"
                      />
                      <span className="text-sm">
                        <span className="font-medium capitalize">{t}</span>
                        <span className="text-[var(--color-gray-500)] ml-2">
                          {describeAnonymityTier(t)}
                        </span>
                      </span>
                    </label>
                  ),
                )}
              </fieldset>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Closes at
                </label>
                <input
                  type="datetime-local"
                  value={closesAt}
                  onChange={(e) => setClosesAt(e.target.value)}
                  className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 text-sm"
                />
              </div>

              {previewLoading ? (
                <div className="text-sm text-[var(--color-gray-500)]">
                  <Loader2 className="inline h-4 w-4 animate-spin mr-1" />
                  Previewing cohort…
                </div>
              ) : preview ? (
                <div className="rounded-md bg-[var(--color-gray-50)] p-3 text-sm">
                  <div className="font-medium">
                    {preview.matched_count} employees will receive this
                  </div>
                  {preview.warnings.map((w, i) => (
                    <div
                      key={i}
                      className={`text-xs mt-2 ${w.kind === "anonymity_unsafe" ? "text-red-600" : "text-amber-600"}`}
                    >
                      ⚠ {w.message}
                    </div>
                  ))}
                </div>
              ) : null}

              {overlapWarnings.length > 0 && (
                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={forceOverlap}
                    onChange={(e) => setForceOverlap(e.target.checked)}
                    className="mt-1"
                  />
                  <span>
                    I acknowledge these employees already have an open survey
                    and want to launch anyway.
                  </span>
                </label>
              )}

              {preview && !preview.anonymity_safe && (
                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={forceAnonymity}
                    onChange={(e) => setForceAnonymity(e.target.checked)}
                    className="mt-1"
                  />
                  <span>
                    I acknowledge the cohort is too small for full anonymity
                    protection (n &lt; 5).
                  </span>
                </label>
              )}

              {error && (
                <div className="rounded-md bg-red-50 text-red-700 text-sm p-2">
                  {error}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-between border-t border-[var(--color-gray-200)] px-6 py-4">
          <button
            onClick={() =>
              step === 1 ? onClose() : setStep((s) => (s - 1) as Step)
            }
            className="px-4 py-2 text-sm rounded-md border border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
          >
            {step === 1 ? "Cancel" : "Back"}
          </button>
          {step < 3 ? (
            <button
              onClick={() => setStep((s) => (s + 1) as Step)}
              disabled={
                (step === 1 && !templateId) ||
                (step === 2 && useSavedCohort && !cohortId)
              }
              className="px-4 py-2 text-sm rounded-md bg-rose-600 hover:bg-rose-700 text-white disabled:opacity-50"
            >
              Next
            </button>
          ) : (
            <button
              onClick={launch}
              disabled={submitting || !name.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-md bg-rose-600 hover:bg-rose-700 text-white disabled:opacity-50"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Launch survey
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
