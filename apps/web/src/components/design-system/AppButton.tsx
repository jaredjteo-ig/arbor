"use client";

import { type ButtonHTMLAttributes, forwardRef } from "react";
import clsx from "clsx";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "outlined"
  | "text"
  | "danger";
export type ButtonSize = "sm" | "md" | "lg";

interface AppButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-light)] active:bg-[var(--color-primary-dark)]",
  secondary:
    "bg-[var(--color-secondary)] text-white hover:bg-[var(--color-secondary-light)] active:bg-[var(--color-secondary-dark)]",
  outlined:
    "border-2 border-[var(--color-primary)] text-[var(--color-primary)] bg-transparent hover:bg-[var(--color-primary)] hover:text-white",
  text: "text-[var(--color-primary)] bg-transparent hover:bg-[var(--color-gray-100)] active:bg-[var(--color-gray-200)]",
  danger:
    "bg-[var(--color-error)] text-white hover:bg-red-700 active:bg-red-800",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm min-h-[36px]",
  md: "px-4 py-2 text-base min-h-[44px]",
  lg: "px-6 py-3 text-base min-h-[48px]",
};

export const AppButton = forwardRef<HTMLButtonElement, AppButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading,
      disabled,
      className,
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={clsx(
          "inline-flex items-center justify-center gap-2 rounded-[8px] font-medium transition-colors",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          variantStyles[variant],
          sizeStyles[size],
          className,
        )}
        {...props}
      >
        {loading && (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  },
);

AppButton.displayName = "AppButton";
