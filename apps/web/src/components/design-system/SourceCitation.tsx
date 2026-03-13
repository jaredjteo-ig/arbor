"use client";

import clsx from "clsx";

export type AuthorityLevel = "statutory" | "guideline" | "best-practice";

export interface SourceCitationProps {
  /** Display text, e.g. "Employment Act, Section 88A" */
  label: string;
  /** Authority level determines badge colour */
  authority: AuthorityLevel;
  /** Click handler for viewing the source */
  onClick?: () => void;
  className?: string;
}

const authorityStyles: Record<AuthorityLevel, string> = {
  statutory:
    "bg-[var(--color-authority-statutory-bg)] text-[var(--color-authority-statutory)] border-[var(--color-authority-statutory)]",
  guideline:
    "bg-[var(--color-authority-guideline-bg)] text-[var(--color-authority-guideline)] border-[var(--color-authority-guideline)]",
  "best-practice":
    "bg-[var(--color-authority-best-practice-bg)] text-[var(--color-authority-best-practice)] border-[var(--color-authority-best-practice)]",
};

const authorityLabels: Record<AuthorityLevel, string> = {
  statutory: "Statutory",
  guideline: "Guideline",
  "best-practice": "Best Practice",
};

export function SourceCitation({
  label,
  authority,
  onClick,
  className,
}: SourceCitationProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Source: ${label} (${authorityLabels[authority]})`}
      className={clsx(
        "inline-flex items-center gap-1 rounded-full",
        "px-2.5 py-1 text-xs font-medium",
        "border min-h-[28px]",
        "transition-opacity hover:opacity-80",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
        "cursor-pointer",
        authorityStyles[authority],
        className,
      )}
    >
      [{label}]
    </button>
  );
}
