"use client";
import type { ReactNode } from "react";
import { CalendarDays } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "leave", title: "Leave Management", tagline: "Full leave lifecycle for Singapore employers",
  icon: CalendarDays, color: "text-blue-600", bgColor: "bg-blue-50",
  description: "Manage every type of leave — from annual and sick leave to maternity, paternity, childcare, and NS leave. Employees apply, managers approve, balances update automatically.",
  usps: [
    "16+ leave types covering all Singapore statutory requirements",
    "Pro-ration for mid-year joiners — automatic calculation",
    "Carry-forward rules with expiry — no manual tracking",
    "Public holiday integration — SG gazetted holidays loaded",
    "Leave-to-payroll sync — unpaid leave auto-deducted",
    "Team calendar view — see who's off at a glance",
  ],
  features: [
    { title: "Leave Application", description: "Employee self-service: apply, view balance, check history. Half-day and multi-day support." },
    { title: "Approval Workflow", description: "Manager reviews and approves/rejects with remarks. Audit trail on every action." },
    { title: "Balance Tracking", description: "Real-time balances per leave type. Entitlement based on service years (EA compliant)." },
    { title: "Leave Policies", description: "Company-level policies with entitlements per leave type. Assign to employee groups." },
    { title: "Leave Calendar", description: "Monthly view showing approved leave and public holidays. Filter by department." },
    { title: "Custom Leave Types", description: "Create company-specific leave types: compassionate, marriage, study, replacement leave, etc." },
    { title: "Carry-Forward", description: "Configure max carry-forward days and expiry periods per leave type." },
    { title: "Public Holidays", description: "Singapore gazetted holidays auto-loaded. Working day calculations exclude holidays." },
  ],
};

export default function LeaveLayout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
