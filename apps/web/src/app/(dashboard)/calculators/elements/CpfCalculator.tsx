"use client";

/* -- CPF Calculator -------------------------------------------------- */
/* Calculates employer/employee CPF contributions and the OA/SA/MA       */
/* allocation by calling the backend /calculator/cpf endpoint.           */
/* All calculation logic lives server-side so rates stay in one place.   */

import { useState } from "react";
import { AppCard, AppButton, AppInput } from "@/components/design-system";
import { InlineAnnotation } from "@/components/shadow-agent";
import type { AnnotationData } from "@/components/shadow-agent";
import { ResultPanel } from "./ResultPanel";
import { ResultRow } from "./ResultRow";
import { useCpfCalculation } from "@/hooks/api/useCalculators";
import type { CpfCalculationResponse } from "@/types/api";

const fmt = (n: number) =>
  `$${(n ?? 0).toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

export function CpfCalculator() {
  const [salary, setSalary] = useState("");
  const [age, setAge] = useState("");
  const [citizenship, setCitizenship] = useState("sc");
  const [prYear, setPrYear] = useState("1");

  const cpfMutation = useCpfCalculation();

  const calculate = () => {
    const salaryNum = parseFloat(salary);
    const ageNum = parseInt(age, 10);

    // Client-side pre-validation to avoid unnecessary API calls
    if (isNaN(salaryNum) || salaryNum <= 0) return;
    if (isNaN(ageNum) || ageNum <= 0) return;

    cpfMutation.mutate({
      gross_salary: salaryNum,
      employee_age: ageNum,
      citizenship_status: citizenship,
      pr_year: citizenship === "pr" ? parseInt(prYear, 10) : null,
    });
  };

  const result: CpfCalculationResponse | undefined = cpfMutation.data;
  const error = cpfMutation.error;

  // Build contextual notes from the result
  const notes: string[] = [];
  if (result) {
    if (!result.cpf_applicable) {
      notes.push(
        "Employment Pass holders are not required to make CPF contributions.",
      );
    }
    if (result.ow_capped) {
      notes.push(
        `Ordinary Wage ceiling of ${fmt(result.breakdown.ceilings.ow_ceiling)} per month applies. Contributions are calculated on the capped amount.`,
      );
    }
    if (result.cpf_tier.startsWith("pr_year")) {
      notes.push(
        `PR Year ${prYear} graduated employer/employee rates applied.`,
      );
    }
    notes.push("Based on CPF contribution rates effective 1 January 2026.");
  }

  // Build contextual inline annotations (T123)
  const resultAnnotations: AnnotationData[] = [];
  if (result) {
    if (result.ow_capped) {
      resultAnnotations.push({
        id: "cpf-ow-ceiling",
        text: "This employee's ordinary wages exceed the OW ceiling ($8,000). CPF is calculated on OW up to the ceiling only.",
        severity: "medium",
        provision: "CPF Act, First Schedule",
      });
    }
    if (result.cpf_tier.startsWith("pr_year")) {
      resultAnnotations.push({
        id: "cpf-pr-graduated",
        text: `PR Year ${prYear} graduated rates apply. Rates increase in subsequent years until full rates are reached in Year 3.`,
        severity: "info",
        provision: "CPF Act, First Schedule",
      });
    }
    resultAnnotations.push({
      id: "cpf-rates-year",
      text: "Based on 2026 CPF contribution rates.",
      severity: "info",
    });
  }

  return (
    <div className="space-y-6">
      <AppCard variant="standard">
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Monthly Gross Salary ($)"
              variant="number"
              placeholder="e.g. 5000"
              value={salary}
              onChange={(e) => setSalary((e.target as HTMLInputElement).value)}
              min="0"
              step="100"
            />
            <AppInput
              label="Employee Age"
              variant="number"
              placeholder="e.g. 30"
              value={age}
              onChange={(e) => setAge((e.target as HTMLInputElement).value)}
              min="16"
              max="100"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Citizenship Status"
              variant="select"
              value={citizenship}
              onChange={(e) =>
                setCitizenship((e.target as HTMLSelectElement).value)
              }
              options={[
                { value: "sc", label: "Singapore Citizen" },
                { value: "pr", label: "Permanent Resident" },
                { value: "ep", label: "Employment Pass" },
              ]}
            />
            {citizenship === "pr" && (
              <AppInput
                label="PR Year"
                variant="select"
                value={prYear}
                onChange={(e) =>
                  setPrYear((e.target as HTMLSelectElement).value)
                }
                options={[
                  { value: "1", label: "1st Year" },
                  { value: "2", label: "2nd Year" },
                  { value: "3", label: "3rd Year onwards" },
                ]}
                helperText="Graduated rates apply in years 1-2"
              />
            )}
          </div>

          <AppButton
            onClick={calculate}
            className="w-full sm:w-auto"
            disabled={cpfMutation.isPending}
          >
            {cpfMutation.isPending ? "Calculating..." : "Calculate CPF"}
          </AppButton>

          {/* Show validation errors from the backend */}
          {error && (
            <div
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
              role="alert"
            >
              {error.message}
            </div>
          )}
        </div>
      </AppCard>

      {result && result.cpf_applicable && (
        <ResultPanel
          title="CPF Contribution Breakdown"
          citations={[
            { label: "CPF Act, First Schedule", authority: "statutory" },
          ]}
          advisoryQuery="What are the current CPF contribution rates and obligations for employers?"
          notes={notes}
        >
          <ResultRow
            label="Employer Contribution"
            value={`${fmt(result.employer_contribution)} (${pct(result.employer_rate)})`}
          />
          <ResultRow
            label="Employee Contribution"
            value={`${fmt(result.employee_contribution)} (${pct(result.employee_rate)})`}
          />
          <ResultRow
            label="Total Contribution"
            value={fmt(result.total_contribution)}
            bold
            highlight
          />
          <div className="pt-2">
            <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider pb-1">
              Account Allocation
            </p>
          </div>
          <ResultRow
            label="Ordinary Account (OA)"
            value={fmt(result.allocation_oa)}
          />
          <ResultRow
            label="Special Account (SA)"
            value={fmt(result.allocation_sa)}
          />
          <ResultRow
            label="MediSave Account (MA)"
            value={fmt(result.allocation_ma)}
          />
        </ResultPanel>
      )}

      {result && !result.cpf_applicable && (
        <ResultPanel
          title="CPF Contribution Breakdown"
          citations={[
            { label: "CPF Act, First Schedule", authority: "statutory" },
          ]}
          advisoryQuery="What are the current CPF contribution rates and obligations for employers?"
          notes={notes}
        >
          <div className="py-4 text-center text-sm text-[var(--color-gray-600)]">
            CPF contributions are not applicable for this employee category.
          </div>
        </ResultPanel>
      )}

      {/* T123: Contextual inline annotations after results */}
      {result && resultAnnotations.length > 0 && (
        <div className="space-y-2">
          {resultAnnotations.map((annotation) => (
            <InlineAnnotation key={annotation.id} annotation={annotation} />
          ))}
        </div>
      )}
    </div>
  );
}
