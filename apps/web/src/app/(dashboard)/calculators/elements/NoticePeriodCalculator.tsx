"use client";

/* ── Notice Period Calculator ────────────────────────────── */
/* Determines notice period length and salary-in-lieu based   */
/* on years of service and contractual terms.                  */

import { useState } from "react";
import { AppCard, AppButton, AppInput } from "@/components/design-system";
import { ResultPanel } from "./ResultPanel";
import { ResultRow } from "./ResultRow";

const fmt = (n: number) =>
  `$${n.toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/* ── Statutory defaults (Employment Act, s10) ────────────── */

function getStatutoryNoticeWeeks(yearsOfService: number): number {
  if (yearsOfService < 0.5) return 1;
  if (yearsOfService < 2) return 1;
  if (yearsOfService < 5) return 2;
  return 4;
}

interface NoticeResult {
  noticeWeeks: number;
  source: string;
  salaryInLieu: number;
  notes: string[];
}

export function NoticePeriodCalculator() {
  const [years, setYears] = useState("");
  const [salary, setSalary] = useState("");
  const [contractualWeeks, setContractualWeeks] = useState("");
  const [terminator, setTerminator] = useState("employer");
  const [result, setResult] = useState<NoticeResult | null>(null);

  const calculate = () => {
    const yearsNum = parseFloat(years);
    const salaryNum = parseFloat(salary);
    if (isNaN(yearsNum) || isNaN(salaryNum) || salaryNum <= 0) return;

    const statutoryWeeks = getStatutoryNoticeWeeks(yearsNum);
    const contractWeeks = parseInt(contractualWeeks) || 0;

    // Use whichever is longer: contractual or statutory
    const noticeWeeks = contractWeeks > 0 ? contractWeeks : statutoryWeeks;
    const source =
      contractWeeks > 0
        ? `Contract (${contractWeeks} weeks)`
        : `Employment Act, s10 (${statutoryWeeks} weeks)`;

    // Salary-in-lieu: monthly salary / 4 * notice weeks
    const weeklyRate = salaryNum / 4;
    const salaryInLieu = Math.round(weeklyRate * noticeWeeks * 100) / 100;

    const notes: string[] = [];
    if (contractWeeks > 0 && contractWeeks < statutoryWeeks) {
      notes.push(
        `Your contractual notice period (${contractWeeks} weeks) is shorter than the statutory minimum (${statutoryWeeks} weeks). The statutory minimum applies.`,
      );
    }
    if (terminator === "employer") {
      notes.push(
        "The employer must give the employee the required notice or pay salary-in-lieu. The employee may waive notice.",
      );
    } else {
      notes.push(
        "The employee must give the employer the required notice or pay salary-in-lieu. The employer may waive notice.",
      );
    }
    notes.push(
      "During probation, notice period is typically 1 week or as stated in the contract. Check your employment contract.",
    );
    notes.push(
      "Based on Employment Act, Section 10. Applies to employees covered under Part IV of the Employment Act.",
    );

    setResult({
      noticeWeeks:
        contractWeeks > 0 && contractWeeks < statutoryWeeks
          ? statutoryWeeks
          : noticeWeeks,
      source,
      salaryInLieu,
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
              placeholder="e.g. 3"
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Contractual Notice (weeks)"
              variant="number"
              placeholder="Leave blank if none"
              value={contractualWeeks}
              onChange={(e) =>
                setContractualWeeks((e.target as HTMLInputElement).value)
              }
              min="0"
              helperText="If your contract specifies a notice period"
            />
            <AppInput
              label="Who is Terminating?"
              variant="select"
              value={terminator}
              onChange={(e) =>
                setTerminator((e.target as HTMLSelectElement).value)
              }
              options={[
                { value: "employer", label: "Employer" },
                { value: "employee", label: "Employee" },
              ]}
            />
          </div>

          <AppButton onClick={calculate} className="w-full sm:w-auto">
            Calculate Notice Period
          </AppButton>
        </div>
      </AppCard>

      {result && (
        <ResultPanel
          title="Notice Period"
          citations={[
            { label: "Employment Act, Section 10", authority: "statutory" },
          ]}
          advisoryQuery="What are the notice period requirements for termination under Singapore employment law?"
          notes={result.notes}
        >
          <ResultRow
            label="Notice Period"
            value={`${result.noticeWeeks} week${result.noticeWeeks !== 1 ? "s" : ""}`}
            bold
            highlight
          />
          <ResultRow label="Source" value={result.source} />
          <ResultRow
            label="Salary-in-Lieu"
            value={fmt(result.salaryInLieu)}
            bold
          />
        </ResultPanel>
      )}
    </div>
  );
}
