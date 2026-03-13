"use client";

import { useState } from "react";
import { AppButton, AppInput, AppCard } from "@/components/design-system";
import { X } from "lucide-react";
import { useCreateQaSession } from "@/hooks/api/useQa";
import type {
  QARiskTierFilter,
  QASamplingStrategy,
  QASessionFilters,
} from "@/types/api";

/* ── Props ───────────────────────────────────────────────── */

interface NewSessionModalProps {
  open: boolean;
  onClose: () => void;
}

/* ── Constants ───────────────────────────────────────────── */

const RISK_TIER_OPTIONS: { value: QARiskTierFilter; label: string }[] = [
  { value: "all", label: "All tiers" },
  { value: "green", label: "Green (Low Risk)" },
  { value: "amber", label: "Amber (Medium Risk)" },
  { value: "red", label: "Red (High Risk)" },
];

const SAMPLING_OPTIONS: { value: QASamplingStrategy; label: string }[] = [
  { value: "random", label: "Random" },
  { value: "lowest-confidence", label: "Lowest confidence first" },
  { value: "flagged-first", label: "Flagged first" },
  { value: "recent-first", label: "Most recent first" },
];

const DOMAIN_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "All domains" },
  { value: "employment", label: "Employment Act" },
  { value: "cpf", label: "CPF" },
  { value: "workplace-safety", label: "Workplace Safety" },
  { value: "foreign-workers", label: "Foreign Workers" },
  { value: "leave", label: "Leave Entitlements" },
  { value: "termination", label: "Termination & Retrenchment" },
];

/* ── Component ───────────────────────────────────────────── */

export function NewSessionModal({ open, onClose }: NewSessionModalProps) {
  const createSession = useCreateQaSession();

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [riskTier, setRiskTier] = useState<QARiskTierFilter>("all");
  const [domain, setDomain] = useState("all");
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [confidenceMin, setConfidenceMin] = useState(0);
  const [confidenceMax, setConfidenceMax] = useState(1);
  const [samplingStrategy, setSamplingStrategy] =
    useState<QASamplingStrategy>("random");

  function handleSubmit() {
    const filters: QASessionFilters = {
      sampling_strategy: samplingStrategy,
    };

    if (dateFrom) filters.date_from = dateFrom;
    if (dateTo) filters.date_to = dateTo;
    if (riskTier !== "all") filters.risk_tier = riskTier;
    if (domain !== "all") filters.domain = domain;
    if (flaggedOnly) filters.flagged_only = true;
    if (confidenceMin > 0) filters.confidence_min = confidenceMin;
    if (confidenceMax < 1) filters.confidence_max = confidenceMax;

    createSession.mutate(
      { filters },
      {
        onSuccess: () => {
          onClose();
          // Reset form
          setDateFrom("");
          setDateTo("");
          setRiskTier("all");
          setDomain("all");
          setFlaggedOnly(false);
          setConfidenceMin(0);
          setConfidenceMax(1);
          setSamplingStrategy("random");
        },
      },
    );
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-label="Start new QA session"
    >
      <AppCard
        variant="elevated"
        className="w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto"
        header={
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Start New QA Session
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-md hover:bg-[var(--color-gray-100)] transition-colors"
              aria-label="Close modal"
            >
              <X className="h-4 w-4 text-[var(--color-gray-500)]" />
            </button>
          </div>
        }
      >
        <div className="space-y-4">
          {/* Date range */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--color-gray-700)]">
                Date from
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full rounded-[8px] border px-3 py-2 text-base min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] focus:border-[var(--color-surface-input-focus)]"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--color-gray-700)]">
                Date to
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full rounded-[8px] border px-3 py-2 text-base min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] focus:border-[var(--color-surface-input-focus)]"
              />
            </div>
          </div>

          {/* Risk tier filter */}
          <AppInput
            variant="select"
            label="Risk tier"
            value={riskTier}
            onChange={(e) =>
              setRiskTier(
                (e.target as HTMLSelectElement).value as QARiskTierFilter,
              )
            }
            options={RISK_TIER_OPTIONS}
          />

          {/* Domain filter */}
          <AppInput
            variant="select"
            label="Domain"
            value={domain}
            onChange={(e) => setDomain((e.target as HTMLSelectElement).value)}
            options={DOMAIN_OPTIONS}
          />

          {/* Flagged only toggle */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={flaggedOnly}
              onChange={(e) => setFlaggedOnly(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
            />
            <span className="text-sm font-medium text-[var(--color-gray-700)]">
              Flagged conversations only
            </span>
          </label>

          {/* Confidence range */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-[var(--color-gray-700)]">
              Confidence range
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[var(--color-gray-500)]">
                  Min: {confidenceMin.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={confidenceMin}
                  onChange={(e) => setConfidenceMin(Number(e.target.value))}
                  className="w-full accent-[var(--color-primary)]"
                />
              </div>
              <div>
                <label className="text-xs text-[var(--color-gray-500)]">
                  Max: {confidenceMax.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={confidenceMax}
                  onChange={(e) => setConfidenceMax(Number(e.target.value))}
                  className="w-full accent-[var(--color-primary)]"
                />
              </div>
            </div>
          </div>

          {/* Sampling strategy */}
          <AppInput
            variant="select"
            label="Sampling strategy"
            value={samplingStrategy}
            onChange={(e) =>
              setSamplingStrategy(
                (e.target as HTMLSelectElement).value as QASamplingStrategy,
              )
            }
            options={SAMPLING_OPTIONS}
          />

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <AppButton variant="text" size="sm" onClick={onClose}>
              Cancel
            </AppButton>
            <AppButton
              size="sm"
              onClick={handleSubmit}
              loading={createSession.isPending}
            >
              Start Session
            </AppButton>
          </div>

          {createSession.isError && (
            <p className="text-sm text-[var(--color-error)]">
              {createSession.error.message}
            </p>
          )}
        </div>
      </AppCard>
    </div>
  );
}
