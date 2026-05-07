"use client";

import type { ReactNode } from "react";
import { MessageSquareHeart } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "engagement",
  title: "Engagement Surveys",
  tagline: "See engagement signals before they become resignations",
  icon: MessageSquareHeart,
  color: "text-rose-600",
  bgColor: "bg-rose-50",
  description:
    "Launch pulse surveys, Q12 assessments, and Trust Index reviews. Track trends across cohorts, get AI-suggested actions, and close the loop by linking responses to Goals — so the next pulse measures whether your action moved the needle.",
  usps: [
    "Three-tier anonymity: identified, pseudonymous, anonymous",
    "Trend hero shows 6-pulse history per cohort",
    "Action loop turns findings into linked Goals",
    "Manager view with n≥5 anonymity gate",
    "Cross-stage correlation with exit interviews (P2)",
    "TAFEP / FWA-aware suggested actions",
  ],
  features: [
    {
      title: "Templates",
      description:
        "Gallup Q12 paraphrased + monthly pulse ship out of the box. Add custom templates with Likert, free-text, multi-select, and eNPS questions.",
    },
    {
      title: "Cohorts",
      description:
        "Target all staff, by department, or new joiners. Add specific employees ad-hoc.",
    },
    {
      title: "Action Loop",
      description:
        "When a cohort scores low, accept a suggested action and one-click create a linked Goal. Next pulse measures the delta.",
    },
    {
      title: "Anonymity Tiers",
      description:
        "Identified (names visible), pseudonymous (HMAC trail for cross-survey trends), or fully anonymous. n≥5 gate on aggregations.",
    },
  ],
};

export default function EngagementLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
