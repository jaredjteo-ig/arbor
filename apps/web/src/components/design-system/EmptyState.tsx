import type { ReactNode } from "react";
import clsx from "clsx";
import { Inbox } from "lucide-react";

export interface EmptyStateProps {
  /** Icon to display. Defaults to Inbox. */
  icon?: ReactNode;
  /** Main heading */
  message: string;
  /** Longer description below the heading */
  description?: string;
  /** Optional call-to-action element (e.g. an AppButton) */
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  message,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={clsx(
        "flex flex-col items-center justify-center text-center px-6 py-12",
        className,
      )}
    >
      <div className="mb-4 text-[var(--color-gray-400)]">
        {icon ?? <Inbox className="h-12 w-12" aria-hidden="true" />}
      </div>

      <h3 className="text-lg font-semibold text-[var(--color-gray-700)] mb-1">
        {message}
      </h3>

      {description && (
        <p className="text-sm text-[var(--color-gray-500)] max-w-sm mb-4">
          {description}
        </p>
      )}

      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
