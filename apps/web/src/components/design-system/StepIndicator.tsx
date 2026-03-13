"use client";

import clsx from "clsx";
import { Check } from "lucide-react";

export interface StepIndicatorProps {
  /** Array of step labels */
  steps: string[];
  /** Zero-based index of the current step */
  currentStep: number;
  className?: string;
}

export function StepIndicator({
  steps,
  currentStep,
  className,
}: StepIndicatorProps) {
  return (
    <nav aria-label="Progress" className={clsx("w-full", className)}>
      <ol className="flex items-center">
        {steps.map((label, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isLast = index === steps.length - 1;

          return (
            <li
              key={label}
              className={clsx("flex items-center", !isLast && "flex-1")}
            >
              <div className="flex flex-col items-center gap-1.5">
                {/* Step circle */}
                <div
                  aria-current={isCurrent ? "step" : undefined}
                  className={clsx(
                    "flex items-center justify-center rounded-full",
                    "h-8 w-8 text-sm font-medium shrink-0",
                    "transition-colors",
                    isCompleted && "bg-[var(--color-secondary)] text-white",
                    isCurrent &&
                      "bg-[var(--color-primary)] text-white ring-2 ring-offset-2 ring-[var(--color-primary)]",
                    !isCompleted &&
                      !isCurrent &&
                      "bg-[var(--color-gray-200)] text-[var(--color-gray-500)]",
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    index + 1
                  )}
                </div>

                {/* Step label */}
                <span
                  className={clsx(
                    "text-xs text-center max-w-[80px] leading-tight",
                    isCurrent
                      ? "font-semibold text-[var(--color-primary)]"
                      : isCompleted
                        ? "font-medium text-[var(--color-secondary)]"
                        : "text-[var(--color-gray-500)]",
                  )}
                >
                  {label}
                </span>
              </div>

              {/* Connector line */}
              {!isLast && (
                <div
                  className={clsx(
                    "flex-1 h-0.5 mx-2 mt-[-20px]",
                    isCompleted
                      ? "bg-[var(--color-secondary)]"
                      : "bg-[var(--color-gray-200)]",
                  )}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
