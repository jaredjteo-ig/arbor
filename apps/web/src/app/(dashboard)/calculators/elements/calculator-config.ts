/* ── Calculator Hub Configuration ─────────────────────────── */
/* Defines the list of available calculators, their metadata,  */
/* and the route slug for each.                                */

import type { LucideIcon } from "lucide-react";
import {
  Building2,
  Users,
  CalendarDays,
  Clock,
  Timer,
  Briefcase,
  Receipt,
} from "lucide-react";

export interface CalculatorMeta {
  slug: string;
  name: string;
  description: string;
  icon: LucideIcon;
}

export const CALCULATORS: CalculatorMeta[] = [
  {
    slug: "cpf",
    name: "CPF Contributions",
    description:
      "Calculate employer and employee CPF contributions by age and citizenship status.",
    icon: Building2,
  },
  {
    slug: "quota-levy",
    name: "Quota & Levy",
    description:
      "Check foreign worker quota ratios and estimate monthly levies by sector.",
    icon: Users,
  },
  {
    slug: "leave",
    name: "Leave Entitlement",
    description: "Find statutory leave entitlements based on years of service.",
    icon: CalendarDays,
  },
  {
    slug: "notice-period",
    name: "Notice Period",
    description: "Determine notice period and salary in lieu of notice.",
    icon: Clock,
  },
  {
    slug: "overtime",
    name: "Overtime Pay",
    description: "Check Part IV eligibility and calculate overtime pay rates.",
    icon: Timer,
  },
  {
    slug: "retrenchment",
    name: "Retrenchment Benefit",
    description: "Estimate retrenchment benefits based on market norms.",
    icon: Briefcase,
  },
  {
    slug: "cost-to-company",
    name: "Cost-to-Company",
    description:
      "See the full employment cost breakdown including CPF, levies, and SDL.",
    icon: Receipt,
  },
];

/** Look up a calculator by its URL slug. */
export function getCalculatorBySlug(slug: string): CalculatorMeta | undefined {
  return CALCULATORS.find((c) => c.slug === slug);
}
