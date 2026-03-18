"use client";

import type { ReactNode } from "react";
import { BarChart3 } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "reports",
  title: "Reports",
  tagline: "Workforce insights and analytics",
  icon: BarChart3,
  color: "text-indigo-600",
  bgColor: "bg-indigo-50",
  description:
    "Comprehensive reporting hub covering headcount, turnover, payroll, leave, attendance, claims, projects, inventory, and compliance. Filter by date range and department. Export to CSV for further analysis.",
  usps: [
    "11 built-in report types covering all HR modules",
    "Date range and department filters",
    "One-click CSV export for any report",
    "Compliance health check with pass/warning/fail",
    "Real-time data from across all modules",
    "Headcount trends and turnover analytics",
  ],
  features: [
    {
      title: "Workforce Reports",
      description:
        "Headcount by department, turnover analysis with hire/termination trends, and demographic breakdowns.",
    },
    {
      title: "Financial Reports",
      description:
        "Payroll summary, claims breakdown, project cost analysis, and budget variance reports.",
    },
    {
      title: "Operational Reports",
      description:
        "Leave utilisation, attendance patterns, timesheet summaries, and inventory status reports.",
    },
    {
      title: "Compliance",
      description:
        "Automated compliance checks for MOM, CPF, and IRAS requirements. Status dashboard with actionable recommendations.",
    },
  ],
};

export default function ReportsLayout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
