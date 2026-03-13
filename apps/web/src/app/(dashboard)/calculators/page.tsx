"use client";

/* ── Calculator Hub ──────────────────────────────────────── */
/* Grid of available HR calculators. Each card links to the    */
/* calculator detail page at /calculators/[type].              */

import { useRouter } from "next/navigation";
import { AppCard, AppButton } from "@/components/design-system";
import { Calculator } from "lucide-react";
import { CALCULATORS } from "./elements/calculator-config";

export default function CalculatorsPage() {
  const router = useRouter();

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Calculator
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            HR Calculators
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Deterministic calculations based on current Singapore employment
            regulations. All calculations are auditable — no AI, just the law.
          </p>
        </div>
      </div>

      {/* Calculator grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {CALCULATORS.map((calc) => {
          const Icon = calc.icon;
          return (
            <AppCard
              key={calc.slug}
              variant="standard"
              className="flex flex-col"
            >
              <div className="flex-1 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
                    <Icon
                      className="h-5 w-5 text-[var(--color-primary)]"
                      aria-hidden="true"
                    />
                  </div>
                  <h2 className="text-sm font-semibold text-[var(--color-gray-900)]">
                    {calc.name}
                  </h2>
                </div>
                <p className="text-sm text-[var(--color-gray-600)] leading-relaxed">
                  {calc.description}
                </p>
              </div>
              <div className="pt-4">
                <AppButton
                  variant="outlined"
                  size="sm"
                  className="w-full"
                  onClick={() => router.push(`/calculators/${calc.slug}`)}
                >
                  Open Calculator
                </AppButton>
              </div>
            </AppCard>
          );
        })}
      </div>
    </div>
  );
}
