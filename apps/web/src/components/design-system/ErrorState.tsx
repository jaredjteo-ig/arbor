"use client";

import clsx from "clsx";
import { AlertCircle, WifiOff, ServerCrash } from "lucide-react";

export type ErrorVariant = "network" | "server" | "unavailable";

export interface ErrorStateProps {
  variant?: ErrorVariant;
  /** Override the default title */
  title?: string;
  /** Override the default description */
  description?: string;
  /** Called when the retry button is clicked */
  onRetry?: () => void;
  /** Label for the retry button */
  retryLabel?: string;
  className?: string;
}

const variantConfig: Record<
  ErrorVariant,
  {
    icon: typeof AlertCircle;
    defaultTitle: string;
    defaultDescription: string;
  }
> = {
  network: {
    icon: WifiOff,
    defaultTitle: "No internet connection",
    defaultDescription: "Please check your network connection and try again.",
  },
  server: {
    icon: AlertCircle,
    defaultTitle: "Something went wrong",
    defaultDescription:
      "We encountered an unexpected error. Please try again or contact support if the problem persists.",
  },
  unavailable: {
    icon: ServerCrash,
    defaultTitle: "Service unavailable",
    defaultDescription:
      "The service is temporarily unavailable. Please try again in a few moments.",
  },
};

export function ErrorState({
  variant = "server",
  title,
  description,
  onRetry,
  retryLabel = "Try again",
  className,
}: ErrorStateProps) {
  const config = variantConfig[variant];
  const Icon = config.icon;

  return (
    <div
      role="alert"
      className={clsx(
        "flex flex-col items-center justify-center text-center px-6 py-12",
        className,
      )}
    >
      <div className="mb-4 text-[var(--color-error)]">
        <Icon className="h-12 w-12" aria-hidden="true" />
      </div>

      <h3 className="text-lg font-semibold text-[var(--color-gray-800)] mb-1">
        {title ?? config.defaultTitle}
      </h3>

      <p className="text-sm text-[var(--color-gray-500)] max-w-sm mb-6">
        {description ?? config.defaultDescription}
      </p>

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className={clsx(
            "inline-flex items-center justify-center gap-2 rounded-[8px] font-medium",
            "px-4 py-2 text-base min-h-[44px]",
            "bg-[var(--color-primary)] text-white",
            "hover:bg-[var(--color-primary-light)] active:bg-[var(--color-primary-dark)]",
            "transition-colors",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
          )}
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
}
