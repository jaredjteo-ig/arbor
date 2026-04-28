"use client";

/**
 * ChecklistStep — renders checklist_items as toggle-able checkboxes.
 *
 * The step is considered complete only when the user has checked every item
 * AND clicked the Complete button (which calls completeStep).
 *
 * checklist_items may arrive as JSON (array of {id, label, checked}) or as
 * newline-separated text — we accept both via parseChecklistItems().
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AppButton, toast } from "@/components/design-system";
import {
  onboardingApi,
  type StepProgressWithStep,
} from "@/services/api/onboarding";

export interface ChecklistStepProps {
  sp: StepProgressWithStep;
  onStepCompleted: () => void;
}

interface ParsedChecklistItem {
  id: string;
  label: string;
  checked: boolean;
}

export function parseChecklistItems(raw: string): ParsedChecklistItem[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed.map((item, idx) => ({
        id: item.id ?? String(idx),
        label: item.label ?? item.text ?? String(item),
        checked: !!item.checked,
      }));
    }
  } catch {
    // If not valid JSON, treat as newline-separated text
    return raw
      .split("\n")
      .filter((line) => line.trim())
      .map((line, idx) => ({
        id: String(idx),
        label: line.trim(),
        checked: false,
      }));
  }
  return [];
}

export function ChecklistStep({ sp, onStepCompleted }: ChecklistStepProps) {
  const { t } = useTranslation();
  const [items, setItems] = useState<ParsedChecklistItem[]>(() =>
    parseChecklistItems(sp.checklist_items),
  );
  const [submitting, setSubmitting] = useState(false);
  const isCompleted = sp.status === "completed";

  function toggleItem(id: string) {
    if (isCompleted) return;
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, checked: !item.checked } : item,
      ),
    );
  }

  const allChecked = items.length > 0 && items.every((item) => item.checked);

  async function handleComplete() {
    setSubmitting(true);
    try {
      await onboardingApi.completeStep(sp.id);
      toast.success(
        t("onboarding.step.checklist.completed", {
          defaultValue: "Checklist completed",
        }),
      );
      onStepCompleted();
    } catch {
      toast.error(
        t("onboarding.step.checklist.failed", {
          defaultValue: "Failed to complete checklist. Please try again.",
        }),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-2 space-y-2">
      <div className="space-y-1.5">
        {items.map((item) => (
          <label
            key={item.id}
            className="flex items-center gap-2 text-sm cursor-pointer"
          >
            <input
              type="checkbox"
              checked={isCompleted || item.checked}
              disabled={isCompleted}
              onChange={() => toggleItem(item.id)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
            />
            <span
              className={
                isCompleted || item.checked
                  ? "text-[var(--color-gray-500)] line-through"
                  : "text-[var(--color-gray-700)]"
              }
            >
              {item.label}
            </span>
          </label>
        ))}
      </div>
      {!isCompleted && (
        <AppButton
          variant="primary"
          size="sm"
          onClick={handleComplete}
          disabled={!allChecked}
          loading={submitting}
        >
          {t("onboarding.step.checklist.complete", {
            defaultValue: "Complete",
          })}
        </AppButton>
      )}
    </div>
  );
}

export default ChecklistStep;
