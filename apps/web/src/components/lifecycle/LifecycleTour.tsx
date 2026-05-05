"use client";

/* P1-9 (obayashi): one-time onboarding tour pop-over for the lifecycle
   page. Persisted via Company.feature_flags.seen_lifecycle_tour.
*/

import { useState } from "react";
import { X, Compass } from "lucide-react";
import { strategyApi } from "@/services/api/strategy";

interface Props {
  /** True when the company hasn't yet dismissed the tour. */
  initialOpen: boolean;
}

export function LifecycleTour({ initialOpen }: Props) {
  const [open, setOpen] = useState(initialOpen);

  const dismiss = async () => {
    setOpen(false);
    try {
      await strategyApi.dismissLifecycleTour();
    } catch {
      // Best-effort; the next render will still show the tour, no real harm.
    }
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-label="Lifecycle dashboard tour"
      className="fixed bottom-6 right-6 z-40 max-w-sm rounded-xl border border-[var(--color-gray-200)] bg-white shadow-xl p-4 sm:p-5"
    >
      <div className="flex items-start gap-3">
        <Compass
          className="h-5 w-5 text-[var(--color-primary)] shrink-0 mt-0.5"
          aria-hidden="true"
        />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Welcome to your Lifecycle map
          </h3>
          <ul className="mt-2 space-y-1.5 text-xs text-[var(--color-gray-700)] list-disc list-inside">
            <li>The 8 cards above are your employee lifecycle stages.</li>
            <li>Click any stage to drill in and see KPIs + quick actions.</li>
            <li>Amber and red pills flag attention items first.</li>
          </ul>
        </div>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Dismiss tour"
          className="rounded-md p-1 text-[var(--color-gray-400)] hover:text-[var(--color-gray-700)] hover:bg-[var(--color-gray-50)]"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      <button
        type="button"
        onClick={dismiss}
        className="mt-3 w-full rounded-lg bg-[var(--color-primary)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
      >
        Got it
      </button>
    </div>
  );
}
