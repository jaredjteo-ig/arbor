"use client";

import { useEffect } from "react";
import { Loader2, X } from "lucide-react";
import clsx from "clsx";
import type { PaceStep } from "@/services/api/shadow";

/* ── Types ────────────────────────────────────────────────── */

interface ArborOverlayProps {
  /** Whether the overlay is active (multi-step execution in progress). */
  isActive: boolean;
  /** Current step index (0-based). */
  currentStep: number;
  /** Total number of steps. */
  totalSteps: number;
  /** Step descriptions and statuses. */
  steps: PaceStep[];
  /** Called when the user clicks "Interrupt" to stop execution. */
  onInterrupt: () => void;
  /** Called when execution completes and user dismisses the overlay. */
  onDismiss: () => void;
  /** Whether all steps are complete. */
  isComplete: boolean;
  /** Whether execution failed. */
  isFailed: boolean;
}

/* ── Component ────────────────────────────────────────────── */

/**
 * ArborOverlay (T471)
 *
 * When Arbor executes a multi-step workflow, the main UI dims slightly
 * and Arbor's actions are highlighted with a teal trace. The overlay
 * shows a progress bar with current step / total steps and an
 * "Interrupt" button to stop execution.
 */
export function ArborOverlay({
  isActive,
  currentStep,
  totalSteps,
  steps,
  onInterrupt,
  onDismiss,
  isComplete,
  isFailed,
}: ArborOverlayProps) {
  // Auto-dismiss after 3 seconds when complete
  useEffect(() => {
    if (!isComplete || isFailed) return;
    const timer = setTimeout(onDismiss, 3000);
    return () => clearTimeout(timer);
  }, [isComplete, isFailed, onDismiss]);

  if (!isActive) return null;

  const progressPercent =
    totalSteps > 0
      ? Math.round(((currentStep + (isComplete ? 1 : 0)) / totalSteps) * 100)
      : 0;

  return (
    <>
      {/* Backdrop — dims the main UI */}
      <div
        className="fixed inset-0 bg-black/20 backdrop-blur-[1px] z-[var(--z-shadow-overlay,80)] transition-opacity duration-300"
        aria-hidden="true"
      />

      {/* Execution progress panel */}
      <div
        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[var(--z-shadow-overlay,80)] w-full max-w-md"
        role="status"
        aria-live="polite"
        aria-label="Central execution progress"
      >
        <div className="rounded-xl border border-[var(--color-primary)]/30 bg-[var(--background)] shadow-xl shadow-[var(--color-primary)]/10 p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <svg
                width="16"
                height="16"
                viewBox="0 0 18 18"
                fill="none"
                aria-hidden="true"
              >
                <circle
                  cx="7"
                  cy="9"
                  r="5"
                  fill="var(--color-primary)"
                  opacity="0.6"
                />
                <ellipse
                  cx="12"
                  cy="9"
                  rx="4"
                  ry="3.5"
                  fill="var(--color-primary)"
                  opacity="0.2"
                />
              </svg>
              <span className="text-sm font-semibold text-[var(--foreground)]">
                {isComplete
                  ? "Execution complete"
                  : isFailed
                    ? "Execution stopped"
                    : "Central is working..."}
              </span>
            </div>

            {!isComplete && !isFailed && (
              <button
                type="button"
                onClick={onInterrupt}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-[var(--color-risk-red)] bg-red-50 hover:bg-red-100 transition-colors"
              >
                <X className="h-3 w-3" />
                Interrupt
              </button>
            )}

            {(isComplete || isFailed) && (
              <button
                type="button"
                onClick={onDismiss}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-[var(--color-gray-600)] bg-[var(--color-gray-100)] hover:bg-[var(--color-gray-200)] transition-colors"
              >
                Dismiss
              </button>
            )}
          </div>

          {/* Progress bar */}
          <div className="w-full h-1.5 bg-[var(--color-gray-200)] rounded-full overflow-hidden mb-3">
            <div
              className={clsx(
                "h-full rounded-full transition-all duration-500 ease-out",
                isFailed
                  ? "bg-[var(--color-risk-red)]"
                  : "bg-[var(--color-primary)]",
              )}
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Step list (compact) */}
          <div className="space-y-1.5">
            {steps.map((step, i) => (
              <div
                key={i}
                className={clsx(
                  "flex items-center gap-2 text-xs",
                  step.status === "done"
                    ? "text-[var(--foreground)]"
                    : step.status === "executing"
                      ? "text-[var(--color-primary)] font-medium"
                      : step.status === "failed"
                        ? "text-[var(--color-risk-red)]"
                        : "text-[var(--color-gray-400)]",
                )}
              >
                {step.status === "executing" ? (
                  <Loader2 className="h-3 w-3 animate-spin shrink-0" />
                ) : step.status === "done" ? (
                  <span className="text-[var(--color-primary)] shrink-0">
                    ✓
                  </span>
                ) : step.status === "failed" ? (
                  <span className="text-[var(--color-risk-red)] shrink-0">
                    ✗
                  </span>
                ) : (
                  <span className="text-[var(--color-gray-300)] shrink-0">
                    ○
                  </span>
                )}
                <span className="truncate">{step.description}</span>
              </div>
            ))}
          </div>

          {/* Step counter */}
          <p className="text-xs text-[var(--color-gray-500)] mt-2 text-right">
            Step {Math.min(currentStep + 1, totalSteps)} of {totalSteps}
          </p>
        </div>
      </div>
    </>
  );
}
