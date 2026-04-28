"use client";

/**
 * ProgressBar (T204) — linear bar showing % complete for an onboarding
 * assignment. Hovering the bar reveals a tooltip with module-level
 * breakdown (X of Y steps complete in each module).
 *
 * Pure presentation component — caller owns the data shape.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";

export interface ModuleBreakdownItem {
  /** Display name of the module. */
  name: string;
  /** Number of completed steps. */
  completed: number;
  /** Total number of steps. */
  total: number;
}

export interface ProgressBarProps {
  /** Percent complete (0-100). The component clamps and rounds the value. */
  percent: number;
  /** Optional module-level breakdown shown in a tooltip on hover/focus. */
  modules?: ModuleBreakdownItem[];
  /** Optional override for the bar height (defaults to "h-3"). */
  heightClass?: string;
  /** Whether to show the percentage label above the bar (default true). */
  showLabel?: boolean;
  /** Optional label text shown above the bar (default "Overall Progress"). */
  label?: string;
}

function clampPercent(value: number): number {
  if (Number.isNaN(value)) return 0;
  if (value < 0) return 0;
  if (value > 100) return 100;
  return Math.round(value);
}

export function ProgressBar({
  percent,
  modules,
  heightClass = "h-3",
  showLabel = true,
  label,
}: ProgressBarProps) {
  const { t } = useTranslation();
  const pct = clampPercent(percent);
  const [showTooltip, setShowTooltip] = useState(false);
  const hasBreakdown = !!modules && modules.length > 0;
  const labelText =
    label ??
    t("onboarding.progress.overall", { defaultValue: "Overall Progress" });

  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-[var(--color-gray-700)]">
            {labelText}
          </span>
          <span className="text-sm font-bold text-[var(--color-gray-900)]">
            {pct}%
          </span>
        </div>
      )}

      <div
        className="relative"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onFocus={() => setShowTooltip(true)}
        onBlur={() => setShowTooltip(false)}
        tabIndex={hasBreakdown ? 0 : -1}
        role={hasBreakdown ? "tooltip" : undefined}
        aria-label={
          hasBreakdown
            ? t("onboarding.progress.tooltip_label", {
                defaultValue: "Module-level progress breakdown",
              })
            : undefined
        }
      >
        <div
          className={`${heightClass} rounded-full bg-[var(--color-gray-100)] overflow-hidden`}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={t("onboarding.progress.aria_label", {
            defaultValue: "Onboarding completion: {{pct}}%",
            pct,
          })}
        >
          <div
            className="h-full rounded-full bg-[var(--color-primary)] transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>

        {hasBreakdown && showTooltip && (
          <div
            className="absolute z-20 left-1/2 -translate-x-1/2 mt-2 w-72 max-w-[90vw] rounded-[8px] bg-[var(--color-gray-900)] text-white text-xs p-3 shadow-[var(--shadow-raised)]"
            role="tooltip"
          >
            <p className="font-semibold mb-2">
              {t("onboarding.progress.by_module", {
                defaultValue: "By module",
              })}
            </p>
            <ul className="space-y-1.5">
              {modules!.map((m) => {
                const modPct =
                  m.total > 0 ? clampPercent((m.completed / m.total) * 100) : 0;
                return (
                  <li
                    key={m.name}
                    className="flex items-center justify-between gap-3"
                  >
                    <span className="truncate">{m.name}</span>
                    <span className="text-white/70 shrink-0">
                      {m.completed}/{m.total} ({modPct}%)
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProgressBar;
