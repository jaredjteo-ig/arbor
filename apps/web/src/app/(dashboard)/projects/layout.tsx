"use client";

import type { ReactNode } from "react";
import { FolderKanban } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "projects",
  title: "Project Management",
  tagline: "Track projects, timesheets, and costs",
  icon: FolderKanban,
  color: "text-sky-600",
  bgColor: "bg-sky-50",
  description:
    "Manage projects from start to finish. Assign team members, track timesheets, monitor budgets, and analyse project costs. Full visibility into resource allocation and project profitability.",
  usps: [
    "Project setup with budgets, timelines, and team assignments",
    "Employee timesheet entry with approval workflow",
    "Real-time budget vs actual cost tracking",
    "Resource allocation and utilisation reports",
    "Project overhead and profitability analysis",
    "Integration with payroll for cost allocation",
  ],
  features: [
    {
      title: "Project Tracking",
      description:
        "Create projects with budgets, milestones, and deadlines. Monitor progress and status across all active projects.",
    },
    {
      title: "Team Assignments",
      description:
        "Assign employees to projects with roles, hourly rates, and allocation percentages. Manage multiple assignments per employee.",
    },
    {
      title: "Timesheets",
      description:
        "Employees log hours against projects. Manager approval workflow. Integration with payroll for overtime and project cost allocation.",
    },
    {
      title: "Cost Analysis",
      description:
        "Real-time budget vs actual comparison. Labour costs from timesheets, overhead allocation, and profitability metrics.",
    },
  ],
};

export default function ProjectsLayout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
