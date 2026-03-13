"use client";

/* ── Calculator Detail Page ──────────────────────────────── */
/* Renders the calculator form/results for the given [type].  */
/* Each calculator is a self-contained element component.      */

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getCalculatorBySlug } from "../elements/calculator-config";
import { CpfCalculator } from "../elements/CpfCalculator";
import { QuotaLevyCalculator } from "../elements/QuotaLevyCalculator";
import { LeaveCalculator } from "../elements/LeaveCalculator";
import { NoticePeriodCalculator } from "../elements/NoticePeriodCalculator";
import { OvertimeCalculator } from "../elements/OvertimeCalculator";
import { RetrenchmentCalculator } from "../elements/RetrenchmentCalculator";
import { CostToCompanyCalculator } from "../elements/CostToCompanyCalculator";

interface CalculatorDetailPageProps {
  params: Promise<{ type: string }>;
}

/** Map slug to calculator component. */
const CALCULATOR_COMPONENTS: Record<string, React.ComponentType> = {
  cpf: CpfCalculator,
  "quota-levy": QuotaLevyCalculator,
  leave: LeaveCalculator,
  "notice-period": NoticePeriodCalculator,
  overtime: OvertimeCalculator,
  retrenchment: RetrenchmentCalculator,
  "cost-to-company": CostToCompanyCalculator,
};

export default function CalculatorDetailPage({
  params,
}: CalculatorDetailPageProps) {
  const { type } = use(params);
  const meta = getCalculatorBySlug(type);
  const CalculatorComponent = CALCULATOR_COMPONENTS[type];

  if (!meta || !CalculatorComponent) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <Link
          href="/calculators"
          className="inline-flex items-center gap-1.5 text-sm text-[var(--color-primary)] hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Calculators
        </Link>
        <div className="text-center py-12">
          <p className="text-lg font-semibold text-[var(--color-gray-900)]">
            Calculator not found
          </p>
          <p className="text-sm text-[var(--color-gray-500)] mt-1">
            The calculator type &ldquo;{type}&rdquo; does not exist.
          </p>
        </div>
      </div>
    );
  }

  const Icon = meta.icon;

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Back link */}
      <Link
        href="/calculators"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-primary)] hover:underline"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Calculators
      </Link>

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
          <Icon
            className="h-6 w-6 text-[var(--color-primary)]"
            aria-hidden="true"
          />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            {meta.name}
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            {meta.description}
          </p>
        </div>
      </div>

      {/* Calculator form + results */}
      <CalculatorComponent />
    </div>
  );
}
