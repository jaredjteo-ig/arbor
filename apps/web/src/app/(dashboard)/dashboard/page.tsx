"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  AppCard,
  AppButton,
  AlertBanner,
  RiskTierBadge,
} from "@/components/design-system";
import type { RiskTierLevel } from "@/components/design-system";
import {
  ShadowBriefingCard,
  useShadowContext,
} from "@/components/shadow-agent";
import { useAuth } from "@/contexts/AuthContext";
import { HRISModuleGrid } from "@/components/management/HRISModuleGrid";
import { CompanySetupModal } from "@/components/company/CompanySetupModal";
import { complianceApi } from "@/services/api/compliance";
import { adminApi } from "@/services/api/admin";
import type {
  ComplianceStatusResponse,
  PlatformMetricsResponse,
} from "@/types/api";
import {
  ShieldCheck,
  ClipboardCheck,
  Calendar,
  MessageSquare,
  Calculator,
  FileText,
  Scan,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Circle,
  Building2,
  Compass,
  Sparkles,
  BookOpen,
  Scale,
} from "lucide-react";

/* ── Types ──────────────────────────────────────────────────── */

interface MetricCard {
  label: string;
  value: string;
  icon: typeof ShieldCheck;
  subtext?: string;
}

interface ActionItem {
  id: string;
  title: string;
  tier: RiskTierLevel;
  dueDate?: string;
}

/* ── Domain labels ─────────────────────────────────────────── */

const DOMAIN_LABELS: Record<string, string> = {
  employment_act: "Employment Act",
  cpf: "Central Provident Fund (CPF)",
  foreign_manpower: "Foreign Manpower (EFMA)",
  tax: "Tax / IRAS",
  wsh: "Workplace Safety and Health (WSH)",
};

/* ── Risk tier mapping ─────────────────────────────────────── */

function domainStatusToTier(status: string): RiskTierLevel {
  if (status === "covered") return "green";
  if (status === "sparse") return "amber";
  return "red";
}

/* ── Loading skeleton ──────────────────────────────────────── */

function MetricsSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {[...Array(3)].map((_, i) => (
        <AppCard key={i} variant="flat">
          <div className="animate-pulse">
            <div className="h-3 w-24 bg-[var(--color-gray-200)] rounded mb-3" />
            <div className="h-7 w-16 bg-[var(--color-gray-200)] rounded mb-2" />
            <div className="h-3 w-32 bg-[var(--color-gray-100)] rounded" />
          </div>
        </AppCard>
      ))}
    </div>
  );
}

function ListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {[...Array(rows)].map((_, i) => (
        <div
          key={i}
          className="p-3 rounded-lg bg-[var(--color-surface-card)] border border-[var(--color-gray-200)] animate-pulse"
        >
          <div className="h-4 w-3/4 bg-[var(--color-gray-200)] rounded mb-2" />
          <div className="h-3 w-1/4 bg-[var(--color-gray-100)] rounded" />
        </div>
      ))}
    </div>
  );
}

/* ── Error banner ──────────────────────────────────────────── */

function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
      <AlertCircle className="h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

/* ── Quick Action Buttons ──────────────────────────────────── */

