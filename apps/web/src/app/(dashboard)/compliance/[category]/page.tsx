"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import {
  Shield,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowLeft,
  MessageSquare,
} from "lucide-react";
import {
  AppCard,
  RiskTierBadge,
  LoadingState,
  ErrorState,
} from "@/components/design-system";
import type { RiskTierLevel } from "@/components/design-system";
import type { ComplianceGap, ComplianceDomainStatus } from "@/types/api";
import { complianceApi } from "@/services/api/compliance";
import { useAuth } from "@/contexts/AuthContext";

/* ── Domain slug mapping ─────────────────────────────────── */

const DOMAIN_MAP: Record<string, string> = {
  "employment-act": "employment_act",
  cpf: "cpf",
  "foreign-manpower": "foreign_manpower",
  tax: "tax",
  wsh: "wsh",
  "fair-employment": "fair_employment",
};

const DOMAIN_LABELS: Record<string, string> = {
  employment_act: "Employment Act",
  cpf: "Central Provident Fund (CPF)",
  foreign_manpower: "Foreign Manpower (EFMA)",
  tax: "Tax / IRAS",
  wsh: "Workplace Safety and Health (WSH)",
  fair_employment: "Fair Employment (TAFEP / WFA)",
};

const DOMAIN_DESCRIPTIONS: Record<string, string> = {
  employment_act:
    "Covers employment contracts, key employment terms, salary payments, leave entitlements, overtime provisions, and termination procedures under the Employment Act.",
  cpf: "Covers employer and employee Central Provident Fund contribution requirements, rates, and compliance obligations.",
  foreign_manpower:
    "Covers work pass requirements, quota limits, levy obligations, and compliance requirements for employing foreign workers under the Employment of Foreign Manpower Act.",
  tax: "Covers income tax withholding, IRAS filing obligations, and tax-related employment compliance.",
  wsh: "Covers workplace safety policies, risk assessments, incident reporting, and compliance with the Workplace Safety and Health Act.",
  fair_employment:
    "Covers fair hiring practices, grievance handling, flexible work arrangements, and compliance with Tripartite Guidelines.",
};

const ADVISORY_QUESTIONS: Record<string, string[]> = {
  employment_act: [
    "What are the KET requirements for my employees?",
    "How do I calculate overtime pay correctly?",
    "What leave entitlements must I provide?",
  ],
  cpf: [
    "How do I calculate CPF contributions?",
    "What are the CPF rates for different age groups?",
    "What are my CPF obligations for PR employees?",
  ],
  foreign_manpower: [
    "What are the foreign worker quota limits for my sector?",
    "What work passes do my foreign employees need?",
    "How do I calculate the foreign worker levy?",
  ],
  tax: [
    "What are my tax withholding obligations?",
    "How do I handle tax clearance for departing employees?",
    "What benefits are taxable for employees?",
  ],
  wsh: [
    "What workplace safety policies do I need?",
    "How do I conduct a workplace risk assessment?",
    "What are the incident reporting requirements?",
  ],
  fair_employment: [
    "What are the fair hiring requirements?",
    "How do I set up a grievance handling process?",
    "What is required for a flexible work arrangement policy?",
  ],
};

/* ── Severity styling ────────────────────────────────────── */

const severityColor: Record<string, string> = {
  critical: "var(--color-risk-red)",
  high: "var(--color-risk-amber)",
  medium: "var(--color-primary)",
  low: "var(--color-gray-400)",
};

const severityBg: Record<string, string> = {
  critical: "var(--color-risk-red-bg)",
  high: "var(--color-risk-amber-bg)",
  medium: "var(--color-primary-bg)",
  low: "var(--color-gray-100)",
};

/* ── Page Component ──────────────────────────────────────── */

interface ComplianceCategoryPageProps {
  params: Promise<{ category: string }>;
}

