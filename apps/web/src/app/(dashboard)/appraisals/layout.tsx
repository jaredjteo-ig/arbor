"use client";

import type { ReactNode } from "react";
import { Award } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "appraisals",
  title: "Performance Appraisals",
  tagline: "Structured performance reviews for your team",
  icon: Award,
  color: "text-violet-600",
  bgColor: "bg-violet-50",
  description:
    "Create appraisal templates, launch review cycles, and track employee performance. Supports weighted scoring, self-assessments, and manager reviews with electronic sign-off.",
  usps: [
    "Customisable appraisal templates with weighted sections",
    "Scheduled review periods with automated assignment",
    "Self-assessment and manager review workflow",
    "Electronic sign-off and acknowledgement tracking",
    "Scoring and overall performance ratings",
    "Historical review data for career development",
  ],
  features: [
    {
      title: "Templates",
      description:
        "Build appraisal forms with custom sections, competencies, and KPIs. Enable weightage for balanced scoring.",
    },
    {
      title: "Review Periods",
      description:
        "Set up annual, semi-annual, or quarterly review cycles. Launch periods to assign appraisals to all eligible employees.",
    },
    {
      title: "Performance Reviews",
      description:
        "Employees complete self-assessments. Managers provide ratings and comments. Both sign off on completed reviews.",
    },
    {
      title: "Scoring & Analytics",
      description:
        "Weighted scores across sections. Department-level analytics and performance distribution reports.",
    },
  ],
};

export default function AppraisalsLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
