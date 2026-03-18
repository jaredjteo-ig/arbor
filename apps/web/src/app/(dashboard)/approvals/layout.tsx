"use client";

import type { ReactNode } from "react";
import { ClipboardCheck } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "approvals",
  title: "Approvals",
  tagline: "Review and approve pending requests",
  icon: ClipboardCheck,
  color: "text-violet-600",
  bgColor: "bg-violet-50",
  description:
    "Central approval hub for timesheet entries and inventory requests. Managers can review, approve, or reject submissions with batch actions for efficiency.",
  usps: [
    "Unified approval queue across modules",
    "Batch approve timesheets in one click",
    "Reject with reason for audit trail",
    "Real-time status updates",
  ],
  features: [
    {
      title: "Timesheet Approvals",
      description:
        "Review submitted timesheet entries with employee, project, hours, and description. Approve or reject individually or in batch.",
    },
    {
      title: "Inventory Requests",
      description:
        "Review pending inventory requests with item details and reason. Approve or deny with notes.",
    },
  ],
};

export default function ApprovalsLayout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
