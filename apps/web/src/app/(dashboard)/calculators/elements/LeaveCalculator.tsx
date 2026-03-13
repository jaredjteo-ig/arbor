"use client";

/* ── Leave Entitlement Calculator ────────────────────────── */
/* Calculates statutory leave entitlements based on years of   */
/* service, employment type, and leave category.               */

import { useState } from "react";
import { AppCard, AppButton, AppInput } from "@/components/design-system";
import { ResultPanel } from "./ResultPanel";
import { ResultRow } from "./ResultRow";

/* ── Leave entitlement tables ────────────────────────────── */

function getAnnualLeave(yearsOfService: number): number {
  if (yearsOfService < 1) return 0;
  if (yearsOfService === 1) return 7;
  if (yearsOfService === 2) return 8;
  if (yearsOfService === 3) return 9;
  if (yearsOfService === 4) return 10;
  if (yearsOfService === 5) return 11;
  if (yearsOfService === 6) return 12;
  if (yearsOfService === 7) return 13;
  return 14; // 8+ years
}

interface LeaveResult {
  annualLeave: number;
  sickLeave: number;
  hospitalisationLeave: number;
  maternityLeave: number;
  paternityLeave: number;
  childcarLeave: number;
  basis: string;
  notes: string[];
}

export function LeaveCalculator() {
  const [years, setYears] = useState("");
  const [empType, setEmpType] = useState("full-time");
  const [leaveType, setLeaveType] = useState("all");
  const [result, setResult] = useState<LeaveResult | null>(null);

  const calculate = () => {
    const yearsNum = parseFloat(years);
    if (isNaN(yearsNum) || yearsNum < 0) return;

    const annualLeave = getAnnualLeave(Math.floor(yearsNum));
    const sickLeave = yearsNum >= 0.5 ? 14 : Math.floor(yearsNum * 2 * 14);
    const hospitalisationLeave =
      yearsNum >= 0.5 ? 60 : Math.floor(yearsNum * 2 * 60);
    const maternityLeave = 16 * 7; // 16 weeks in days
    const paternityLeave = 14; // 2 weeks
    const childcarLeave = yearsNum >= 0.25 ? 6 : 0;

    const notes: string[] = [];
    let basis = "Employment Act, Part IV";

    if (empType === "part-time") {
      basis =
        "Employment Act, Part IV + Employment (Part-Time Employees) Regulations";
      notes.push(
        "Part-time employees receive pro-rated leave based on hours worked relative to a comparable full-time employee.",
      );
    }

    if (yearsNum < 0.25) {
      notes.push(
        "Employees with less than 3 months of service are not entitled to statutory leave benefits.",
      );
    } else if (yearsNum < 1) {
      notes.push(
        "Employees in their first year are entitled to pro-rated annual leave after completing 3 months.",
      );
    }

    notes.push(
      "Sick leave and hospitalisation leave entitlements require at least 6 months of service for full entitlement.",
    );
    notes.push(
      "Maternity leave of 16 weeks applies to female employees who have served at least 3 months. Government co-funds the last 8 weeks.",
    );

    setResult({
      annualLeave,
      sickLeave,
      hospitalisationLeave,
      maternityLeave,
      paternityLeave,
      childcarLeave,
      basis,
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
              helperText="Enter 0.5 for 6 months, etc."
            />
            <AppInput
              label="Employment Type"
              variant="select"
              value={empType}
              onChange={(e) =>
                setEmpType((e.target as HTMLSelectElement).value)
              }
              options={[
                { value: "full-time", label: "Full-Time" },
                { value: "part-time", label: "Part-Time" },
              ]}
            />
          </div>

          <AppInput
            label="Leave Category"
            variant="select"
            value={leaveType}
            onChange={(e) =>
              setLeaveType((e.target as HTMLSelectElement).value)
            }
            options={[
              { value: "all", label: "All Leave Types" },
              { value: "annual", label: "Annual Leave Only" },
              { value: "sick", label: "Sick & Hospitalisation Leave" },
              { value: "parental", label: "Parental Leave" },
            ]}
          />

          <AppButton onClick={calculate} className="w-full sm:w-auto">
            Calculate Leave
          </AppButton>
        </div>
      </AppCard>

      {result && (
        <ResultPanel
          title="Leave Entitlement"
          citations={[
            { label: "Employment Act, Part IV", authority: "statutory" },
            {
              label: "Child Development Co-Savings Act",
              authority: "statutory",
            },
          ]}
          advisoryQuery="What are the statutory leave entitlements under Singapore employment law?"
          notes={result.notes}
        >
          {(leaveType === "all" || leaveType === "annual") && (
            <ResultRow
              label="Annual Leave"
              value={`${result.annualLeave} days`}
              bold={leaveType === "annual"}
              highlight={leaveType === "annual"}
            />
          )}
          {(leaveType === "all" || leaveType === "sick") && (
            <>
              <ResultRow
                label="Outpatient Sick Leave"
                value={`${result.sickLeave} days`}
              />
              <ResultRow
                label="Hospitalisation Leave"
                value={`${result.hospitalisationLeave} days`}
                bold={leaveType === "sick"}
                highlight={leaveType === "sick"}
              />
            </>
          )}
          {(leaveType === "all" || leaveType === "parental") && (
            <>
              <ResultRow
                label="Maternity Leave"
                value={`${result.maternityLeave} days (16 weeks)`}
              />
              <ResultRow
                label="Paternity Leave"
                value={`${result.paternityLeave} days (2 weeks)`}
              />
              <ResultRow
                label="Childcare Leave"
                value={`${result.childcarLeave} days/year`}
              />
            </>
          )}
          <ResultRow label="Calculation Basis" value={result.basis} bold />
        </ResultPanel>
      )}
    </div>
  );
}