function QuickActions() {
  const router = useRouter();

  const actions = [
    {
      label: "Ask a question",
      icon: MessageSquare,
      href: "/advisory",
      primary: true,
    },
    { label: "Run a calculation", icon: Calculator, href: "/calculators" },
    { label: "Generate a document", icon: FileText, href: "/documents" },
    { label: "Compliance check", icon: Scan, href: "/compliance" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {actions.map((action) => {
        const Icon = action.icon;
        return (
          <button
            key={action.label}
            type="button"
            onClick={() => router.push(action.href)}
            className={`flex flex-col items-center gap-2 rounded-xl p-4 text-center transition-colors min-h-[88px] ${
              action.primary
                ? "bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-light)]"
                : "bg-[var(--color-surface-card)] border border-[var(--color-gray-200)] text-[var(--color-gray-700)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary)]"
            }`}
          >
            <Icon className="h-5 w-5" />
            <span className="text-sm font-medium">{action.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/* ── Getting Started Step Card ─────────────────────────────── */

function GettingStartedStep({
  step,
  title,
  description,
  href,
  icon: Icon,
  completed,
}: {
  step: number;
  title: string;
  description: string;
  href: string;
  icon: typeof Building2;
  completed: boolean;
}) {
  const router = useRouter();

  return (
    <button
      type="button"
      onClick={() => router.push(href)}
      className="text-left rounded-xl border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-4 transition-colors hover:border-[var(--color-primary)] group"
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 mt-0.5">
          {completed ? (
            <CheckCircle2 className="h-5 w-5 text-[var(--color-success)]" />
          ) : (
            <Circle className="h-5 w-5 text-[var(--color-gray-300)]" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
              Step {step}
            </span>
          </div>
          <p className="text-sm font-medium text-[var(--color-gray-900)] group-hover:text-[var(--color-primary)] transition-colors">
            {title}
          </p>
          <p className="text-xs text-[var(--color-gray-500)] mt-1">
            {description}
          </p>
        </div>
        <Icon className="h-4 w-4 text-[var(--color-gray-400)] shrink-0 mt-1" />
      </div>
    </button>
  );
}

/* ── Compliance Preview Card ──────────────────────────────── */

const SAMPLE_DOMAINS: {
  name: string;
  tier: RiskTierLevel;
}[] = [
  { name: "Employment Act", tier: "green" },
  { name: "Central Provident Fund (CPF)", tier: "green" },
  { name: "Foreign Manpower (EFMA)", tier: "amber" },
  { name: "Workplace Safety & Health (WSH)", tier: "red" },
  { name: "Tax / IRAS", tier: "amber" },
];

function CompliancePreviewCard() {
  return (
    <AppCard variant="flat" className="relative overflow-hidden">
      {/* Example badge */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="h-4 w-4 text-[var(--color-primary)]" />
          <span className="text-sm font-semibold text-[var(--color-gray-900)]">
            Compliance at a Glance
          </span>
        </div>
        <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)] bg-[var(--color-gray-100)] rounded-full px-2 py-0.5">
          Example
        </span>
      </div>

      <div className="space-y-2">
        {SAMPLE_DOMAINS.map((domain) => (
          <div
            key={domain.name}
            className="flex items-center justify-between gap-2 py-1.5"
          >
            <span className="text-sm text-[var(--color-gray-700)]">
              {domain.name}
            </span>
            <RiskTierBadge tier={domain.tier} className="text-xs" />
          </div>
        ))}
      </div>

      <p className="text-xs text-[var(--color-gray-500)] mt-4 italic">
        Set up your profile for your actual compliance score
      </p>
    </AppCard>
  );
}

/* ── Advisory Preview Card ────────────────────────────────── */

function AdvisoryPreviewCard() {
  return (
    <AppCard variant="flat" className="relative overflow-hidden">
      {/* Example badge */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex items-center gap-1.5">
          <Sparkles className="h-4 w-4 text-[var(--color-primary)]" />
          <span className="text-sm font-semibold text-[var(--color-gray-900)]">
            AI-Powered Advisory
          </span>
        </div>
        <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)] bg-[var(--color-gray-100)] rounded-full px-2 py-0.5">
          Example
        </span>
      </div>

      {/* Sample question */}
      <div className="rounded-lg bg-[var(--color-gray-100)] p-3 mb-3">
        <p className="text-xs font-medium text-[var(--color-gray-500)] mb-1">
          Question
        </p>
        <p className="text-sm text-[var(--color-gray-800)]">
          What are the notice period requirements for employees under the
          Employment Act?
        </p>
      </div>

      {/* Sample answer */}
      <div className="rounded-lg border border-[var(--color-gray-200)] p-3">
        <p className="text-xs font-medium text-[var(--color-gray-500)] mb-1">
          Answer
        </p>
        <p className="text-sm text-[var(--color-gray-700)] leading-relaxed">
          Under Part II of the Employment Act, notice periods depend on the
          length of service. For employees with less than 26 weeks, the notice
          period is 1 day...
        </p>

        {/* Source citations */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--color-primary)] bg-[var(--color-primary-bg)] rounded-full px-2.5 py-0.5">
            <BookOpen className="h-3 w-3" />
            EA Part II
          </span>
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--color-primary)] bg-[var(--color-primary-bg)] rounded-full px-2.5 py-0.5">
            <Scale className="h-3 w-3" />
            Section 10
          </span>
        </div>
      </div>

      <p className="text-xs text-[var(--color-gray-500)] mt-4 italic">
        Try asking your own question in the Advisory section
      </p>
    </AppCard>
  );
}

/* ── Company Setup CTA ────────────────────────────────────── */

function CompanySetupCTA() {
  const [showModal, setShowModal] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setShowModal(true)}
        className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all text-sm shadow-lg shadow-blue-500/20 shrink-0"
      >
        <Building2 className="w-4 h-4" />
        Set Up Company
      </button>
      <CompanySetupModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
      />
    </>
  );
}

/* ── Dashboard Page ────────────────────────────────────────── */

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const firstName = user?.name?.split(" ")[0] ?? null;

  /* ── State ───────────────────────────────────────────────── */
  const [complianceData, setComplianceData] =
    useState<ComplianceStatusResponse | null>(null);
  const [metricsData, setMetricsData] =
    useState<PlatformMetricsResponse | null>(null);
  const [complianceLoading, setComplianceLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [complianceError, setComplianceError] = useState<string | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);

  /* ── Fetch data ──────────────────────────────────────────── */
  useEffect(() => {
    if (!user?.company_id) {
      setComplianceLoading(false);
      setMetricsLoading(false);
      return;
    }

    complianceApi
      .status(user.company_id)
      .then((data) => setComplianceData(data))
      .catch(() =>
        setComplianceError("Unable to load compliance data right now."),
      )
      .finally(() => setComplianceLoading(false));

    adminApi
      .metrics()
      .then((data) => setMetricsData(data))
      .catch(() =>
        setMetricsError("Unable to load platform metrics right now."),
      )
      .finally(() => setMetricsLoading(false));
  }, [user?.company_id]);

  /* ── Derive metric cards from real data ──────────────────── */
  const metrics: MetricCard[] = [];
  if (complianceData) {
    const domainEntries = Object.entries(complianceData.domains);
    const coveredCount = domainEntries.filter(
      ([, d]) => d.status === "covered",
    ).length;
    const totalDomains = domainEntries.length;
    const scorePercent =
      totalDomains > 0 ? Math.round((coveredCount / totalDomains) * 100) : 0;
    const needsAttention = domainEntries.filter(
      ([, d]) => d.status !== "covered",
    ).length;

    metrics.push({
      label: "Compliance Score",
      value: `${scorePercent}/100`,
      icon: ShieldCheck,
      subtext:
        needsAttention > 0
          ? `${needsAttention} domain${needsAttention > 1 ? "s" : ""} need${needsAttention === 1 ? "s" : ""} attention`
          : "All domains covered",
    });
  }

  if (complianceData) {
    const pendingActions = Object.entries(complianceData.domains).filter(
      ([, d]) => d.status !== "covered",
    );
    const criticalCount = pendingActions.filter(
      ([, d]) => d.status === "missing",
    ).length;

    metrics.push({
      label: "Pending Actions",
      value: String(pendingActions.length),
      icon: ClipboardCheck,
      subtext:
        criticalCount > 0 ? `${criticalCount} critical` : "No critical items",
    });
  }

  if (metricsData) {
    metrics.push({
      label: "Advisory Queries",
      value: String(metricsData.queries_tracked),
      icon: Calendar,
      subtext: `${metricsData.kb_provisions} provisions in KB`,
    });
  }

  /* ── Derive pending actions from compliance findings ─────── */
  const pendingActions: ActionItem[] = [];
  if (complianceData) {
    Object.entries(complianceData.domains).forEach(([domain, domainStatus]) => {
      if (domainStatus.status !== "covered") {
        const tier = domainStatusToTier(domainStatus.status);
        const label = DOMAIN_LABELS[domain] ?? domain;
        pendingActions.push({
          id: domain,
          title:
            domainStatus.status === "missing"
              ? `Add ${label} provisions to knowledge base`
              : `Expand ${label} coverage (${domainStatus.provisions_count} provisions found)`,
          tier,
        });
      }
    });
  }

  /* ── No company onboarding state ─────────────────────────── */
  if (!user?.company_id) {
    return (
      <div className="max-w-5xl mx-auto space-y-6 pb-8">
        {/* Greeting + Company Setup CTA */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-heading text-[var(--color-gray-900)]">
              {firstName ? `Welcome, ${firstName}` : "Welcome to Arbor"}
            </h1>
            <p className="text-body text-[var(--color-gray-500)] mt-1">
              Your free HR management platform for Singapore
            </p>
          </div>
          <CompanySetupCTA />
        </div>

        {/* Getting Started */}
        <div>
          <h2 className="text-subtitle text-[var(--color-gray-900)] mb-3">
            Getting Started
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <GettingStartedStep
              step={1}
              title="Create your company profile"
              description="Unlock payroll, leave, claims, attendance, and all HR features"
              href="/settings"
              icon={Building2}
              completed={false}
            />
            <GettingStartedStep
              step={2}
              title="Explore compliance requirements"
              description="See which Singapore regulations apply to your company"
              href="/compliance"
              icon={Compass}
              completed={false}
            />
            <GettingStartedStep
              step={3}
              title="Ask your first question"
              description="Get instant answers on employment law, CPF, levies, and more"
              href="/advisory"
              icon={MessageSquare}
              completed={false}
            />
          </div>
        </div>

        {/* HRIS Module Grid — the key addition */}
        <div>
          <h2 className="text-subtitle text-[var(--color-gray-900)] mb-3">
            Your HR Management Suite
          </h2>
          <HRISModuleGrid hasCompany={false} />
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="text-subtitle text-[var(--color-gray-900)] mb-3">
            Quick Actions
          </h2>
          <QuickActions />
        </div>

        {/* Value Preview */}
        <div>
          <h2 className="text-subtitle text-[var(--color-gray-900)] mb-3">
            AI Advisory & Compliance
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <CompliancePreviewCard />
            <AdvisoryPreviewCard />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* T124: Living Briefing Card with time-aware greeting */}
      <DashboardBriefing userName={user?.name} hasCompanyProfile />

      {/* Metric cards */}
      {complianceLoading || metricsLoading ? (
        <MetricsSkeleton />
      ) : complianceError && metricsError ? (
        <ErrorMessage message="Unable to load dashboard data. Please try refreshing the page." />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <AppCard key={metric.label} variant="flat">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
                      {metric.label}
                    </p>
                    <p className="text-2xl font-bold text-[var(--color-gray-900)] mt-1">
                      {metric.value}
                    </p>
                    {metric.subtext && (
                      <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                        {metric.subtext}
                      </p>
                    )}
                  </div>
                  <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
                    <Icon className="h-5 w-5 text-[var(--color-primary)]" />
                  </div>
                </div>
              </AppCard>
            );
          })}
        </div>
      )}

      {/* Quick actions */}
      <div>
        <h2 className="text-subtitle text-[var(--color-gray-900)] mb-3">
          Quick Actions
        </h2>
        <QuickActions />
      </div>

      {/* HRIS Module Navigation */}
      <div>
        <h2 className="text-subtitle text-[var(--color-gray-900)] mb-3">
          HR Management
        </h2>
        <HRISModuleGrid hasCompany />
      </div>

      {/* Two-column: Compliance domains + Pending actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Compliance domain status */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-subtitle text-[var(--color-gray-900)]">
              Compliance by Domain
            </h2>
            <button
              type="button"
              onClick={() => router.push("/compliance")}
              className="text-xs text-[var(--color-primary)] hover:underline flex items-center gap-1"
            >
              View details <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          {complianceLoading ? (
            <ListSkeleton />
          ) : complianceError ? (
            <ErrorMessage message={complianceError} />
          ) : complianceData ? (
            <div className="space-y-2">
              {Object.entries(complianceData.domains).map(
                ([domain, domainStatus]) => (
                  <div
                    key={domain}
                    className="flex items-start justify-between gap-2 p-3 rounded-lg bg-[var(--color-surface-card)] border border-[var(--color-gray-200)]"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[var(--color-gray-900)]">
                        {DOMAIN_LABELS[domain] ?? domain}
                      </p>
                      <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                        {domainStatus.provisions_count} provision
                        {domainStatus.provisions_count !== 1 ? "s" : ""} found
                      </p>
                    </div>
                    <RiskTierBadge
                      tier={domainStatusToTier(domainStatus.status)}
                      className="text-xs shrink-0"
                    />
                  </div>
                ),
              )}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-gray-500)]">
              No compliance data available.
            </p>
          )}
        </div>

        {/* Pending action items */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-subtitle text-[var(--color-gray-900)]">
              Pending Actions
            </h2>
            <button
              type="button"
              onClick={() => router.push("/compliance")}
              className="text-xs text-[var(--color-primary)] hover:underline flex items-center gap-1"
            >
              View all <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          {complianceLoading ? (
            <ListSkeleton />
          ) : complianceError ? (
            <ErrorMessage message={complianceError} />
          ) : pendingActions.length > 0 ? (
            <div className="space-y-2">
              {pendingActions.map((item) => (
                <div
                  key={item.id}
                  className="flex items-start gap-3 p-3 rounded-lg bg-[var(--color-surface-card)] border border-[var(--color-gray-200)]"
                >
                  <RiskTierBadge
                    tier={item.tier}
                    className="text-xs shrink-0 mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--color-gray-900)]">
                      {item.title}
                    </p>
                    {item.dueDate && (
                      <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                        Due: {item.dueDate}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 text-center rounded-lg bg-[var(--color-surface-card)] border border-[var(--color-gray-200)]">
              <p className="text-sm text-[var(--color-gray-500)]">
                No pending actions. All compliance domains are covered.
              </p>
            </div>
          )}
          <AppButton
            variant="outlined"
            size="sm"
            onClick={() => router.push("/compliance")}
            className="mt-3 w-full"
          >
            Run Compliance Check
          </AppButton>
        </div>
      </div>
    </div>
  );
}

/* -- Dashboard Briefing (T124) ------------------------------------ */

function DashboardBriefing({
  userName,
  hasCompanyProfile,
}: {
  userName?: string | null;
  hasCompanyProfile: boolean;
}) {
  const { insights, isLoading } = useShadowContext();

  return (
    <ShadowBriefingCard
      userName={userName}
      insights={insights}
      isLoading={isLoading}
      hasCompanyProfile={hasCompanyProfile}
    />
  );
}
