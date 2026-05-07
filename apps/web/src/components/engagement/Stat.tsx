"use client";

/**
 * Shared Stat component (red-team C1 — extracted from 3 duplicated
 * inline definitions in /engagement/page.tsx, /engagement/team/page.tsx,
 * and /engagement/surveys/[id]/page.tsx).
 *
 * Variants:
 *   "plain" — just text, used in inline dashboard rows
 *   "card"  — wrapped in a white card with border
 */

import type { ReactNode } from "react";

interface StatProps {
  label: string;
  value: ReactNode;
  variant?: "plain" | "card";
}

export function Stat({ label, value, variant = "plain" }: StatProps) {
  if (variant === "card") {
    return (
      <div className="rounded-lg bg-white border border-[var(--color-gray-200)] p-4">
        <div className="text-xs text-[var(--color-gray-500)] uppercase tracking-wide">
          {label}
        </div>
        <div className="text-xl font-semibold text-[var(--color-gray-900)] mt-1">
          {value}
        </div>
      </div>
    );
  }
  return (
    <div>
      <div className="text-xs text-[var(--color-gray-500)] uppercase tracking-wide">
        {label}
      </div>
      <div className="text-xl font-semibold text-[var(--color-gray-900)] mt-1">
        {value}
      </div>
    </div>
  );
}
