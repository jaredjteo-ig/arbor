"use client";

import clsx from "clsx";

/* ── Types ────────────────────────────────────────────────── */

export interface AnnotationData {
  id: string;
  text: string;
  severity?: "high" | "medium" | "low" | "info";
  provision?: string;
  fineAmount?: string;
}

interface InlineAnnotationProps {
  annotation: AnnotationData;
  className?: string;
}

/* ── Severity styles ──────────────────────────────────────── */

const severityLeftBorder: Record<string, string> = {
  high: "border-l-[var(--color-risk-red)]",
  medium: "border-l-[var(--color-risk-amber)]",
  low: "border-l-[var(--color-risk-green)]",
  info: "border-l-[var(--shadow-accent)]",
};

/* ── Component ────────────────────────────────────────────── */

/**
 * Inline Annotation — AI insight embedded within existing pages.
 *
 * Visual treatment: subtle background tint, 2px left border colored by severity,
 * shadow mark disclosure icon. Uses the shadow agent's visual language to
 * distinguish AI content from platform content.
 */
export function InlineAnnotation({
  annotation,
  className,
}: InlineAnnotationProps) {
  const severity = annotation.severity || "info";

  return (
    <div
      className={clsx(
        "flex items-start gap-2 px-3 py-2 rounded-lg",
        "bg-[var(--shadow-surface)] border-l-2",
        "animate-shadow-fade-in",
        severityLeftBorder[severity],
        className,
      )}
      role="note"
      aria-label={`AI insight: ${annotation.text}`}
    >
      {/* Shadow mark disclosure icon */}
      <svg
        width="12"
        height="12"
        viewBox="0 0 18 18"
        fill="none"
        aria-hidden="true"
        className="shrink-0 mt-0.5"
      >
        <circle cx="7" cy="9" r="5" fill="var(--color-primary)" opacity="0.4" />
        <ellipse
          cx="12"
          cy="9"
          rx="4"
          ry="3.5"
          fill="var(--color-primary)"
          opacity="0.15"
        />
      </svg>

      <div className="flex-1 min-w-0">
        <p className="text-[11px] text-[var(--color-gray-600)] leading-snug">
          {annotation.text}
        </p>
        {(annotation.provision || annotation.fineAmount) && (
          <div className="flex items-center gap-1.5 mt-1">
            {annotation.provision && (
              <span className="text-[10px] font-medium text-[var(--color-authority-statutory)] bg-[var(--color-authority-statutory-bg)] rounded-full px-1.5 py-0.5">
                {annotation.provision}
              </span>
            )}
            {annotation.fineAmount && (
              <span className="text-[10px] font-medium text-[var(--color-risk-red)]">
                Fine: {annotation.fineAmount}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
