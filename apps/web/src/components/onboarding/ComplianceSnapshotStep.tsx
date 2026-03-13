"use client";

import { useState, useEffect } from "react";
import { ShieldCheck, AlertTriangle, AlertOctagon } from "lucide-react";
import { AppButton } from "@/components/design-system/AppButton";
import { AppCard } from "@/components/design-system/AppCard";
import { RiskTierBadge } from "@/components/design-system/RiskTierBadge";
import { LoadingState } from "@/components/design-system/LoadingState";
import type { CompanyProfileData } from "./CompanyProfileStep";
import type { RiskTierLevel } from "@/components/design-system/RiskTierBadge";

interface ComplianceInsight {
  id: string;
  title: string;
  description: string;
  tier: RiskTierLevel;
  category: string;
}

interface ComplianceSnapshotStepProps {
  profileData: CompanyProfileData;
  onNext: () => void;
  onBack: () => void;
}

function generateInsights(data: CompanyProfileData): ComplianceInsight[] {
  const insights: ComplianceInsight[] = [];
  const totalForeign = data.headcountEP + data.headcountSP + data.headcountWP;
  const totalLocal = data.headcountLocal + data.headcountPR;

  // Insight 1: Foreign worker quota check
  if (
    data.sector &&
    ["services", "manufacturing", "construction", "process", "marine"].includes(
      data.sector,
    )
  ) {
    const drcLimits: Record<string, number> = {
      services: 0.35,
      manufacturing: 0.6,
      construction: 0.875,
      process: 0.6,
      marine: 0.6,
    };
    const drc = drcLimits[data.sector] ?? 0.35;
    const total = totalLocal + totalForeign;
    const ratio = total > 0 ? totalForeign / total : 0;

    if (ratio > drc * 0.9 && ratio <= drc) {
      insights.push({
        id: "drc-approaching",
        title: "Approaching Foreign Worker Ceiling",
        description: `Your foreign worker ratio (${(ratio * 100).toFixed(0)}%) is close to the ${data.sector} sector DRC limit of ${(drc * 100).toFixed(0)}%. Plan local hiring before adding foreign workers.`,
        tier: "amber",
        category: "Foreign Manpower",
      });
    } else if (ratio > drc) {
      insights.push({
        id: "drc-exceeded",
        title: "Foreign Worker Quota Exceeded",
        description: `Your foreign worker ratio (${(ratio * 100).toFixed(0)}%) exceeds the ${data.sector} sector DRC limit of ${(drc * 100).toFixed(0)}%. You cannot hire additional foreign workers.`,
        tier: "red",
        category: "Foreign Manpower",
      });
    } else if (totalForeign > 0) {
      insights.push({
        id: "drc-ok",
        title: "Foreign Worker Quota Within Limits",
        description: `Your foreign worker ratio (${(ratio * 100).toFixed(0)}%) is within the ${(drc * 100).toFixed(0)}% DRC limit for ${data.sector} sector.`,
        tier: "green",
        category: "Foreign Manpower",
      });
    }
  }

  // Insight 2: CPF obligations
  if (data.totalHeadcount > 0 || totalLocal > 0) {
    insights.push({
      id: "cpf-obligations",
      title: "CPF Contributions Required",
      description:
        "As an employer, you must contribute CPF for all Singapore Citizen and PR employees. Use our CPF calculator to check exact amounts by age band.",
      tier: "green",
      category: "CPF",
    });
  }

  // Insight 3: Employment Act coverage
  if (data.salaryRangeMin > 0 && data.salaryRangeMin <= 2600) {
    insights.push({
      id: "ea-part-iv",
      title: "Part IV Protections Apply",
      description:
        "Some employees earn $2,600 or below — they are covered by Part IV of the Employment Act (working hours, overtime, rest days). Ensure overtime is tracked and paid at 1.5x.",
      tier: "amber",
      category: "Employment Act",
    });
  } else {
    insights.push({
      id: "ea-general",
      title: "Employment Act Applies",
      description:
        "All employees (except domestic workers, seafarers, and statutory board employees) are covered by the Employment Act regardless of salary.",
      tier: "green",
      category: "Employment Act",
    });
  }

  // Insight 4: TAFEP / Fair employment
  insights.push({
    id: "tafep-fcf",
    title: "Fair Consideration Framework",
    description:
      "Before hiring foreign workers on EP or S Pass, you must advertise the position on MyCareersFuture for at least 14 consecutive days (unless exempt).",
    tier: "green",
    category: "Fair Employment",
  });

  // Insight 5: Levy obligations
  if (data.headcountSP > 0 || data.headcountWP > 0) {
    const spLevy = data.headcountSP * 550;
    const wpLevy = data.headcountWP * 450;
    const totalLevy = spLevy + wpLevy;
    insights.push({
      id: "levy-estimate",
      title: `Estimated Monthly Levy: $${totalLevy.toLocaleString()}`,
      description: `Based on ${data.headcountSP} S Pass ($550/month each) and ${data.headcountWP} WP ($450/month each) holders. Use our quota calculator for exact figures.`,
      tier: totalLevy > 5000 ? "amber" : "green",
      category: "Foreign Manpower",
    });
  }

  return insights.slice(0, 5);
}

