"use client";

import { useState, useEffect } from "react";
import {
  BarChart3,
  Users,
  Shield,
  MessageSquare,
  TrendingUp,
  TrendingDown,
  ThumbsUp,
  HelpCircle,
  AlertCircle,
} from "lucide-react";
import { AppCard } from "@/components/design-system";
import { useAuth } from "@/contexts/AuthContext";
import { complianceApi } from "@/services/api/compliance";
import { adminApi } from "@/services/api/admin";
import { profileApi } from "@/services/api/profile";
import type {
  ComplianceStatusResponse,
  PlatformMetricsResponse,
  QueryPatternsResponse,
  FeedbackSummaryResponse,
  MonthlyReportResponse,
  WorkforceBreakdown,
} from "@/types/api";

/* ── Types ────────────────────────────────────────────────── */

interface BreakdownItem {
  label: string;
  value: number;
  color: string;
}

/* ── Helper: sum of values ─────────────────────────────────── */

function sumValues(items: BreakdownItem[]): number {
  return items.reduce((acc, i) => acc + i.value, 0);
}

/* ── Loading skeleton ──────────────────────────────────────── */

function SectionSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-5 w-48 bg-[var(--color-gray-200)] rounded" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <AppCard key={i} variant="flat">
            <div className="h-16 bg-[var(--color-gray-100)] rounded" />
          </AppCard>
        ))}
      </div>
      <AppCard variant="standard">
        <div className="h-[200px] bg-[var(--color-gray-100)] rounded" />
      </AppCard>
    </div>
  );
}

function SummaryCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => (
        <AppCard key={i} variant="flat">
          <div className="animate-pulse">
            <div className="h-3 w-20 bg-[var(--color-gray-200)] rounded mb-3" />
            <div className="h-7 w-14 bg-[var(--color-gray-200)] rounded mb-2" />
            <div className="h-3 w-28 bg-[var(--color-gray-100)] rounded" />
          </div>
        </AppCard>
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

/* ── Donut Chart (pure CSS) ──────────────────────────────── */

function DonutChart({
  items,
  label,
}: {
  items: BreakdownItem[];
  label: string;
}) {
  const total = sumValues(items);

  if (total === 0) {
    return (
      <div className="flex flex-col items-center gap-3">
        <div className="w-[120px] h-[120px] rounded-full bg-[var(--color-gray-100)] flex items-center justify-center">
          <span className="text-lg font-bold text-[var(--color-gray-400)]">
            0
          </span>
        </div>
        <p className="text-xs font-medium text-[var(--color-gray-500)]">
          {label}
        </p>
        <p className="text-xs text-[var(--color-gray-400)]">No data yet</p>
      </div>
    );
  }

  // Build conic-gradient segments
  let accumulated = 0;
  const segments = items.map((item) => {
    const start = accumulated;
    const pct = (item.value / total) * 100;
    accumulated += pct;
    return `${item.color} ${start}% ${accumulated}%`;
  });
  const gradient = `conic-gradient(${segments.join(", ")})`;

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className="relative w-[120px] h-[120px] rounded-full"
        style={{ background: gradient }}
        role="img"
        aria-label={`${label} chart: ${items.map((i) => `${i.label} ${i.value}`).join(", ")}`}
      >
        {/* Inner circle for donut effect */}
        <div className="absolute inset-[25%] rounded-full bg-[var(--color-surface-card)] flex items-center justify-center">
          <span className="text-lg font-bold text-[var(--color-gray-900)]">
            {total}
          </span>
        </div>
      </div>
      <p className="text-xs font-medium text-[var(--color-gray-500)]">
        {label}
      </p>
      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-x-3 gap-y-1">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-xs text-[var(--color-gray-600)]">
              {item.label} ({item.value})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Horizontal Bar Chart ────────────────────────────────── */

function HorizontalBarChart({
  items,
  maxValue,
  barColor,
}: {
  items: { label: string; value: number }[];
  maxValue?: number;
  barColor?: string;
}) {
  const max = maxValue ?? Math.max(...items.map((i) => i.value), 1);

  return (
    <div className="space-y-2.5">
      {items.map((item) => {
        const pct = max > 0 ? (item.value / max) * 100 : 0;
        return (
          <div key={item.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-[var(--color-gray-700)] truncate max-w-[60%]">
                {item.label}
              </span>
              <span className="text-xs font-medium text-[var(--color-gray-900)]">
                {item.value}
              </span>
            </div>
            <div className="h-2 rounded-full bg-[var(--color-gray-100)] overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${pct}%`,
                  backgroundColor: barColor ?? "var(--color-primary)",
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Compliance Status Bar Chart ─────────────────────────── */

function ComplianceDomainsChart({ data }: { data: ComplianceStatusResponse }) {
  const domainLabels: Record<string, string> = {
    employment_act: "Employment Act",
    cpf: "CPF",
    foreign_manpower: "Foreign Manpower",
    tax: "Tax / IRAS",
    wsh: "WSH",
  };

  const entries = Object.entries(data.domains);
  if (entries.length === 0) {
    return (
      <p className="text-sm text-[var(--color-gray-400)]">
        No domain data available.
      </p>
    );
  }

  const maxProvisions = Math.max(
    ...entries.map(([, d]) => d.provisions_count),
    1,
  );

  return (
    <div>
      {/* Legend */}
      <div className="flex gap-3 mb-3">
        <span className="flex items-center gap-1 text-xs text-[var(--color-gray-500)]">
          <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-risk-green)]" />
          Covered
        </span>
        <span className="flex items-center gap-1 text-xs text-[var(--color-gray-500)]">
          <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-risk-amber)]" />
          Sparse
        </span>
        <span className="flex items-center gap-1 text-xs text-[var(--color-gray-500)]">
          <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-risk-red)]" />
          Missing
        </span>
      </div>

      {/* Bars */}
      <div className="relative h-[180px] flex items-end gap-1">
        {entries.map(([domain, domainStatus]) => {
          const heightPct =
            maxProvisions > 0
              ? (domainStatus.provisions_count / maxProvisions) * 100
              : 0;
          const color =
            domainStatus.status === "covered"
              ? "var(--color-risk-green)"
              : domainStatus.status === "sparse"
                ? "var(--color-risk-amber)"
                : "var(--color-risk-red)";

          return (
            <div
              key={domain}
              className="flex-1 flex flex-col items-center justify-end"
            >
              <span className="text-xs font-medium mb-1" style={{ color }}>
                {domainStatus.provisions_count}
              </span>
              <div
                className="w-full max-w-[40px] rounded-t-md transition-all duration-500"
                style={{
                  height: `${Math.max(heightPct, 5)}%`,
                  backgroundColor: color,
                  opacity: 0.85,
                }}
              />
            </div>
          );
        })}
      </div>
      {/* X-axis labels */}
      <div className="flex gap-1 mt-2">
        {entries.map(([domain]) => (
          <div key={domain} className="flex-1 text-center">
            <span className="text-xs text-[var(--color-gray-400)]">
              {domainLabels[domain] ?? domain}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Summary Metric Card ─────────────────────────────────── */

function SummaryCard({
  label,
  value,
  icon: Icon,
  subtext,
  trend,
}: {
  label: string;
  value: string;
  icon: typeof Users;
  subtext?: string;
  trend?: "up" | "down";
}) {
  return (
    <AppCard variant="flat">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            {label}
          </p>
          <p className="text-2xl font-bold text-[var(--color-gray-900)] mt-1">
            {value}
          </p>
          {subtext && (
            <div className="flex items-center gap-1 mt-0.5">
              {trend === "up" && (
                <TrendingUp className="h-3 w-3 text-[var(--color-risk-green)]" />
              )}
              {trend === "down" && (
                <TrendingDown className="h-3 w-3 text-[var(--color-risk-red)]" />
              )}
              <p className="text-xs text-[var(--color-gray-400)]">{subtext}</p>
            </div>
          )}
        </div>
        <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
          <Icon className="h-5 w-5 text-[var(--color-primary)]" />
        </div>
      </div>
    </AppCard>
  );
}

/* ── Page ──────────────────────────────────────────────────── */

export default function AnalyticsPage() {
  const { user } = useAuth();

  const [activeSection, setActiveSection] = useState<
    "overview" | "compliance" | "advisory"
  >("overview");

  /* ── Data state ──────────────────────────────────────────── */
  const [workforce, setWorkforce] = useState<WorkforceBreakdown | null>(null);
  const [compliance, setCompliance] = useState<ComplianceStatusResponse | null>(
    null,
  );
  const [metrics, setMetrics] = useState<PlatformMetricsResponse | null>(null);
  const [patterns, setPatterns] = useState<QueryPatternsResponse | null>(null);
  const [feedback, setFeedback] = useState<FeedbackSummaryResponse | null>(
    null,
  );
  const [report, setReport] = useState<MonthlyReportResponse | null>(null);

  /* ── Loading state ───────────────────────────────────────── */
  const [workforceLoading, setWorkforceLoading] = useState(true);
  const [complianceLoading, setComplianceLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [patternsLoading, setPatternsLoading] = useState(true);
  const [feedbackLoading, setFeedbackLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(true);

  /* ── Error state ─────────────────────────────────────────── */
  const [workforceError, setWorkforceError] = useState<string | null>(null);
  const [complianceError, setComplianceError] = useState<string | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [patternsError, setPatternsError] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  /* ── Fetch all data on mount ─────────────────────────────── */
  useEffect(() => {
    const companyId = user?.company_id;

    if (companyId) {
      profileApi
        .workforce(companyId)
        .then((data) => setWorkforce(data))
        .catch(() =>
          setWorkforceError("Unable to load workforce data right now."),
        )
        .finally(() => setWorkforceLoading(false));

      complianceApi
        .status(companyId)
        .then((data) => setCompliance(data))
        .catch(() =>
          setComplianceError("Unable to load compliance data right now."),
        )
        .finally(() => setComplianceLoading(false));
    } else {
      setWorkforceLoading(false);
      setComplianceLoading(false);
    }

    adminApi
      .metrics()
      .then((data) => setMetrics(data))
      .catch(() => setMetricsError("Unable to load metrics right now."))
      .finally(() => setMetricsLoading(false));

    adminApi
      .queryPatterns()
      .then((data) => setPatterns(data))
      .catch(() => setPatternsError("Unable to load query patterns right now."))
      .finally(() => setPatternsLoading(false));

    adminApi
      .feedbackSummary()
      .then((data) => setFeedback(data))
      .catch(() => setFeedbackError("Unable to load feedback data right now."))
      .finally(() => setFeedbackLoading(false));

    adminApi
      .monthlyReport()
      .then((data) => {
        // Backend returns { empty: true } when no reports exist yet
        if (data && !("empty" in data)) {
          setReport(data);
        }
      })
      .catch(() => {
        // Gracefully handle errors -- not a critical section
        setReportError(null);
      })
      .finally(() => setReportLoading(false));
  }, [user?.company_id]);

  /* ── Derive data for the workforce overview ──────────────── */
  const workforceBreakdown: BreakdownItem[] = workforce
    ? [
        {
          label: "Local",
          value: workforce.workforce.local,
          color: "var(--color-primary)",
        },
        {
          label: "PR",
          value: workforce.workforce.pr,
          color: "var(--color-risk-amber)",
        },
        {
          label: "EP",
          value: workforce.workforce.ep,
          color: "var(--color-risk-green)",
        },
        {
          label: "SP",
          value: workforce.workforce.sp,
          color: "#8b5cf6",
        },
        {
          label: "WP",
          value: workforce.workforce.wp,
          color: "var(--color-risk-red)",
        },
      ].filter((item) => item.value > 0)
    : [];

  const totalEmployees = workforce?.total ?? 0;

  /* ── Derive compliance score ─────────────────────────────── */
  const complianceScore = compliance
    ? (() => {
        const entries = Object.entries(compliance.domains);
        const covered = entries.filter(
          ([, d]) => d.status === "covered",
        ).length;
        return entries.length > 0
          ? Math.round((covered / entries.length) * 100)
          : 0;
      })()
    : 0;

  /* ── Derive domain queries from patterns ─────────────────── */
  const domainQueries: { label: string; value: number }[] = [];
  if (patterns) {
    const domainCounts: Record<string, number> = {};
    for (const pattern of patterns.patterns) {
      for (const domain of pattern.domains) {
        domainCounts[domain] = (domainCounts[domain] ?? 0) + pattern.frequency;
      }
    }
    const domainLabels: Record<string, string> = {
      employment_act: "Employment Act",
      cpf: "CPF",
      foreign_manpower: "Foreign Manpower",
      fair_employment: "Fair Employment",
      wsh: "Workplace Safety",
      tax: "Tax / IRAS",
    };
    Object.entries(domainCounts)
      .sort((a, b) => b[1] - a[1])
      .forEach(([domain, count]) => {
        domainQueries.push({
          label: domainLabels[domain] ?? domain,
          value: count,
        });
      });
  }

  /* ── Derive top topics from patterns ─────────────────────── */
  const topTopics = patterns
    ? patterns.patterns
        .sort((a, b) => b.frequency - a.frequency)
        .slice(0, 5)
        .map((p) => ({
          topic: p.description,
          count: p.frequency,
        }))
    : [];

  const totalQueries = metrics?.queries_tracked ?? 0;
  const feedbackRate = feedback ? Math.round(feedback.positive_rate * 100) : 0;

  const sections = [
    { key: "overview" as const, label: "Workforce" },
    { key: "compliance" as const, label: "Compliance" },
    { key: "advisory" as const, label: "Advisory" },
  ];

  const summaryLoading =
    workforceLoading || complianceLoading || metricsLoading || feedbackLoading;

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BarChart3
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Analytics
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Workforce composition, compliance trends, and advisory usage at a
            glance.
          </p>
        </div>
      </div>

      {/* Summary metric cards */}
      {summaryLoading ? (
        <SummaryCardsSkeleton />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <SummaryCard
            label="Total Employees"
            value={String(totalEmployees)}
            icon={Users}
            subtext={
              workforce
                ? `${Math.round(workforce.local_ratio * 100)}% local`
                : "No workforce data"
            }
          />
          <SummaryCard
            label="Compliance Score"
            value={compliance ? `${complianceScore}/100` : "N/A"}
            icon={Shield}
            subtext={
              compliance
                ? compliance.overall_status === "compliant"
                  ? "All domains covered"
                  : "Some domains need attention"
                : "No data"
            }
          />
          <SummaryCard
            label="Advisory Queries"
            value={String(totalQueries)}
            icon={MessageSquare}
            subtext={
              feedback && feedback.total_feedback > 0
                ? `${feedbackRate}% positive`
                : "No feedback yet"
            }
            trend={
              feedbackRate >= 80 ? "up" : feedbackRate > 0 ? "down" : undefined
            }
          />
          <SummaryCard
            label="KB Provisions"
            value={metrics ? String(metrics.kb_provisions) : "N/A"}
            icon={HelpCircle}
            subtext={
              metrics
                ? `${metrics.kb_domains} domains, ${metrics.kb_acts} acts`
                : "No data"
            }
          />
        </div>
      )}

      {/* Section tabs */}
      <div className="flex gap-2 overflow-x-auto">
        {sections.map((s) => (
          <button
            key={s.key}
            onClick={() => setActiveSection(s.key)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${
              activeSection === s.key
                ? "bg-[var(--color-primary)] text-white"
                : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:text-[var(--color-gray-800)]"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* ─── Section: Workforce Overview ─────────────────────── */}
      {activeSection === "overview" && (
        <div className="space-y-6">
          {workforceLoading ? (
            <SectionSkeleton />
          ) : workforceError ? (
            <ErrorMessage message={workforceError} />
          ) : !workforce || totalEmployees === 0 ? (
            <AppCard variant="standard">
              <div className="text-center py-8">
                <Users className="h-10 w-10 text-[var(--color-gray-300)] mx-auto mb-3" />
                <p className="text-sm text-[var(--color-gray-500)]">
                  No workforce data available. Update your company profile to
                  see workforce analytics.
                </p>
              </div>
            </AppCard>
          ) : (
            <>
              {/* Donut charts row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <AppCard variant="standard">
                  <DonutChart items={workforceBreakdown} label="By Pass Type" />
                </AppCard>
                <AppCard variant="standard">
                  <DonutChart
                    items={[
                      {
                        label: "Local + PR",
                        value:
                          workforce.workforce.local + workforce.workforce.pr,
                        color: "var(--color-primary)",
                      },
                      {
                        label: "Foreign",
                        value:
                          workforce.workforce.ep +
                          workforce.workforce.sp +
                          workforce.workforce.wp,
                        color: "var(--color-risk-amber)",
                      },
                    ].filter((i) => i.value > 0)}
                    label="Local vs Foreign"
                  />
                </AppCard>
              </div>

              {/* Workforce composition table */}
              <AppCard variant="standard">
                <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-4">
                  Workforce Composition Summary
                </h3>
                <div className="overflow-x-auto -mx-5">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[var(--color-gray-200)]">
                        <th className="px-5 py-2 text-left font-medium text-[var(--color-gray-500)]">
                          Category
                        </th>
                        <th className="px-5 py-2 text-left font-medium text-[var(--color-gray-500)]">
                          Count
                        </th>
                        <th className="px-5 py-2 text-left font-medium text-[var(--color-gray-500)]">
                          Percentage
                        </th>
                        <th className="px-5 py-2 text-left font-medium text-[var(--color-gray-500)]">
                          Distribution
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {workforceBreakdown.map((item) => {
                        const pct =
                          totalEmployees > 0
                            ? ((item.value / totalEmployees) * 100).toFixed(1)
                            : "0.0";
                        return (
                          <tr
                            key={item.label}
                            className="border-b border-[var(--color-gray-100)]"
                          >
                            <td className="px-5 py-2.5">
                              <div className="flex items-center gap-2">
                                <span
                                  className="w-2.5 h-2.5 rounded-full shrink-0"
                                  style={{ backgroundColor: item.color }}
                                />
                                <span className="text-[var(--color-gray-700)]">
                                  {item.label}
                                </span>
                              </div>
                            </td>
                            <td className="px-5 py-2.5 font-medium text-[var(--color-gray-900)]">
                              {item.value}
                            </td>
                            <td className="px-5 py-2.5 text-[var(--color-gray-600)]">
                              {pct}%
                            </td>
                            <td className="px-5 py-2.5">
                              <div className="h-2 w-full max-w-[120px] rounded-full bg-[var(--color-gray-100)] overflow-hidden">
                                <div
                                  className="h-full rounded-full"
                                  style={{
                                    width: `${pct}%`,
                                    backgroundColor: item.color,
                                  }}
                                />
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </AppCard>
            </>
          )}
        </div>
      )}

      {/* ─── Section: Compliance ─────────────────────────────── */}
      {activeSection === "compliance" && (
        <div className="space-y-6">
          {complianceLoading ? (
            <SectionSkeleton />
          ) : complianceError ? (
            <ErrorMessage message={complianceError} />
          ) : !compliance ? (
            <AppCard variant="standard">
              <div className="text-center py-8">
                <Shield className="h-10 w-10 text-[var(--color-gray-300)] mx-auto mb-3" />
                <p className="text-sm text-[var(--color-gray-500)]">
                  No compliance data available. Set up your company profile and
                  run a compliance check.
                </p>
              </div>
            </AppCard>
          ) : (
            <>
              {/* Current score card */}
              <AppCard variant="elevated">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[var(--color-gray-500)]">
                      Current Compliance Score
                    </p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-4xl font-bold text-[var(--color-gray-900)]">
                        {complianceScore}
                      </span>
                      <span className="text-lg text-[var(--color-gray-400)]">
                        / 100
                      </span>
                    </div>
                    <p className="text-xs text-[var(--color-gray-500)] mt-1">
                      Status: {compliance.overall_status.replace("_", " ")}
                    </p>
                  </div>
                  <div
                    className="w-20 h-20 rounded-full border-4 flex items-center justify-center"
                    style={{
                      borderColor:
                        complianceScore >= 80
                          ? "var(--color-risk-green)"
                          : complianceScore >= 50
                            ? "var(--color-risk-amber)"
                            : "var(--color-risk-red)",
                    }}
                  >
                    <span className="text-xl font-bold">
                      {complianceScore}%
                    </span>
                  </div>
                </div>
              </AppCard>

              {/* Domain coverage chart */}
              <AppCard variant="standard">
                <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-4">
                  Compliance Coverage by Domain
                </h3>
                <ComplianceDomainsChart data={compliance} />
              </AppCard>

              {/* Domain detail table */}
              <AppCard variant="standard">
                <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-4">
                  Domain Coverage Details
                </h3>
                <div className="space-y-2">
                  {Object.entries(compliance.domains).map(
                    ([domain, domainStatus]) => {
                      const statusLabel =
                        domainStatus.status === "covered"
                          ? "Covered"
                          : domainStatus.status === "sparse"
                            ? "Sparse Coverage"
                            : "Missing";
                      const color =
                        domainStatus.status === "covered"
                          ? "var(--color-risk-green)"
                          : domainStatus.status === "sparse"
                            ? "var(--color-risk-amber)"
                            : "var(--color-risk-red)";

                      const domainLabels: Record<string, string> = {
                        employment_act: "Employment Act",
                        cpf: "CPF",
                        foreign_manpower: "Foreign Manpower",
                        tax: "Tax / IRAS",
                        wsh: "WSH",
                      };

                      return (
                        <div
                          key={domain}
                          className="flex items-center justify-between py-2 border-b border-[var(--color-gray-100)] last:border-0"
                        >
                          <span className="text-sm text-[var(--color-gray-700)]">
                            {domainLabels[domain] ?? domain}
                          </span>
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-[var(--color-gray-400)]">
                              {domainStatus.provisions_count} provision
                              {domainStatus.provisions_count !== 1 ? "s" : ""}
                            </span>
                            <span
                              className="text-sm font-semibold min-w-[80px] text-right"
                              style={{ color }}
                            >
                              {statusLabel}
                            </span>
                          </div>
                        </div>
                      );
                    },
                  )}
                </div>
              </AppCard>
            </>
          )}
        </div>
      )}

      {/* ─── Section: Advisory Usage ─────────────────────────── */}
      {activeSection === "advisory" && (
        <div className="space-y-6">
          {/* Advisory summary */}
          {metricsLoading || feedbackLoading ? (
            <SectionSkeleton />
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <AppCard variant="flat">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs text-[var(--color-gray-500)]">
                        Total Queries
                      </p>
                      <p className="text-2xl font-bold text-[var(--color-gray-900)] mt-1">
                        {totalQueries}
                      </p>
                    </div>
                    <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
                      <MessageSquare className="h-5 w-5 text-[var(--color-primary)]" />
                    </div>
                  </div>
                </AppCard>
                <AppCard variant="flat">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs text-[var(--color-gray-500)]">
                        Positive Feedback
                      </p>
                      <p className="text-2xl font-bold text-[var(--color-risk-green)] mt-1">
                        {feedback && feedback.total_feedback > 0
                          ? `${feedbackRate}%`
                          : "N/A"}
                      </p>
                    </div>
                    <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
                      <ThumbsUp className="h-5 w-5 text-[var(--color-primary)]" />
                    </div>
                  </div>
                </AppCard>
                <AppCard variant="flat">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs text-[var(--color-gray-500)]">
                        Domains Covered
                      </p>
                      <p className="text-2xl font-bold text-[var(--color-gray-900)] mt-1">
                        {domainQueries.length}
                      </p>
                    </div>
                    <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
                      <HelpCircle className="h-5 w-5 text-[var(--color-primary)]" />
                    </div>
                  </div>
                </AppCard>
              </div>

              {/* Risk distribution */}
              {metrics && (
                <AppCard variant="standard">
                  <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-4">
                    Query Risk Distribution
                  </h3>
                  <DonutChart
                    items={[
                      {
                        label: "Green",
                        value: metrics.risk_distribution.green ?? 0,
                        color: "var(--color-risk-green)",
                      },
                      {
                        label: "Amber",
                        value: metrics.risk_distribution.amber ?? 0,
                        color: "var(--color-risk-amber)",
                      },
                      {
                        label: "Red",
                        value: metrics.risk_distribution.red ?? 0,
                        color: "var(--color-risk-red)",
                      },
                    ].filter((i) => i.value > 0)}
                    label="Risk Tier Distribution"
                  />
                </AppCard>
              )}

              {/* Queries by domain */}
              {patternsLoading ? (
                <AppCard variant="standard">
                  <div className="animate-pulse">
                    <div className="h-5 w-40 bg-[var(--color-gray-200)] rounded mb-4" />
                    <div className="space-y-3">
                      {[...Array(4)].map((_, i) => (
                        <div key={i}>
                          <div className="h-3 w-full bg-[var(--color-gray-100)] rounded" />
                        </div>
                      ))}
                    </div>
                  </div>
                </AppCard>
              ) : patternsError ? (
                <ErrorMessage message={patternsError} />
              ) : domainQueries.length > 0 ? (
                <AppCard variant="standard">
                  <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-4">
                    Queries by Domain
                  </h3>
                  <HorizontalBarChart items={domainQueries} />
                </AppCard>
              ) : (
                <AppCard variant="standard">
                  <div className="text-center py-6">
                    <p className="text-sm text-[var(--color-gray-400)]">
                      No query patterns recorded yet.
                    </p>
                  </div>
                </AppCard>
              )}

              {/* Most-asked topics */}
              {topTopics.length > 0 && (
                <AppCard variant="standard">
                  <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-4">
                    Most-Asked Topics
                  </h3>
                  <div className="space-y-3">
                    {topTopics.map((topic, idx) => (
                      <div
                        key={topic.topic}
                        className="flex items-center gap-3 py-2 border-b border-[var(--color-gray-100)] last:border-0"
                      >
                        <span className="w-6 h-6 rounded-full bg-[var(--color-primary-bg)] text-[var(--color-primary)] text-xs font-bold flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        <span className="text-sm text-[var(--color-gray-700)] flex-1">
                          {topic.topic}
                        </span>
                        <span className="text-xs font-medium text-[var(--color-gray-500)] bg-[var(--color-gray-100)] px-2 py-0.5 rounded-full">
                          {topic.count} queries
                        </span>
                      </div>
                    ))}
                  </div>
                </AppCard>
              )}

              {/* Feedback bar */}
              {feedback && feedback.total_feedback > 0 && (
                <AppCard variant="standard">
                  <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
                    Advisory Feedback Rate
                  </h3>
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <div className="h-3 rounded-full bg-[var(--color-gray-100)] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-[var(--color-risk-green)] transition-all duration-500"
                          style={{ width: `${feedbackRate}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-sm font-semibold text-[var(--color-risk-green)] min-w-[48px] text-right">
                      {feedbackRate}%
                    </span>
                  </div>
                  <p className="text-xs text-[var(--color-gray-400)] mt-2">
                    Based on {feedback.total_feedback} responses with user
                    feedback ({feedback.positive_count} positive,{" "}
                    {feedback.negative_count} negative)
                  </p>
                </AppCard>
              )}

              {/* Monthly report summary */}
              {report && (
                <AppCard variant="standard">
                  <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
                    Latest Monthly Report ({report.period})
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                    <div>
                      <p className="text-xs text-[var(--color-gray-500)]">
                        Queries
                      </p>
                      <p className="text-lg font-bold text-[var(--color-gray-900)]">
                        {report.total_queries}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--color-gray-500)]">
                        Feedback
                      </p>
                      <p className="text-lg font-bold text-[var(--color-gray-900)]">
                        {report.total_feedback}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--color-gray-500)]">
                        KB Gaps
                      </p>
                      <p className="text-lg font-bold text-[var(--color-gray-900)]">
                        {report.kb_gaps_count}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--color-gray-500)]">
                        Recommendations
                      </p>
                      <p className="text-lg font-bold text-[var(--color-gray-900)]">
                        {report.recommendations_count}
                      </p>
                    </div>
                  </div>
                </AppCard>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