export default function ComplianceCategoryPage({
  params,
}: ComplianceCategoryPageProps) {
  const { category } = use(params);
  const { user } = useAuth();

  const [domainStatus, setDomainStatus] =
    useState<ComplianceDomainStatus | null>(null);
  const [gaps, setGaps] = useState<ComplianceGap[]>([]);
  const [overallStatus, setOverallStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const domainKey = DOMAIN_MAP[category] || category.replace(/-/g, "_");
  const displayName = DOMAIN_LABELS[domainKey] || formatDisplayName(category);
  const description =
    DOMAIN_DESCRIPTIONS[domainKey] ||
    `Compliance status and requirements for the ${displayName.toLowerCase()} domain.`;
  const advisoryQuestions = ADVISORY_QUESTIONS[domainKey] || [];

  useEffect(() => {
    let cancelled = false;

    async function loadComplianceData() {
      setLoading(true);
      setError(null);

      const companyId = user?.company_id;
      if (!companyId) {
        setLoading(false);
        setError(
          "No company profile found. Please complete your company setup first.",
        );
        return;
      }

      try {
        const [statusRes, gapRes] = await Promise.all([
          complianceApi.status(companyId),
          complianceApi.gapAnalysis({ company_id: companyId }),
        ]);

        if (cancelled) return;

        // Extract domain-specific status
        const domains = statusRes.domains || {};
        const thisDomainStatus = domains[domainKey] || null;
        setDomainStatus(thisDomainStatus);
        setOverallStatus(statusRes.overall_status);

        // Filter gaps for this domain
        const domainGaps = (gapRes.gaps || []).filter(
          (g: ComplianceGap) => g.domain === domainKey,
        );
        setGaps(domainGaps);
      } catch (err) {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : "Failed to load compliance data";
        setError(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadComplianceData();
    return () => {
      cancelled = true;
    };
  }, [user?.company_id, domainKey]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <LoadingState variant="card" count={3} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <ErrorState
          title="Unable to load compliance data"
          description={error}
        />
      </div>
    );
  }

  const statusLabel = domainStatus?.status || "unknown";
  const provisionsCount = domainStatus?.provisions_count ?? 0;
  const riskTier: RiskTierLevel =
    statusLabel === "covered"
      ? "green"
      : statusLabel === "sparse"
        ? "amber"
        : "red";

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back link */}
      <Link
        href="/compliance"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-gray-500)] hover:text-[var(--color-primary)] transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Compliance Check
      </Link>

      {/* Header */}
      <div className="flex items-center gap-3">
        <Shield
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            {displayName}
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            {description}
          </p>
        </div>
      </div>

      {/* Status overview */}
      <AppCard variant="elevated">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-[var(--color-gray-500)]">
              Domain Status
            </p>
            <div className="flex items-center gap-3 mt-1">
              <RiskTierBadge tier={riskTier} />
              <span className="text-sm text-[var(--color-gray-600)]">
                {provisionsCount} provision
                {provisionsCount !== 1 ? "s" : ""} in knowledge base
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {statusLabel === "covered" && (
              <CheckCircle2 className="h-8 w-8 text-[var(--color-risk-green)]" />
            )}
            {statusLabel === "sparse" && (
              <AlertTriangle className="h-8 w-8 text-[var(--color-risk-amber)]" />
            )}
            {statusLabel === "missing" && (
              <XCircle className="h-8 w-8 text-[var(--color-risk-red)]" />
            )}
          </div>
        </div>

        {overallStatus && (
          <div className="mt-3 pt-3 border-t border-[var(--color-gray-200)]">
            <p className="text-xs text-[var(--color-gray-500)]">
              Overall company compliance:{" "}
              <span className="font-medium text-[var(--color-gray-700)]">
                {overallStatus.replace(/_/g, " ")}
              </span>
            </p>
          </div>
        )}
      </AppCard>

      {/* Gaps and findings */}
      {gaps.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
            Findings ({gaps.length})
          </h2>
          {gaps.map((gap, idx) => (
            <AppCard key={idx} variant="standard">
              <div className="flex items-start gap-3">
                <div
                  className="px-2 py-0.5 rounded text-xs font-semibold uppercase shrink-0"
                  style={{
                    backgroundColor:
                      severityBg[gap.severity] || severityBg.medium,
                    color: severityColor[gap.severity] || severityColor.medium,
                  }}
                >
                  {gap.severity}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[var(--color-gray-900)]">
                    {gap.reason}
                  </p>
                  <p className="text-xs text-[var(--color-gray-600)] mt-1">
                    {gap.remediation}
                  </p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-xs text-[var(--color-gray-400)]">
                      {gap.provisions_found} provision
                      {gap.provisions_found !== 1 ? "s" : ""} found
                    </span>
                  </div>
                </div>
              </div>
            </AppCard>
          ))}
        </div>
      ) : (
        <AppCard variant="standard">
          <div className="flex items-center gap-3 py-2">
            <CheckCircle2 className="h-5 w-5 text-[var(--color-risk-green)]" />
            <p className="text-sm text-[var(--color-gray-700)]">
              No compliance gaps found for {displayName}. Your knowledge base
              coverage for this domain is adequate.
            </p>
          </div>
        </AppCard>
      )}

      {/* Advisory questions */}
      {advisoryQuestions.length > 0 && (
        <AppCard variant="standard">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <MessageSquare
                className="h-4 w-4 text-[var(--color-gray-500)]"
                aria-hidden="true"
              />
              <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
                Related Advisory Questions
              </h3>
            </div>
            <p className="text-xs text-[var(--color-gray-500)]">
              Ask AITE about {displayName.toLowerCase()} compliance:
            </p>
            <div className="flex flex-wrap gap-2">
              {advisoryQuestions.map((q) => (
                <Link
                  key={q}
                  href={`/advisory?q=${encodeURIComponent(q)}`}
                  className="inline-flex items-center whitespace-nowrap rounded-full px-3 py-1.5 text-sm min-h-[36px] border border-[var(--color-gray-300)] bg-[var(--color-surface-card)] text-[var(--color-gray-700)] hover:bg-[var(--color-gray-100)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] transition-colors"
                >
                  {q}
                </Link>
              ))}
            </div>
          </div>
        </AppCard>
      )}
    </div>
  );
}

/* ── Helpers ──────────────────────────────────────────────── */

function formatDisplayName(slug: string): string {
  return slug
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
