"use client";

/* ── Retrenchment Benefit Calculator ─────────────────────── */
/* Estimates retrenchment benefit based on years of service,   */
/* monthly salary, and sector norms.                           */

import { useState } from "react";
import { AppCard, AppButton, AppInput } from "@/components/design-system";
import { ResultPanel } from "./ResultPanel";
import { ResultRow } from "./ResultRow";

const fmt = (n: number) =>
  `$${n.toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/* ── Sector norms (weeks per year of service) ──────────── */

interface SectorNorm {
  label: string;
  weeksPerYear: number;
  note: string;
}

const SECTOR_NORMS: Record<string, SectorNorm> = {
  services: {
    label: "Services",
    weeksPerYear: 2,
    note: "Services sector norm: 2 weeks of salary per year of service.",
  },
  manufacturing: {
    label: "Manufacturing",
    weeksPerYear: 2,
    note: "Manufacturing sector norm: 2 weeks of salary per year of service.",
  },
  construction: {
    label: "Construction",
    weeksPerYear: 1.5,
    note: "Construction sector norm: 1.5 weeks of salary per year of service.",
  },
  technology: {
    label: "Technology",
    weeksPerYear: 3,
    note: "Technology sector norm: 3 weeks of salary per year of service.",
  },
  finance: {
    label: "Finance",
    weeksPerYear: 3,
    note: "Finance sector norm: 3 weeks of salary per year of service.",
  },
  other: {
    label: "Other",
    weeksPerYear: 2,
    note: "Default market norm: 2 weeks of salary per year of service.",
  },
};

interface RetrenchmentResult {
  weeksPerYear: number;
  totalWeeks: number;
  benefitPerYear: number;
  totalBenefit: number;
  sectorNote: string;
  notes: string[];
}

export function RetrenchmentCalculator() {
  const [years, setYears] = useState("");
  const [salary, setSalary] = useState("");
  const [sector, setSector] = useState("services");
  const [result, setResult] = useState<RetrenchmentResult | null>(null);

  const calculate = () => {
    const yearsNum = parseFloat(years);
    const salaryNum = parseFloat(salary);
    if (isNaN(yearsNum) || isNaN(salaryNum) || yearsNum <= 0 || salaryNum <= 0)
      return;

    const norm = SECTOR_NORMS[sector];
    const weeksPerYear = norm.weeksPerYear;
    const totalWeeks = weeksPerYear * yearsNum;
    const weeklyRate = salaryNum / 4;
    const benefitPerYear = Math.round(weeklyRate * weeksPerYear * 100) / 100;
    const totalBenefit = Math.round(weeklyRate * totalWeeks * 100) / 100;

    const notes: string[] = [];
    if (yearsNum < 2) {
      notes.push(
        "Employees with less than 2 years of service are generally not entitled to retrenchment benefits under tripartite guidelines, though some employers may still provide them.",
      );
    }
    notes.push(norm.note);
    notes.push(
      "Retrenchment benefits are not mandated by law in Singapore. The amounts shown are based on market norms and tripartite advisory guidelines.",
    );
    notes.push(
      "Employers must notify MOM of retrenchments if retrenching 5 or more employees within 6 months.",
    );

    setResult({
      weeksPerYear,
      totalWeeks,
      benefitPerYear,
      totalBenefit,
      sectorNote: norm.label,
      notes,
    });
  };

  return (
    <div className="space-y-6">
      <AppCard variant="standard">
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Years of Service"
              variant="number"
              placeholder="e.g. 5"
              value={years}
              onChange={(e) => setYears((e.target as HTMLInputElement).value)}
              min="0"
              step="0.5"
            />
            <AppInput
              label="Monthly Salary ($)"
              variant="number"
              placeholder="e.g. 4000"
              value={salary}
              onChange={(e) => setSalary((e.target as HTMLInputElement).value)}
              min="0"
            />
          </div>
          <AppInput
            label="Sector"
            variant="select"
            value={sector}
            onChange={(e) => setSector((e.target as HTMLSelectElement).value)}
            options={Object.entries(SECTOR_NORMS).map(([key, val]) => ({
              value: key,
              label: val.label,
            }))}
            helperText="Sector norms affect the typical benefit rate"
          />

          <AppButton onClick={calculate} className="w-full sm:w-auto">
            Calculate Retrenchment
          </AppButton>
        </div>
      </AppCard>

      {result && (
        <ResultPanel
          title="Retrenchment Benefit Estimate"
          citations={[
            {
              label: "Tripartite Advisory on Managing Excess Manpower",
              authority: "guideline",
            },
            {
              label: "MOM Retrenchment Advisory",
              authority: "best-practice",
            },
          ]}
          advisoryQuery="What are the retrenchment benefit guidelines and employer obligations in Singapore?"
          notes={result.notes}
        >
          <ResultRow
            label="Statutory Minimum"
            value="None -- advisory norms only"
            bold
          />
          <ResultRow label="Sector" value={result.sectorNote} />
          <ResultRow
            label="Market Norm"
            value={`${result.weeksPerYear} weeks per year of service`}
          />
          <ResultRow label="Total Weeks" value={`${result.totalWeeks} weeks`} />
          <ResultRow
            label="Benefit Per Year of Service"
            value={fmt(result.benefitPerYear)}
          />
          <ResultRow
            label="Estimated Total Benefit"
            value={fmt(result.totalBenefit)}
            bold
            highlight
          />
        </ResultPanel>
      )}
    </div>
  );
}
