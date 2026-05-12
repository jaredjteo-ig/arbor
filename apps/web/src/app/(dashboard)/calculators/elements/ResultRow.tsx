"use client";

/* ── ResultRow ───────────────────────────────────────────── */
/* A single key/value row used inside calculator result cards. */

import { Info } from "lucide-react";
import clsx from "clsx";

interface ResultRowProps {
  label: string;
  value: string;
  bold?: boolean;
  highlight?: boolean;
  /**
   * Optional tooltip text. When provided, renders an info icon next
   * to the label. Used to explain $0 entries (e.g. WICA not applicable
   * for a non-manual SG citizen earning >$2,600/mo) so the buyer
   * doesn't read a legitimate zero as a missing field. See P4-QW-8.
   */
  tooltip?: string;
}

export function ResultRow({
  label,
  value,
  bold = false,
  highlight = false,
  tooltip,
}: ResultRowProps) {
  return (
    <div
      className={clsx(
        "flex items-center justify-between py-2",
        highlight &&
          "bg-[var(--color-primary-bg)] -mx-4 px-4 rounded-lg font-semibold",
      )}
    >
      <span
        className={clsx(
          "text-sm flex items-center gap-1.5",
          bold
            ? "font-semibold text-[var(--color-gray-900)]"
            : "text-[var(--color-gray-600)]",
        )}
      >
        {label}
        {tooltip && (
          <span
            title={tooltip}
            aria-label={tooltip}
            className="inline-flex items-center text-[var(--color-gray-400)] hover:text-[var(--color-gray-600)] cursor-help"
          >
            <Info className="h-3.5 w-3.5" />
          </span>
        )}
      </span>
      <span
        className={clsx(
          "text-sm tabular-nums",
          bold || highlight
            ? "font-semibold text-[var(--color-gray-900)]"
            : "text-[var(--color-gray-900)]",
        )}
      >
        {value}
      </span>
    </div>
  );
}
