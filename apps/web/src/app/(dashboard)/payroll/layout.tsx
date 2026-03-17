"use client";

import type { ReactNode } from "react";
import { Wallet } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "payroll",
  title: "Payroll",
  tagline: "Singapore-compliant payroll processing",
  icon: Wallet,
  color: "text-emerald-600",
  bgColor: "bg-emerald-50",
  description:
    "Run payroll for your entire workforce — from gross-to-net calculation with CPF, SDL, FWL, and SHG, to generating payslips, bank files, and statutory filings. Everything a Singapore employer needs.",
  usps: [
    "CPF for all age bands, PR graduated rates, OW/AW ceilings",
    "One-click payslip generation (EA s88A compliant)",
    "Bank GIRO & FAST file generation for DBS, OCBC, UOB",
    "IR8A/IR21 tax filing data — ready for IRAS submission",
    "Auto-pulls leave deductions, OT hours, approved claims",
    "Back-pay, bonuses, 13th-month, final salary all handled",
  ],
  features: [
    {
      title: "Gross-to-Net Calculation",
      description:
        "Full salary calculation with all statutory deductions. Supports full-time, part-time, contractors.",
    },
    {
      title: "CPF Contributions",
      description:
        "All age bands, PR Year 1/2/3+ graduated rates, OW ceiling $8,000, annual ceiling $102,000.",
    },
    {
      title: "Payslip Generation",
      description:
        "Itemised payslips compliant with EA s88A. HTML/PDF with company branding. Email delivery.",
    },
    {
      title: "Statutory File Generation",
      description:
        "CPF e-Submit, bank GIRO (ISO 20022), IR8A/IR21 tax data. Ready for portal upload.",
    },
    {
      title: "YTD Tracking",
      description:
        "Year-to-date CPF tracking per employee. Mid-year joiners, leavers, and PR status changes.",
    },
    {
      title: "Payroll Reports",
      description:
        "Summary by department, YTD reports, payment reconciliation. CSV export.",
    },
    {
      title: "Back-Pay & Bonuses",
      description:
        "Back-pay adjustments, AWS, commissions, bonus runs with correct CPF treatment.",
    },
    {
      title: "Final Salary",
      description:
        "Auto-calculated final salary — pro-rated pay, leave encashment, IR21 for foreign leavers.",
    },
  ],
};

export default function PayrollLayout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
