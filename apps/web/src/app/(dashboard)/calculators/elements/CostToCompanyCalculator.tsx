"use client";

/* ── Cost-to-Company Calculator ──────────────────────────── */
/* Shows the full employer cost breakdown: base salary + CPF   */
/* + foreign worker levy + SDL + work injury insurance.        */

import { useState } from "react";
import { AppCard, AppButton, AppInput } from "@/components/design-system";
import { ResultPanel } from "./ResultPanel";
import { ResultRow } from "./ResultRow";

const fmt = (n: number) =>
  `$${n.toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/* ── CPF employer rates ─────────────────────────────────── */

function getEmployerCpfRate(
  age: number,
  citizenship: string,
  prYear: number,
): number {
  if (citizenship === "ep" || citizenship === "sp" || citizenship === "wp")
    return 0;

  // PR graduated rates
  if (citizenship === "pr" && prYear === 1) return 0.04;
  if (citizenship === "pr" && prYear === 2) return 0.09;

  // SC or PR 3rd year onwards
  if (age <= 55) return 0.17;
  if (age <= 60) return 0.15;
  if (age <= 65) return 0.115;
  if (age <= 70) return 0.085;
  return 0.075;
}

/* ── Levy rates by pass type ─────────────────────────────── */

interface SectorLevyConfig {
  label: string;
  wpLevy: number;
  spLevy: number;
}

const SECTOR_LEVIES: Record<string, SectorLevyConfig> = {
  services: { label: "Services", wpLevy: 450, spLevy: 550 },
  manufacturing: { label: "Manufacturing", wpLevy: 450, spLevy: 550 },
  construction: { label: "Construction", wpLevy: 450, spLevy: 550 },
  technology: { label: "Technology", wpLevy: 450, spLevy: 550 },
  finance: { label: "Finance", wpLevy: 450, spLevy: 550 },
};

/* ── SDL ─────────────────────────────────────────────────── */
const SDL_RATE = 0.0025;
const SDL_MIN = 2;
const SDL_MAX = 11.25;

function calculateSdl(salary: number): number {
  const sdl = salary * SDL_RATE;
  if (sdl < SDL_MIN) return SDL_MIN;
  if (sdl > SDL_MAX) return SDL_MAX;
  return Math.round(sdl * 100) / 100;
}

interface CostResult {
  baseSalary: number;
  cpfEmployer: number;
  levy: number;
  sdl: number;
  insurance: number;
  totalCost: number;
  notes: string[];
}

export function CostToCompanyCalculator() {
  const [salary, setSalary] = useState("");
  const [citizenship, setCitizenship] = useState("sc");
  const [age, setAge] = useState("30");
  const [prYear, setPrYear] = useState("3");
  const [sector, setSector] = useState("services");
  const [result, setResult] = useState<CostResult | null>(null);

  const calculate = () => {
    const salaryNum = parseFloat(salary);
    const ageNum = parseInt(age);
    if (isNaN(salaryNum) || salaryNum <= 0) return;

    // CPF employer contribution
    const cpfCeiling = 6800;
    const cappedSalary = Math.min(salaryNum, cpfCeiling);
    const cpfRate = getEmployerCpfRate(
      ageNum || 30,
      citizenship,
      parseInt(prYear),
    );
    const cpfEmployer = Math.round(cappedSalary * cpfRate * 100) / 100;

    // Foreign worker levy
    let levy = 0;
    const sectorConfig = SECTOR_LEVIES[sector];
    const isForeign = citizenship !== "sc" && citizenship !== "pr";
    if (citizenship === "wp") {
      levy = sectorConfig.wpLevy;
    } else if (citizenship === "sp") {
      levy = sectorConfig.spLevy;
    }

    // SDL
    const sdl = calculateSdl(salaryNum);

    // WICA insurance estimate: $15/month for foreign workers, $0 for SC/PR
    const insurance = isForeign ? 15 : 0;

    const totalCost =
      Math.round((salaryNum + cpfEmployer + levy + sdl + insurance) * 100) /
      100;

    const notes: string[] = [];
    if (citizenship === "sc" || citizenship === "pr") {
      notes.push(
        `CPF employer contribution at ${(cpfRate * 100).toFixed(1)}% on salary capped at $${cpfCeiling.toLocaleString()}.`,
      );
    }
    if (citizenship === "pr") {
      notes.push(
        `PR Year ${prYear} graduated employer CPF rate of ${(cpfRate * 100).toFixed(1)}% applied.`,
      );
    }
    if (citizenship === "wp" || citizenship === "sp") {
      notes.push(
        `Foreign worker levy of $${levy}/month applies for ${citizenship.toUpperCase()} holders.`,
      );
    }
    notes.push(
      `Skills Development Levy (SDL) of $${sdl.toFixed(2)}/month (0.25% of salary, min $2, max $11.25).`,
    );
    if (isForeign) {
      notes.push(
        "WICA insurance estimate of $15/month included for foreign workers.",
      );
    }
    notes.push(
      "Does not include variable costs such as bonuses, benefits-in-kind, or training costs.",
    );

    setResult({
      baseSalary: salaryNum,
      cpfEmployer,
      levy,
      sdl,
      insurance,
      totalCost,
      notes,
    });
  };

  // Determine which fields to show based on citizenship
  const showPrYear = citizenship === "pr";

  return (
    <div className="space-y-6">
      <AppCard variant="standard">
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Monthly Salary ($)"
              variant="number"
              placeholder="e.g. 5000"
              value={salary}
              onChange={(e) => setSalary((e.target as HTMLInputElement).value)}
              min="0"
            />
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
                { value: "sp", label: "S Pass" },
                { value: "wp", label: "Work Permit" },
              ]}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Employee Age"
              variant="number"
              placeholder="e.g. 30"
              value={age}
              onChange={(e) => setAge((e.target as HTMLInputElement).value)}
              min="16"
              max="100"
              helperText="Affects CPF employer contribution rate"
            />
            {showPrYear && (
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
                helperText="Graduated CPF rates apply in years 1-2"
              />
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Sector"
              variant="select"
              value={sector}
              onChange={(e) => setSector((e.target as HTMLSelectElement).value)}
              options={Object.entries(SECTOR_LEVIES).map(([key, val]) => ({
                value: key,
                label: val.label,
              }))}
              helperText="Affects foreign worker levy rates"
            />
          </div>

          <AppButton onClick={calculate} className="w-full sm:w-auto">
            Calculate Total Cost
          </AppButton>
        </div>
      </AppCard>

      {result && (
        <ResultPanel
          title="Cost-to-Company Breakdown"
          citations={[
            { label: "CPF Act", authority: "statutory" },
            {
              label: "Skills Development Levy Act",
              authority: "statutory",
            },
            {
              label: "Employment of Foreign Manpower Act",
              authority: "statutory",
            },
            { label: "WICA", authority: "statutory" },
          ]}
          advisoryQuery="What is the full cost breakdown for hiring an employee in Singapore?"
          notes={result.notes}
        >
          <ResultRow
            label="Base Monthly Salary"
            value={fmt(result.baseSalary)}
          />
          <ResultRow label="CPF (Employer)" value={fmt(result.cpfEmployer)} />
          <ResultRow label="Foreign Worker Levy" value={fmt(result.levy)} />
          <ResultRow label="SDL" value={fmt(result.sdl)} />
          <ResultRow
            label="WICA Insurance (est.)"
            value={fmt(result.insurance)}
          />
          <ResultRow
            label="Total Monthly Cost"
            value={fmt(result.totalCost)}
            bold
            highlight
          />
          <ResultRow
            label="Total Annual Cost"
            value={fmt(result.totalCost * 12)}
            bold
          />
        </ResultPanel>
      )}
    </div>
  );
}
