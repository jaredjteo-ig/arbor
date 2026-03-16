"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { X } from "lucide-react";
import { AppButton, AppInput, toast } from "@/components/design-system";
import { useAdvisoryEscalation } from "@/hooks/api/useEmergency";
import type { EscalationUrgency, EscalationContactMethod } from "@/types/api";

/* ── Constants ───────────────────────────────────────────────── */

const URGENCY_OPTIONS: { value: EscalationUrgency; label: string }[] = [
  { value: "urgent", label: "Urgent -- need help now" },
  { value: "within-24h", label: "Within 24 hours" },
  { value: "general-enquiry", label: "General enquiry" },
];

const CONTACT_METHOD_OPTIONS: {
  value: EscalationContactMethod;
  label: string;
}[] = [
  { value: "email", label: "Email" },
  { value: "phone", label: "Phone" },
];

const URGENCY_TIMEFRAMES: Record<EscalationUrgency, string> = {
  urgent: "2 business hours",
  "within-24h": "24 hours",
  "general-enquiry": "3 business days",
};

const SITUATION_MIN_LENGTH = 20;

/* ── Props ───────────────────────────────────────────────────── */

export interface EscalationDialogProps {
  open: boolean;
  onClose: () => void;
  /** Pre-filled situation text (e.g. from the advisory message). */
  defaultSituation?: string;
  /** Default urgency level. */
  defaultUrgency?: EscalationUrgency;
}

/* ── Component ───────────────────────────────────────────────── */

export function EscalationDialog({
  open,
  onClose,
  defaultSituation = "",
  defaultUrgency = "urgent",
}: EscalationDialogProps) {
  /* ── Form state ──────────────────────────────────────────── */
  const [situation, setSituation] = useState(defaultSituation);
  const [urgency, setUrgency] = useState<EscalationUrgency>(defaultUrgency);
  const [contactMethod, setContactMethod] =
    useState<EscalationContactMethod>("email");
  const [contactValue, setContactValue] = useState("");

  /* ── Validation state ────────────────────────────────────── */
  const [errors, setErrors] = useState<Record<string, string>>({});

  /* ── Mutation ────────────────────────────────────────────── */
  const mutation = useAdvisoryEscalation();

  /* ── Refs ────────────────────────────────────────────────── */
  const overlayRef = useRef<HTMLDivElement>(null);

  /* ── Sync defaults when dialog opens with new values ─────── */
  useEffect(() => {
    if (open) {
      setSituation(defaultSituation);
      setUrgency(defaultUrgency);
      setContactMethod("email");
      setContactValue("");
      setErrors({});
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, defaultSituation, defaultUrgency]);

  /* ── Escape key handling ─────────────────────────────────── */
  useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !mutation.isPending) {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, mutation.isPending, onClose]);

  /* ── Overlay click handling ──────────────────────────────── */
  const handleOverlayClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === overlayRef.current && !mutation.isPending) {
        onClose();
      }
    },
    [mutation.isPending, onClose],
  );

  /* ── Validation ──────────────────────────────────────────── */
  function validate(): boolean {
    const newErrors: Record<string, string> = {};

    if (situation.trim().length < SITUATION_MIN_LENGTH) {
      newErrors.situation = `Please describe your situation in at least ${SITUATION_MIN_LENGTH} characters.`;
    }

    if (!contactValue.trim()) {
      newErrors.contactValue =
        contactMethod === "email"
          ? "Please enter your email address."
          : "Please enter your phone number.";
    } else if (contactMethod === "email" && !contactValue.includes("@")) {
      newErrors.contactValue = "Please enter a valid email address.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  /* ── Submit ──────────────────────────────────────────────── */
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!validate()) return;

    mutation.mutate(
      {
        situation: situation.trim(),
        urgency,
        contact_method: contactMethod,
        contact_value: contactValue.trim(),
      },
      {
        onSuccess: (data) => {
          const timeframe = data.expected_response_time;
          toast.success(
            `Request received -- a specialist will contact you within ${timeframe}.`,
          );
          onClose();
        },
      },
    );
  }

  /* ── Don't render when closed ────────────────────────────── */
  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      role="dialog"
      aria-modal="true"
      aria-label="Connect to a specialist"
      onClick={handleOverlayClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    >
      <div className="relative w-full max-w-lg rounded-[12px] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-gray-200)]">
          <h2 className="text-lg font-bold text-[var(--color-gray-900)]">
            Connect to a Specialist
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={mutation.isPending}
            className="p-1.5 rounded-lg text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] hover:bg-[var(--color-gray-100)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Close dialog"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* Situation description */}
          <AppInput
            variant="textarea"
            label="Describe your situation"
            value={situation}
            onChange={(e) => {
              setSituation(e.target.value);
              if (errors.situation) {
                setErrors((prev) => {
                  const next = { ...prev };
                  delete next.situation;
                  return next;
                });
              }
            }}
            placeholder="Briefly describe the HR situation you need help with..."
            rows={4}
            required
            error={errors.situation}
            helperText={
              !errors.situation
                ? `${situation.trim().length}/${SITUATION_MIN_LENGTH} minimum characters`
                : undefined
            }
          />

          {/* Urgency level */}
          <AppInput
            variant="select"
            label="How urgent is this?"
            value={urgency}
            onChange={(e) => setUrgency(e.target.value as EscalationUrgency)}
            options={URGENCY_OPTIONS}
          />

          {/* Preferred contact method */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-[var(--color-gray-700)]">
              Preferred contact method
            </label>
            <div className="flex gap-3">
              {CONTACT_METHOD_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    setContactMethod(opt.value);
                    setContactValue("");
                    if (errors.contactValue) {
                      setErrors((prev) => {
                        const next = { ...prev };
                        delete next.contactValue;
                        return next;
                      });
                    }
                  }}
                  className={`flex-1 rounded-[8px] border px-4 py-2.5 text-sm font-medium transition-colors ${
                    contactMethod === opt.value
                      ? "border-[var(--color-primary)] bg-[var(--color-primary-bg)] text-[var(--color-primary)]"
                      : "border-[var(--color-gray-300)] text-[var(--color-gray-600)] hover:border-[var(--color-gray-400)]"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Contact value input */}
            <AppInput
              variant={contactMethod === "email" ? "email" : "text"}
              placeholder={
                contactMethod === "email" ? "you@company.com" : "+65 9123 4567"
              }
              value={contactValue}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                setContactValue(e.target.value);
                if (errors.contactValue) {
                  setErrors((prev) => {
                    const next = { ...prev };
                    delete next.contactValue;
                    return next;
                  });
                }
              }}
              error={errors.contactValue}
              required
            />
          </div>

          {/* Server error */}
          {mutation.isError && (
            <div className="rounded-[8px] border border-[var(--color-error)] bg-red-50 px-4 py-3">
              <p className="text-sm text-[var(--color-error)]">
                Something went wrong. Please try again or contact support
                directly.
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <AppButton
              type="button"
              variant="text"
              size="md"
              onClick={onClose}
              disabled={mutation.isPending}
            >
              Cancel
            </AppButton>
            <AppButton
              type="submit"
              variant="primary"
              size="md"
              loading={mutation.isPending}
            >
              Submit Request
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}
