"use client";
import type { ReactNode } from "react";
import { Users } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "employees",
  title: "Employee Management",
  tagline: "Complete employee lifecycle from onboarding to offboarding",
  icon: Users,
  color: "text-teal-600",
  bgColor: "bg-teal-50",
  description:
    "Manage your entire workforce — from hiring and onboarding through to resignation and offboarding. Employee profiles, documents, salary components, emergency contacts, and probation tracking all in one place.",
  usps: [
    "30+ employee profile fields — everything you need",
    "PII encryption (NRIC, bank account) — PDPA compliant",
    "Bulk CSV import — migrate from any HRIS or Excel",
    "Org chart — visualise your company structure",
    "Document storage — contracts, certs, upload and download",
    "Employment history — auto-tracked on every change",
  ],
  features: [
    {
      title: "Employee Profiles",
      description:
        "Personal details, employment terms, bank info, work pass, emergency contacts. All in one view.",
    },
    {
      title: "Onboarding",
      description:
        "Invite employees via email. Guided profile completion. Checklist of required documents.",
    },
    {
      title: "Probation Tracking",
      description:
        "Track probation periods. Auto-reminders before expiry. Confirm or extend with one click.",
    },
    {
      title: "Salary Components",
      description:
        "Basic salary, allowances (transport, meal, housing), deductions (loans, insurance). CRUD per employee.",
    },
    {
      title: "Document Storage",
      description:
        "Upload contracts, certificates, letters. Download or soft-delete. Organised per employee.",
    },
    {
      title: "Org Chart",
      description:
        "Visual organisation structure. Department-based hierarchy with reporting lines.",
    },
    {
      title: "Bulk Import",
      description:
        "Upload CSV with employee data. Preview with validation. Confirm to create records.",
    },
    {
      title: "PII Encryption",
      description:
        "NRIC, bank account, work pass numbers encrypted at rest (Fernet). PDPA audit log on every access.",
    },
  ],
};

export default function EmployeesLayout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
