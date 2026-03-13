"use client";

import clsx from "clsx";
import { CheckCircle, AlertTriangle, AlertOctagon } from "lucide-react";

export type RiskTierLevel = "green" | "amber" | "red";

export interface RiskTierBadgeProps {
  tier: RiskTierLevel;
  className?: string;
}

const tierConfig: Record<
  RiskTierLevel,
  {
    icon: typeof CheckCircle;
    label: string;
    classes: string;
  }
> = {
  green: {
    icon: CheckCircle,
    label: "Low Risk",
    classes:
      "bg-[var(--color-risk-green-bg)] text-[var(--color-risk-green)] border-[var(--color-risk-green-border)]",
  },
  amber: {
    icon: AlertTriangle,
    label: "Medium Risk",
    classes:
      "bg-[var(--color-risk-amber-bg)] text-[var(--color-risk-amber)] border-[var(--color-risk-amber-border)]",
  },
  red: {
    icon: AlertOctagon,
    label: "High Risk",
    classes:
      "bg-[var(--color-risk-red-bg)] text-[var(--color-risk-red)] border-[var(--color-risk-red-border)]",
  },
};

export function RiskTierBadge({ tier, className }: RiskTierBadgeProps) {
  const { icon: Icon, label, classes } = tierConfig[tier];

  return (
    <span
      role="status"
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full",
        "px-3 py-1 text-sm font-medium",
        "border",
        classes,
        className,
      )}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      {label}
    </span>
  );
}
