"use client";

import { Toaster, toast as sonnerToast } from "sonner";

/**
 * Pre-configured Sonner Toaster with design-system styling.
 * Mount once in a layout or root component.
 */
export function AppToaster() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        unstyled: true,
        classNames: {
          toast:
            "flex items-start gap-3 w-full rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] px-4 py-3 shadow-[var(--shadow-raised)] text-sm text-[var(--foreground)]",
          title: "font-semibold",
          description: "text-[var(--color-gray-500)]",
          success: "border-l-4 border-l-[var(--color-success)]",
          error: "border-l-4 border-l-[var(--color-error)]",
          warning: "border-l-4 border-l-[var(--color-warning)]",
          info: "border-l-4 border-l-[var(--color-info)]",
        },
      }}
    />
  );
}

/**
 * Re-export sonner's toast function for convenience.
 *
 * Usage:
 * ```ts
 * toast.success("Saved successfully");
 * toast.error("Something went wrong");
 * toast("Neutral message");
 * ```
 */
export const toast = sonnerToast;
