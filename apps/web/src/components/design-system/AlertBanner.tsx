"use client";

import clsx from "clsx";
import { Info, AlertTriangle, AlertCircle, CheckCircle, X } from "lucide-react";

export type AlertVariant = "info" | "warning" | "error" | "success";

export interface AlertBannerProps {
  variant: AlertVariant;
  title: string;
  description?: string;
  /** Show a dismiss button */
  dismissible?: boolean;
  /** Called when dismiss button is clicked */
  onDismiss?: () => void;
  className?: string;
}

const variantConfig: Record<
  AlertVariant,
  { icon: typeof Info; bg: string; border: string; text: string }
> = {
  info: {
    icon: Info,
    bg: "bg-[var(--color-info-bg)]",
    border: "border-[var(--color-info)]",
    text: "text-[var(--color-info)]",
  },
  warning: {
    icon: AlertTriangle,
    bg: "bg-[var(--color-warning-bg)]",
    border: "border-[var(--color-warning)]",
    text: "text-[var(--color-warning)]",
  },
  error: {
    icon: AlertCircle,
    bg: "bg-[var(--color-error-bg)]",
    border: "border-[var(--color-error)]",
    text: "text-[var(--color-error)]",
  },
  success: {
    icon: CheckCircle,
    bg: "bg-[var(--color-success-bg)]",
    border: "border-[var(--color-success)]",
    text: "text-[var(--color-success)]",
  },
};

export function AlertBanner({
  variant,
  title,
  description,
  dismissible = false,
  onDismiss,
  className,
}: AlertBannerProps) {
  const { icon: Icon, bg, border, text } = variantConfig[variant];

  return (
    <div
      role="alert"
      className={clsx(
        "w-full rounded-[8px] border-l-4 px-4 py-3",
        bg,
        border,
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <Icon
          className={clsx("h-5 w-5 mt-0.5 shrink-0", text)}
          aria-hidden="true"
        />

        <div className="flex-1 min-w-0">
          <p className={clsx("text-sm font-semibold", text)}>{title}</p>
          {description && (
            <p className="mt-1 text-sm text-[var(--color-gray-700)]">
              {description}
            </p>
          )}
        </div>

        {dismissible && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss alert"
            className={clsx(
              "flex items-center justify-center rounded p-1 min-w-[32px] min-h-[32px]",
              "text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]",
              "hover:bg-black/5 transition-colors",
              "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
            )}
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
