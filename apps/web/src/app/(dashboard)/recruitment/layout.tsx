"use client";

import type { ReactNode } from "react";
import { UserPlus } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "recruitment",
  title: "Recruitment",
  tagline: "Hire the right people, faster",
  icon: UserPlus,
  color: "text-teal-600",
  bgColor: "bg-teal-50",
  description:
    "End-to-end recruitment management. Post job listings, track candidates through your hiring pipeline, schedule interviews, collect feedback, and convert hires into employees seamlessly.",
  usps: [
    "Job listings with department, type, and salary range",
    "Kanban-style candidate pipeline (new to hired)",
    "Interview scheduling with multiple round support",
    "Structured interview feedback and scorecards",
    "One-click candidate-to-employee conversion",
    "Recruitment analytics and time-to-hire metrics",
  ],
  features: [
    {
      title: "Job Listings",
      description:
        "Create and publish job openings with descriptions, requirements, and salary ranges. Track application volumes per listing.",
    },
    {
      title: "Candidate Pipeline",
      description:
        "Visual kanban board showing candidates at each stage. Drag-and-drop between stages. Bulk actions for efficient processing.",
    },
    {
      title: "Interview Management",
      description:
        "Schedule phone, video, onsite, and panel interviews. Calendar integration. Automated reminders for interviewers and candidates.",
    },
    {
      title: "Hiring & Onboarding",
      description:
        "Generate offer letters. Convert hired candidates directly into employee records with pre-filled data. Seamless onboarding handoff.",
    },
  ],
};

export default function RecruitmentLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
