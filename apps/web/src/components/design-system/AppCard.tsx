"use client";

import type { HTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

export type CardVariant = "standard" | "elevated" | "flat";

export interface AppCardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  header?: ReactNode;
  footer?: ReactNode;
}

const variantStyles: Record<CardVariant, string> = {
  standard: "shadow-[var(--shadow-card)] border border-[var(--color-gray-200)]",
  elevated:
    "shadow-[var(--shadow-raised)] border border-[var(--color-gray-200)]",
  flat: "border border-[var(--color-gray-200)]",
};

export function AppCard({
  variant = "standard",
  header,
  footer,
  className,
  children,
  ...props
}: AppCardProps) {
  return (
    <div
      className={clsx(
        "rounded-[12px] bg-[var(--color-surface-card)] overflow-hidden",
        variantStyles[variant],
        className,
      )}
      {...props}
    >
      {header && (
        <div className="px-5 py-4 border-b border-[var(--color-gray-200)]">
          {header}
        </div>
      )}

      <div className="px-5 py-4">{children}</div>

      {footer && (
        <div className="px-5 py-4 border-t border-[var(--color-gray-200)]">
          {footer}
        </div>
      )}
    </div>
  );
}
