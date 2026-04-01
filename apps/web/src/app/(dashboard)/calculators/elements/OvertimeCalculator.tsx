"use client";

/* ── Overtime Pay Calculator ─────────────────────────────── */
/* Calculates OT eligibility, rate, and pay based on salary,   */
/* worker type, hours, and the type of day worked.             */

import { useState } from "react";
import { AppCard, AppButton, AppInput } from "@/components/design-system";
import { ResultPanel } from "./ResultPanel";
import { ResultRow } from "./ResultRow";

const fmt = (n: number) =>
  `$${(n ?? 0).toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/* ── OT eligibility & rate tables ────────────────────────── */

const SALARY_CAP_WORKMAN = 4500;
const SALARY_CAP_NON_WORKMAN = 2600;

interface OtResult {
  eligible: boolean;
  reason: string;
  otHours: number;
  hourlyRate: number;
  otMultiplier: number;
  otPay: number;
  notes: string[];
}

export function OvertimeCalculator() {
  const [salary, setSalary] = useState("");
  const [isWorkman, setIsWorkman] = useState("yes");
  const [hoursWorked, setHoursWorked] = useState("");
  const [normalHours, setNormalHours] = useState("44");
  const [dayType, setDayType] = useState("normal");
  const [result, setResult] = useState<OtResult | null>(null);

  const calculate = () => {
    const salaryNum = parseFloat(salary);
    const hoursNum = parseFloat(hoursWorked);
    const normalNum = parseFloat(normalHours);

    if (isNaN(salaryNum) || isNaN(hoursNum) || isNaN(normalNum)) return;
    if (salaryNum <= 0 || hoursNum < 0) return;

    const workman = isWorkman === "yes";
    const cap = workman ? SALARY_CAP_WORKMAN : SALARY_CAP_NON_WORKMAN;
    const eligible = salaryNum <= cap;

    let reason: string;
    if (eligible) {
      reason = workman
        ? `Workman earning $${salaryNum.toLocaleString()} (cap: $${cap.toLocaleString()})`
        : `Non-workman earning $${salaryNum.toLocaleString()} (cap: $${cap.toLocaleString()})`;
    } else {
      reason = workman
        ? `Workman salary exceeds $${cap.toLocaleString()} cap`
        : `Non-workman salary exceeds $${cap.toLocaleString()} cap`;
    }

    const otHours = Math.max(0, hoursNum - normalNum);

    // For OT computation, salary is capped at the OT salary cap
    const computeSalary = eligible ? salaryNum : Math.min(salaryNum, cap);
    // Hourly rate = monthly salary / (26 * 8) for daily-rated, or monthly / (normal hours * 4.33)
    const hourlyRate = computeSalary / (normalNum * (52 / 12));

    let otMultiplier: number;
    switch (dayType) {
      case "rest-day":
        otMultiplier = 2.0;
        break;
      case "public-holiday":
        otMultiplier = 2.0;
        break;
      default:
        otMultiplier = 1.5;
    }

    const otPay = eligible
      ? Math.round(otHours * hourlyRate * otMultiplier * 100) / 100
      : 0;

    const notes: string[] = [];
    if (!eligible) {
      notes.push(
        `Employee salary ($${salaryNum.toLocaleString()}) exceeds the overtime eligibility cap of $${cap.toLocaleString()}. OT pay is not mandatory under the Employment Act.`,
      );
    }
    if (workman) {
      notes.push(
        "Workmen include manual labour workers, drivers, cleaners, and similar roles as defined under the Employment Act.",
      );
    }
    if (dayType === "rest-day") {
      notes.push(
        "Work on a rest day attracts 2x pay rate for overtime hours. The basic pay for the rest day itself may also apply.",
      );
    }
    if (dayType === "public-holiday") {
      notes.push(
        "Work on a public holiday attracts 2x pay rate for overtime hours, in addition to the basic holiday pay.",
      );
    }
    notes.push(
      "Maximum OT is 72 hours per month. Based on Employment Act, Part IV.",
    );

    setResult({
      eligible,
      reason,
      otHours,
      hourlyRate: Math.round(hourlyRate * 100) / 100,
      otMultiplier,
      otPay,
      notes,
    });
  };

  return (
    <div className="space-y-6">
      <AppCard variant="standard">
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Monthly Salary ($)"
              variant="number"
              placeholder="e.g. 2400"
              value={salary}
              onChange={(e) => setSalary((e.target as HTMLInputElement).value)}
              min="0"
            />
            <AppInput
              label="Is the Employee a Workman?"
              variant="select"
              value={isWorkman}
              onChange={(e) =>
                setIsWorkman((e.target as HTMLSelectElement).value)
              }
              options={[
                { value: "yes", label: "Yes (manual labour, driver, etc.)" },
                { value: "no", label: "No (PME / office worker)" },
              ]}
              helperText={`OT cap: ${isWorkman === "yes" ? "$4,500" : "$2,600"}`}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <AppInput
              label="Total Hours Worked (week)"
              variant="number"
              placeholder="e.g. 50"
              value={hoursWorked}
              onChange={(e) =>
                setHoursWorked((e.target as HTMLInputElement).value)
              }
              min="0"
            />
            <AppInput
              label="Normal Weekly Hours"
              variant="number"
              placeholder="44"
              value={normalHours}
              onChange={(e) =>
                setNormalHours((e.target as HTMLInputElement).value)
              }
              min="0"
              helperText="Default is 44 hours"
            />
            <AppInput
              label="Day Type"
              variant="select"
              value={dayType}
              onChange={(e) =>
                setDayType((e.target as HTMLSelectElement).value)
              }
              options={[
                { value: "normal", label: "Normal Working Day" },
                { value: "rest-day", label: "Rest Day" },
                { value: "public-holiday", label: "Public Holiday" },
              ]}
            />
          </div>

          <AppButton onClick={calculate} className="w-full sm:w-auto">
            Calculate Overtime
          </AppButton>
        </div>
      </AppCard>

      {result && (
        <ResultPanel
          title="Overtime Calculation"
          citations={[
            { label: "Employment Act, Part IV", authority: "statutory" },
          ]}
          advisoryQuery="What are the overtime pay rules and eligibility criteria under Singapore law?"
          notes={result.notes}
        >
          <ResultRow
            label="OT Eligible"
            value={result.eligible ? "Yes" : "No"}
            bold
            highlight
          />
          <ResultRow label="Reason" value={result.reason} />
          <ResultRow label="OT Hours" value={`${result.otHours} hrs`} />
          <ResultRow label="Hourly Rate" value={fmt(result.hourlyRate)} />
          <ResultRow label="OT Multiplier" value={`${result.otMultiplier}x`} />
          <ResultRow
            label="OT Pay"
            value={result.eligible ? fmt(result.otPay) : "N/A (not eligible)"}
            bold
            highlight
          />
        </ResultPanel>
      )}
    </div>
  );
}
