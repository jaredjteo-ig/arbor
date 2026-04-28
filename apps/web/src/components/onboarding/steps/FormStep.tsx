"use client";

/**
 * FormStep — renders dynamic form fields from a JSON form_schema and submits
 * collected values via POST /onboarding/steps/{id}/complete (with form_data
 * in the request body).
 *
 * The form_schema lives on the OnboardingStep record but the my-progress
 * payload exposes it as `body_content` for form-typed steps (the admin
 * builder writes the JSON schema there). We tolerate both shapes:
 *   - body_content as the raw JSON schema string
 *   - body_content as plain instructions, with a `form_schema` field added
 *     in future
 *
 * Supported field types: text, email, tel, number, textarea, select.
 * Each field is { name, label, type, required?, placeholder?, options? }.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { AppButton, toast } from "@/components/design-system";
import { apiClient } from "@/services/api/client";
import {
  type StepProgressWithStep,
  type OnboardingStepProgress,
} from "@/services/api/onboarding";

export interface FormStepProps {
  sp: StepProgressWithStep;
  onStepCompleted: () => void;
}

interface FormField {
  name: string;
  label: string;
  type: "text" | "email" | "tel" | "number" | "textarea" | "select";
  required?: boolean;
  placeholder?: string;
  options?: Array<string | { value: string; label: string }>;
}

interface ParsedSchema {
  title?: string;
  description?: string;
  fields: FormField[];
}

/** Parse the form schema from body_content. Returns an empty schema on error. */
function parseSchema(raw: string): ParsedSchema {
  if (!raw || !raw.trim()) return { fields: [] };
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && Array.isArray(parsed.fields)) {
      return {
        title: typeof parsed.title === "string" ? parsed.title : undefined,
        description:
          typeof parsed.description === "string"
            ? parsed.description
            : undefined,
        fields: parsed.fields.filter(
          (f: unknown): f is FormField =>
            !!f && typeof f === "object" && "name" in f && "label" in f,
        ),
      };
    }
  } catch {
    // Fall through to empty schema
  }
  return { fields: [] };
}

export function FormStep({ sp, onStepCompleted }: FormStepProps) {
  const { t } = useTranslation();
  const isCompleted = sp.status === "completed";
  const schema = useMemo(() => parseSchema(sp.body_content), [sp.body_content]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  function setField(name: string, value: string) {
    setValues((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  }

  function validate(): boolean {
    const next: Record<string, string> = {};
    for (const field of schema.fields) {
      const v = (values[field.name] ?? "").trim();
      if (field.required && !v) {
        next[field.name] = t("onboarding.step.form.required", {
          defaultValue: "This field is required",
        });
      }
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      // POST /onboarding/steps/{progress_id}/complete accepts form_data in the
      // body. apiClient.post serializes the second arg as JSON.
      await apiClient.post<{
        message: string;
        progress: OnboardingStepProgress;
      }>(`/onboarding/steps/${sp.id}/complete`, {
        form_data: JSON.stringify(values),
      });
      toast.success(
        t("onboarding.step.form.submitted", {
          defaultValue: "Form submitted",
        }),
      );
      onStepCompleted();
    } catch {
      toast.error(
        t("onboarding.step.form.failed", {
          defaultValue: "Failed to submit form. Please try again.",
        }),
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (isCompleted) {
    return (
      <div className="mt-2 text-sm text-[var(--color-gray-500)]">
        {t("onboarding.step.form.already_submitted", {
          defaultValue: "Form already submitted.",
        })}
      </div>
    );
  }

  if (schema.fields.length === 0) {
    return (
      <div className="mt-2 text-sm italic text-[var(--color-gray-500)]">
        {t("onboarding.step.form.no_fields", {
          defaultValue: "No form fields defined for this step.",
        })}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mt-2 space-y-3">
      {schema.description && (
        <p className="text-sm text-[var(--color-gray-600)]">
          {schema.description}
        </p>
      )}

      {schema.fields.map((field) => (
        <div key={field.name}>
          <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-1">
            {field.label}
            {field.required && (
              <span className="text-red-500 ml-1" aria-hidden="true">
                *
              </span>
            )}
          </label>
          {field.type === "textarea" ? (
            <textarea
              value={values[field.name] ?? ""}
              onChange={(e) => setField(field.name, e.target.value)}
              placeholder={field.placeholder ?? ""}
              required={field.required}
              rows={3}
              className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] placeholder:text-[var(--color-gray-400)] resize-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            />
          ) : field.type === "select" ? (
            <select
              value={values[field.name] ?? ""}
              onChange={(e) => setField(field.name, e.target.value)}
              required={field.required}
              className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            >
              <option value="">
                {t("onboarding.step.form.select_placeholder", {
                  defaultValue: "Select…",
                })}
              </option>
              {(field.options ?? []).map((opt) => {
                const value = typeof opt === "string" ? opt : opt.value;
                const label = typeof opt === "string" ? opt : opt.label;
                return (
                  <option key={value} value={value}>
                    {label}
                  </option>
                );
              })}
            </select>
          ) : (
            <input
              type={field.type}
              value={values[field.name] ?? ""}
              onChange={(e) => setField(field.name, e.target.value)}
              placeholder={field.placeholder ?? ""}
              required={field.required}
              className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] placeholder:text-[var(--color-gray-400)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            />
          )}
          {errors[field.name] && (
            <p className="text-xs text-[var(--color-error)] mt-1">
              {errors[field.name]}
            </p>
          )}
        </div>
      ))}

      <AppButton
        variant="primary"
        size="sm"
        type="submit"
        loading={submitting}
        disabled={submitting}
      >
        {t("onboarding.step.form.submit", { defaultValue: "Submit" })}
      </AppButton>
    </form>
  );
}

export default FormStep;
