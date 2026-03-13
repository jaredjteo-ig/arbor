"use client";

/* ── ResultRow ───────────────────────────────────────────── */
/* A single key/value row used inside calculator result cards. */

import clsx from "clsx";

interface ResultRowProps {
  label: string;
  value: string;
  bold?: boolean;
  highlight?: boolean;
}

export function ResultRow({
  label,
  value,
  bold = false,
  highlight = false,
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
          "text-sm",
          bold
            ? "font-semibold text-[var(--color-gray-900)]"
            : "text-[var(--color-gray-600)]",
        )}
      >
        {label}
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
