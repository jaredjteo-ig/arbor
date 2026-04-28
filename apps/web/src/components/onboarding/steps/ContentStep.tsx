"use client";

/**
 * ContentStep — renders body_content as formatted text + "Mark as read" button.
 *
 * The body_content from OnboardingStep is treated as plain text with newlines
 * preserved. We deliberately avoid `dangerouslySetInnerHTML` since the content
 * is admin-authored and may contain unsafe HTML — `whitespace-pre-wrap` gives
 * us paragraph breaks safely.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { BookOpen } from "lucide-react";
import { AppButton, toast } from "@/components/design-system";
import {
  onboardingApi,
  type StepProgressWithStep,
} from "@/services/api/onboarding";

export interface ContentStepProps {
  sp: StepProgressWithStep;
  onStepCompleted: () => void;
}

export function ContentStep({ sp, onStepCompleted }: ContentStepProps) {
  const { t } = useTranslation();
  const [showContent, setShowContent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const isCompleted = sp.status === "completed";
  const hasContent = !!(sp.body_content && sp.body_content.trim());

  async function handleMarkRead() {
    setSubmitting(true);
    try {
      await onboardingApi.completeStep(sp.id);
      toast.success(
        t("onboarding.step.content.marked_read", {
          defaultValue: "Step marked as read",
        }),
      );
      onStepCompleted();
    } catch {
      toast.error(
        t("onboarding.step.content.mark_failed", {
          defaultValue: "Failed to mark as read. Please try again.",
        }),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-2 space-y-2">
      {!showContent && !isCompleted && (
        <AppButton
          variant="outlined"
          size="sm"
          onClick={() => setShowContent(true)}
        >
          <BookOpen className="h-4 w-4 mr-1" />
          {t("onboarding.step.content.read", { defaultValue: "Read" })}
        </AppButton>
      )}
      {(showContent || isCompleted) && (
        <div className="rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-gray-50)] p-4 text-sm text-[var(--color-gray-700)] whitespace-pre-wrap">
          {hasContent ? (
            sp.body_content
          ) : (
            <span className="italic text-[var(--color-gray-500)]">
              {t("onboarding.step.content.empty", {
                defaultValue: "No content provided.",
              })}
            </span>
          )}
        </div>
      )}
      {showContent && !isCompleted && (
        <AppButton
          variant="primary"
          size="sm"
          onClick={handleMarkRead}
          loading={submitting}
        >
          {t("onboarding.step.content.mark_as_read", {
            defaultValue: "Mark as Read",
          })}
        </AppButton>
      )}
    </div>
  );
}

export default ContentStep;
