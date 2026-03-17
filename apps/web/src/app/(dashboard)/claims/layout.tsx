"use client";
import type { ReactNode } from "react";
import { Receipt } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "claims", title: "Claims & Expenses", tagline: "Digital expense management with approval workflow",
  icon: Receipt, color: "text-orange-600", bgColor: "bg-orange-50",
  description: "Replace paper receipts and Excel spreadsheets. Employees submit claims with photos, managers approve with one click, and approved amounts flow directly into payroll.",
  usps: [
    "Mobile receipt upload — snap a photo, submit in seconds",
    "Category-based limits — control spending by type",
    "Claims-to-payroll integration — approved claims auto-paid",
    "Complete audit trail — who approved what, when, why",
    "Accounting sync — journal entries to Xero, QBO, Zoho",
    "Custom categories — transport, meals, medical, and more",
  ],
  features: [
    { title: "Digital Claims", description: "Submit claims from web or mobile. Attach up to 5 receipts per item. Draft → submit → approve lifecycle." },
    { title: "Receipt Upload", description: "Photo upload for receipts. Supports JPG, PNG, PDF. Stored securely with the claim." },
    { title: "Approval Workflow", description: "Manager approves/rejects with remarks. Rejection requires reason. Full audit trail." },
    { title: "Categories & Limits", description: "Create custom categories (transport, meals, medical). Set per-claim and monthly limits." },
    { title: "Payroll Integration", description: "Approved claims automatically included in the next payroll run as reimbursements." },
    { title: "Reports", description: "Monthly claim summaries by employee, category, and department. Export to CSV." },
  ],
};

export default function ClaimsLayout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
