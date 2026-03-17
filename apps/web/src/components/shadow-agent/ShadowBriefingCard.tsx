"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Sun,
  Sunrise,
  Moon,
  ShieldCheck,
  Calculator,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { AppCard } from "@/components/design-system";
import type { ShadowInsight } from "./ShadowMargin";

/* -- Types -------------------------------------------------------- */

interface ShadowBriefingCardProps {
  userName?: string | null;
  insights: ShadowInsight[];
  isLoading?: boolean;
  hasCompanyProfile: boolean;
}

/* -- Time-of-day helpers ------------------------------------------ */

type TimeOfDay = "morning" | "afternoon" | "evening";

function getTimeOfDay(): TimeOfDay {
  const hour = new Date().getHours();
  if (hour < 12) return "morning";
  if (hour < 18) return "afternoon";
  return "evening";
}

const GREETINGS: Record<TimeOfDay, string> = {
  morning: "Good morning",
  afternoon: "Good afternoon",
  evening: "Good evening",
};

const TIME_ICONS: Record<TimeOfDay, typeof Sun> = {
  morning: Sunrise,
  afternoon: Sun,
  evening: Moon,
};

/* -- Quick action suggestions ------------------------------------- */

interface QuickAction {
  label: string;
  icon: typeof ShieldCheck;
  href: string;
}

function getContextualActions(
  timeOfDay: TimeOfDay,
  hasCompanyProfile: boolean,
  highSeverityCount: number,
): QuickAction[] {
  const actions: QuickAction[] = [];

  // Always-relevant actions based on context
  if (highSeverityCount > 0) {
    actions.push({
      label: "Review compliance alerts",
      icon: AlertTriangle,
      href: "/compliance",
    });
  }

  if (!hasCompanyProfile) {
    actions.push({
      label: "Set up company profile",
      icon: ShieldCheck,
      href: "/onboarding",
    });
  }

  // Time-contextual suggestions
  if (timeOfDay === "morning") {
    actions.push({
      label: "Run CPF calculations",
      icon: Calculator,
      href: "/calculators",
    });
    if (hasCompanyProfile) {
      actions.push({
        label: "Check compliance status",
        icon: ShieldCheck,
        href: "/compliance",
      });
    }
  } else if (timeOfDay === "afternoon") {
    actions.push({
      label: "Generate documents",
      icon: FileText,
      href: "/documents",
    });
    if (hasCompanyProfile) {
      actions.push({
        label: "Review compliance",
        icon: ShieldCheck,
        href: "/compliance",
      });
    }
  } else {
    // Evening — lighter tasks
    actions.push({
      label: "Prepare for tomorrow",
      icon: FileText,
      href: "/documents",
    });
  }

  // Deduplicate by href
  const seen = new Set<string>();
  return actions
    .filter((a) => {
      if (seen.has(a.href)) return false;
      seen.add(a.href);
      return true;
    })
    .slice(0, 3);
}

/* -- Component ---------------------------------------------------- */

/**
 * Shadow Briefing Card (T124) -- time-aware greeting with contextual
 * compliance summary and quick action suggestions for returning users.
 */
export function ShadowBriefingCard({
  userName,
  insights,
  isLoading = false,
  hasCompanyProfile,
}: ShadowBriefingCardProps) {
  const router = useRouter();
  const timeOfDay = useMemo(() => getTimeOfDay(), []);
  const TimeIcon = TIME_ICONS[timeOfDay];
  const greeting = GREETINGS[timeOfDay];

  const highSeverityCount = insights.filter(
    (i) => i.severity === "high",
  ).length;

  const complianceInsights = insights.filter(
    (i) => i.type === "compliance_gap",
  );
  const deadlineInsights = insights.filter((i) => i.type === "deadline");

  const quickActions = useMemo(
    () => getContextualActions(timeOfDay, hasCompanyProfile, highSeverityCount),
    [timeOfDay, hasCompanyProfile, highSeverityCount],
  );

  // Loading skeleton
  if (isLoading) {
    return (
      <AppCard variant="flat">
        <div className="animate-pulse space-y-3">
          <div className="h-5 w-48 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-64 bg-[var(--color-gray-100)] rounded" />
          <div className="h-4 w-40 bg-[var(--color-gray-100)] rounded" />
        </div>
      </AppCard>
    );
  }

  const firstName = userName?.split(" ")[0];

  return (
    <AppCard variant="flat" className="relative overflow-hidden">
      {/* Subtle shadow mark in corner */}
      <div className="absolute top-3 right-3 opacity-10" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 18 18" fill="none">
          <circle cx="7" cy="9" r="5" fill="var(--color-primary)" />
          <ellipse
            cx="12"
            cy="9"
            rx="4"
            ry="3.5"
            fill="var(--color-primary)"
            opacity="0.4"
          />
        </svg>
      </div>

      <div className="space-y-3">
        {/* Greeting */}
        <div className="flex items-center gap-2">
          <TimeIcon
            className="h-5 w-5 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
            {greeting}
            {firstName ? `, ${firstName}` : ""}
          </h2>
        </div>

        {/* Compliance summary — only if there are insights */}
        {(complianceInsights.length > 0 || deadlineInsights.length > 0) && (
          <div className="text-sm text-[var(--color-gray-600)] space-y-1">
            {complianceInsights.length > 0 && (
              <p>
                {complianceInsights.length} compliance{" "}
                {complianceInsights.length === 1 ? "area needs" : "areas need"}{" "}
                attention.
              </p>
            )}
            {deadlineInsights.length > 0 && (
              <p>
                {deadlineInsights.length} upcoming{" "}
                {deadlineInsights.length === 1 ? "deadline" : "deadlines"} to
                watch.
              </p>
            )}
          </div>
        )}

        {/* No insights — show encouraging message */}
        {complianceInsights.length === 0 &&
          deadlineInsights.length === 0 &&
          hasCompanyProfile && (
            <p className="text-sm text-[var(--color-gray-600)]">
              No compliance alerts right now. Everything looks good.
            </p>
          )}

        {/* Quick action suggestions */}
        {quickActions.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.href}
                  type="button"
                  onClick={() => router.push(action.href)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:bg-[var(--color-gray-200)] hover:text-[var(--color-gray-900)] transition-colors"
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {action.label}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </AppCard>
  );
}
