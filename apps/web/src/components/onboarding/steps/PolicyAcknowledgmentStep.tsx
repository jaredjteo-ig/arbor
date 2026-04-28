"use client";

/**
 * PolicyAcknowledgmentStep — fetch the linked CompanyPolicy, display its
 * title/summary, and call POST /onboarding/steps/{id}/acknowledge once the
 * employee ticks the "I acknowledge" checkbox.
 *
 * The full policy body opens in a new tab so the employee doesn't lose their
 * place in the onboarding flow.
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { CheckCircle2, FileText } from "lucide-react";
import { AppButton, toast } from "@/components/design-system";
import {
  onboardingApi,
  type StepProgressWithStep,
} from "@/services/api/onboarding";
import { policiesApi, type PolicyRecord } from "@/services/api/policies";

export interface PolicyAcknowledgmentStepProps {
  sp: StepProgressWithStep;
  onStepCompleted: () => void;
}

export function PolicyAcknowledgmentStep({
  sp,
  onStepCompleted,
}: PolicyAcknowledgmentStepProps) {
  const { t } = useTranslation();
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [policy, setPolicy] = useState<PolicyRecord | null>(null);
  const [policyLoadFailed, setPolicyLoadFailed] = useState(false);
  const isCompleted = sp.status === "completed";
  const policyId = sp.policy_id ?? null;

  useEffect(() => {
    let cancelled = false;
    async function loadPolicy() {
      if (!policyId) return;
      try {
        const result = await policiesApi.get(policyId);
        if (!cancelled) setPolicy(result);
      } catch {
        if (!cancelled) setPolicyLoadFailed(true);
      }
    }
    loadPolicy();
    return () => {
      cancelled = true;
    };
  }, [policyId]);

  async function handleAcknowledge() {
    setSubmitting(true);
    try {
      await onboardingApi.acknowledgeStep(sp.id);
      toast.success(
        t("onboarding.step.policy.acknowledged", {
          defaultValue: "Policy acknowledged",
        }),
      );
      onStepCompleted();
    } catch {
      toast.error(
        t("onboarding.step.policy.failed", {
          defaultValue: "Failed to acknowledge policy. Please try again.",
        }),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-2 space-y-3">
      {/* Policy preview */}
      {policy && (
        <div className="rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-gray-50)] p-3">
          <div className="flex items-start gap-2">
            <FileText className="h-4 w-4 text-[var(--color-primary)] mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[var(--color-gray-900)]">
                {policy.title}
              </p>
              {policy.category && (
                <p className="text-xs text-[var(--color-gray-600)] mt-1 capitalize">
                  {policy.category.replace(/_/g, " ")}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {policyId && (policy || policyLoadFailed) && (
        <a
          href={`/policies/${policyId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm text-[var(--color-primary)] hover:underline"
        >
          <FileText className="h-3.5 w-3.5" />
          {t("onboarding.step.policy.read_full", {
            defaultValue: "Read full policy",
          })}
        </a>
      )}

      {isCompleted ? (
        <div className="flex items-center gap-2 text-sm text-emerald-600">
          <CheckCircle2 className="h-4 w-4" />
          <span>
            {t("onboarding.step.policy.acknowledged_label", {
              defaultValue: "Acknowledged",
            })}
          </span>
        </div>
      ) : (
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
            />
            <span className="text-[var(--color-gray-700)]">
              {t("onboarding.step.policy.checkbox_label", {
                defaultValue:
                  "I acknowledge that I have read and understood this policy",
              })}
            </span>
          </label>
          <AppButton
            variant="primary"
            size="sm"
            onClick={handleAcknowledge}
            disabled={!acknowledged}
            loading={submitting}
          >
            {t("onboarding.step.policy.submit", {
              defaultValue: "Submit Acknowledgment",
            })}
          </AppButton>
        </div>
      )}
    </div>
  );
}

export default PolicyAcknowledgmentStep;
