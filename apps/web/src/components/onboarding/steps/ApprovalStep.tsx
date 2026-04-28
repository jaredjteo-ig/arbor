"use client";

/**
 * ApprovalStep — read-only view shown to the employee while a step waits for
 * an HR/manager approval. The approver name (when known) and the completion
 * date (once approved) are surfaced; no action is exposed to the employee.
 */

import { useTranslation } from "react-i18next";
import { CheckCircle2, Clock } from "lucide-react";
import { type StepProgressWithStep } from "@/services/api/onboarding";

export interface ApprovalStepProps {
  sp: StepProgressWithStep;
  /** Optional human-readable approver name, surfaced when the backend
   *  attaches it to the step record. Defaults to "HR". */
  approverName?: string;
}

function formatDate(value: string | null): string {
  if (!value) return "";
  try {
    return new Date(value).toLocaleDateString("en-SG", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

export function ApprovalStep({ sp, approverName }: ApprovalStepProps) {
  const { t } = useTranslation();
  const isCompleted = sp.status === "completed";
  const approver =
    approverName ??
    t("onboarding.step.approval.default_approver", { defaultValue: "HR" });

  return (
    <div className="mt-2">
      {isCompleted ? (
        <div className="flex items-center gap-2 text-sm text-emerald-600">
          <CheckCircle2 className="h-4 w-4" />
          <span>
            {t("onboarding.step.approval.approved", {
              defaultValue: "Approved",
            })}
            {sp.completed_at ? ` ${formatDate(sp.completed_at)}` : ""}
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm text-[var(--color-gray-500)]">
          <Clock className="h-4 w-4" />
          <span>
            {t("onboarding.step.approval.awaiting", {
              defaultValue: "Awaiting approval from {{approver}}",
              approver,
            })}
          </span>
        </div>
      )}
    </div>
  );
}

export default ApprovalStep;