function OverallGauge({ insights }: { insights: ComplianceInsight[] }) {
  const hasRed = insights.some((i) => i.tier === "red");
  const hasAmber = insights.some((i) => i.tier === "amber");
  const overallTier: RiskTierLevel = hasRed
    ? "red"
    : hasAmber
      ? "amber"
      : "green";

  const label = hasRed
    ? "Action Required"
    : hasAmber
      ? "Some Items Need Attention"
      : "Looking Good";

  return (
    <div className="flex items-center justify-between p-4 rounded-xl bg-[var(--color-surface-card)] border border-[var(--color-gray-200)]">
      <div>
        <p className="text-sm font-medium text-[var(--color-gray-700)]">
          Overall Compliance Status
        </p>
        <p className="text-xs text-[var(--color-gray-500)] mt-0.5">{label}</p>
      </div>
      <RiskTierBadge tier={overallTier} />
    </div>
  );
}

export function ComplianceSnapshotStep({
  profileData,
  onNext,
  onBack,
}: ComplianceSnapshotStepProps) {
  const [loading, setLoading] = useState(true);
  const [insights, setInsights] = useState<ComplianceInsight[]>([]);

  useEffect(() => {
    // Simulate brief analysis delay
    const timer = setTimeout(() => {
      setInsights(generateInsights(profileData));
      setLoading(false);
    }, 1200);
    return () => clearTimeout(timer);
  }, [profileData]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <LoadingState variant="card" count={3} />
        <p className="mt-4 text-sm text-[var(--color-gray-500)]">
          Analysing your company profile...
        </p>
      </div>
    );
  }

  const tierIcons = {
    green: ShieldCheck,
    amber: AlertTriangle,
    red: AlertOctagon,
  };

  return (
    <div className="max-w-lg mx-auto">
      <h2 className="text-xl font-bold text-[var(--color-gray-900)] mb-1">
        Compliance Snapshot
      </h2>
      <p className="text-sm text-[var(--color-gray-500)] mb-6">
        Here&apos;s a quick overview based on your company profile. Ask AITE for
        detailed guidance on any of these topics.
      </p>

      <OverallGauge insights={insights} />

      <div className="mt-5 space-y-3">
        {insights.map((insight) => {
          const Icon = tierIcons[insight.tier];
          return (
            <AppCard key={insight.id} variant="flat">
              <div className="flex items-start gap-3">
                <div
                  className={`shrink-0 mt-0.5 ${
                    insight.tier === "red"
                      ? "text-[var(--color-risk-red)]"
                      : insight.tier === "amber"
                        ? "text-[var(--color-risk-amber)]"
                        : "text-[var(--color-risk-green)]"
                  }`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
                      {insight.title}
                    </h3>
                    <RiskTierBadge tier={insight.tier} className="text-xs" />
                  </div>
                  <p className="text-xs text-[var(--color-gray-600)] leading-relaxed">
                    {insight.description}
                  </p>
                  <span className="inline-block mt-1.5 text-xs text-[var(--color-gray-400)]">
                    {insight.category}
                  </span>
                </div>
              </div>
            </AppCard>
          );
        })}
      </div>

      <div className="flex gap-3 mt-8">
        <AppButton variant="outlined" onClick={onBack}>
          Back
        </AppButton>
        <AppButton onClick={onNext} className="flex-1">
          Ask Your First Question
        </AppButton>
      </div>
    </div>
  );
}
