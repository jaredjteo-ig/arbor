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
    "Candidate pipeline tracking (new to hired)",
    "Interview scheduling with multiple round support",
    "Interview feedback and ratings from interviewers",
    "Candidate-to-employee conversion on hire",
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
        "Track candidates at each stage from new through screening, interview, offer, to hired. Update stages and add notes as candidates progress.",
    },
    {
      title: "Interview Management",
      description:
        "Schedule phone, video, onsite, and panel interviews. Collect structured feedback and ratings from interviewers.",
    },
    {
      title: "Hiring & Onboarding",
      description:
        "Generate offers for candidates. Convert hired candidates directly into employee records. Seamless onboarding handoff.",
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
