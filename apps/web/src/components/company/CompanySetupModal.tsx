"use client";

import { useState, useEffect } from "react";
import {
  Building2,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  X,
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  Info,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { profileApi } from "@/services/api/profile";

const SECTORS = [
  { value: "technology", label: "Technology & IT" },
  { value: "fnb", label: "Food & Beverage" },
  { value: "retail", label: "Retail & E-commerce" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "construction", label: "Construction" },
  { value: "services", label: "Professional Services" },
  { value: "healthcare", label: "Healthcare" },
  { value: "education", label: "Education" },
  { value: "logistics", label: "Logistics & Transport" },
  { value: "other", label: "Other" },
];

const HEADCOUNT_RANGES = [
  { value: "1-5", label: "1 - 5 employees" },
  { value: "6-25", label: "6 - 25 employees" },
  { value: "26-50", label: "26 - 50 employees" },
  { value: "51-100", label: "51 - 100 employees" },
  { value: "101-200", label: "101 - 200 employees" },
];

/* ------------------------------------------------------------------ */
/*  Compliance Snapshot — insight types and generation                 */
/* ------------------------------------------------------------------ */

type InsightSeverity = "info" | "warning" | "critical";

interface ComplianceInsight {
  id: string;
  title: string;
  description: string;
  severity: InsightSeverity;
  regulation?: string;
}

/**
 * Parse a headcount range string ("26-50") into a representative number
 * (the midpoint of the range).
 */
function parseHeadcount(range: string): number {
  const parts = range.split("-");
  const low = parseInt(parts[0], 10) || 0;
  const high = parseInt(parts[1], 10) || low;
  return Math.round((low + high) / 2);
}

/**
 * Generate 3-5 compliance insights based on the company setup form data.
 * All logic is client-side — no API call required.
 */
function generateModalInsights(form: {
  sector: string;
  headcount: string;
}): ComplianceInsight[] {
  const insights: ComplianceInsight[] = [];
  const count = parseHeadcount(form.headcount);

  // 1. Employment Act coverage — universal for all employers
  insights.push({
    id: "ea-coverage",
    title: "Employment Act Coverage",
    description:
      "All employees (except domestic workers, seafarers, and statutory board employees) are covered by the Employment Act regardless of salary. Ensure employment contracts comply.",
    severity: "info",
    regulation: "Employment Act 1968",
  });

  // 2. CPF obligations — universal
  insights.push({
    id: "cpf-obligations",
    title: "CPF Contribution Obligations",
    description:
      "You must contribute CPF for all Singapore Citizen and Permanent Resident employees. Contribution rates vary by age band and salary ceiling ($6,800/month ordinary wages).",
    severity: "info",
    regulation: "CPF Act",
  });

  // 3. Headcount-based: grievance handling
  if (count >= 10) {
    insights.push({
      id: "grievance-procedure",
      title: "Documented Grievance Procedure Recommended",
      description: `With approximately ${count} employees, MOM recommends a documented grievance handling procedure. This becomes practically essential as your team grows.`,
      severity: "warning",
      regulation: "MOM Tripartite Guidelines",
    });
  }

  // 4. Sector-specific insights
  if (form.sector === "construction") {
    insights.push({
      id: "construction-safety",
      title: "Workplace Safety & Health Requirements",
      description:
        "Construction companies must appoint a Workplace Safety and Health Officer for worksites with 50+ workers, and maintain site-specific safety plans.",
      severity: "critical",
      regulation: "Workplace Safety and Health Act",
    });
  } else if (form.sector === "fnb" || form.sector === "retail") {
    insights.push({
      id: "part-iv-overtime",
      title: "Part IV Overtime Protections Likely Apply",
      description:
        "Employees earning $2,600/month or below are covered by Part IV of the Employment Act — working hours, overtime (1.5x rate), and rest day provisions must be observed.",
      severity: "warning",
      regulation: "Employment Act Part IV",
    });
  } else if (form.sector === "manufacturing") {
    insights.push({
      id: "manufacturing-safety",
      title: "Factory Registration & Safety Requirements",
      description:
        "Manufacturing workplaces may require registration under the Workplace Safety and Health (General Provisions) Regulations. Ensure risk assessments are conducted.",
      severity: "warning",
      regulation: "WSH (General Provisions) Regulations",
    });
  }

  // 5. Fair Consideration Framework — relevant for any employer likely hiring foreign talent
  if (count >= 10) {
    insights.push({
      id: "fcf-advertising",
      title: "Fair Consideration Framework",
      description:
        "Before hiring foreign workers on EP or S Pass, positions must be advertised on MyCareersFuture for at least 14 consecutive days (exemptions apply for firms with fewer than 10 employees).",
      severity: "info",
      regulation: "TAFEP Fair Consideration Framework",
    });
  }

  // 6. Skills Development Levy — universal for employers
  if (count >= 6) {
    insights.push({
      id: "sdl-levy",
      title: "Skills Development Levy",
      description:
        "You must pay SDL for all employees (local and foreign) at $0.25 per $100 of monthly remuneration, with a minimum of $2 per employee per month.",
      severity: "info",
      regulation: "Skills Development Levy Act",
    });
  }

  return insights.slice(0, 5);
}

interface CompanySetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete?: () => void;
}

export function CompanySetupModal({
  isOpen,
  onClose,
  onComplete,
}: CompanySetupModalProps) {
  const { refreshUser } = useAuth();
  const [step, setStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState({
    name: "",
    uen: "",
    sector: "",
    headcount: "",
  });
  const [snapshotInsights, setSnapshotInsights] = useState<ComplianceInsight[]>(
    [],
  );
  const [snapshotLoading, setSnapshotLoading] = useState(false);

  // Generate insights when arriving at the snapshot step
  useEffect(() => {
    if (step === 2 && snapshotLoading) {
      const timer = setTimeout(() => {
        setSnapshotInsights(generateModalInsights(form));
        setSnapshotLoading(false);
      }, 900);
      return () => clearTimeout(timer);
    }
  }, [step, snapshotLoading, form]);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await profileApi.create({
        name: form.name,
        uen: form.uen || undefined,
        sector: form.sector,
      });

      await refreshUser?.();
      // Move to the compliance snapshot step
      setStep(2);
      setSnapshotLoading(true);
    } catch (err: any) {
      const message =
        err?.detail ||
        err?.message ||
        "Something went wrong. Please try again.";
      alert(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSnapshotContinue = () => {
    setStep(3);
    setTimeout(() => {
      onComplete?.();
      onClose();
      window.location.reload();
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-white rounded-2xl shadow-2xl overflow-hidden animate-fade-in max-h-[90vh] flex flex-col">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-full hover:bg-gray-100 transition-colors z-10"
          aria-label="Close"
        >
          <X className="w-5 h-5 text-gray-400" />
        </button>

        {/* Step indicator — visible on steps 1-3 */}
        {step >= 1 && step <= 3 && (
          <div className="flex items-center justify-center gap-2 pt-6 px-8 shrink-0">
            {[1, 2, 3].map((s) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full transition-colors ${
                    s < step
                      ? "bg-green-500"
                      : s === step
                        ? "bg-blue-600"
                        : "bg-gray-300"
                  }`}
                />
                {s < 3 && (
                  <div
                    className={`w-8 h-0.5 transition-colors ${
                      s < step ? "bg-green-500" : "bg-gray-200"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        )}

        <div className="overflow-y-auto">
          {step === 0 && (
            /* Welcome step */
            <div className="p-8 text-center">
              <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mb-6">
                <Building2 className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-3">
                Welcome to Central
              </h2>
              <p className="text-gray-600 mb-2">
                Set up your company to unlock the full HR management suite —
                payroll, leave, claims, attendance, shifts, and more.
              </p>
              <p className="text-sm text-gray-500 mb-8">
                It takes less than a minute. You can always update these details
                later.
              </p>
              <button
                onClick={() => setStep(1)}
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all shadow-lg shadow-blue-500/25"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {step === 1 && (
            /* Form step */
            <div className="p-8">
              <div className="flex items-center gap-3 mb-6">
                <Sparkles className="w-6 h-6 text-blue-600" />
                <h2 className="text-xl font-bold text-gray-900">
                  Company Details
                </h2>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Company Name *
                  </label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="e.g. Acme Pte Ltd"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    autoFocus
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    UEN *
                  </label>
                  <input
                    type="text"
                    value={form.uen}
                    onChange={(e) => setForm({ ...form, uen: e.target.value })}
                    placeholder="e.g. 201234567K"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Your Unique Entity Number from ACRA
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Industry Sector *
                  </label>
                  <select
                    value={form.sector}
                    onChange={(e) =>
                      setForm({ ...form, sector: e.target.value })
                    }
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  >
                    <option value="">Select your industry</option>
                    {SECTORS.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Number of Employees *
                  </label>
                  <select
                    value={form.headcount}
                    onChange={(e) =>
                      setForm({ ...form, headcount: e.target.value })
                    }
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  >
                    <option value="">Select range</option>
                    {HEADCOUNT_RANGES.map((h) => (
                      <option key={h.value} value={h.value}>
                        {h.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-8 flex gap-3">
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors font-medium"
                >
                  I&apos;ll do this later
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={
                    !form.name ||
                    !form.uen ||
                    !form.sector ||
                    !form.headcount ||
                    isSubmitting
                  }
                  className="flex-1 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/25"
                >
                  {isSubmitting ? "Setting up..." : "Create Company"}
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            /* Compliance Snapshot step */
            <div className="p-8">
              <div className="flex items-center gap-3 mb-1">
                <ShieldCheck className="w-6 h-6 text-blue-600" />
                <h2 className="text-xl font-bold text-gray-900">
                  Compliance Snapshot
                </h2>
              </div>
              <p className="text-sm text-gray-500 mb-6">
                Based on your company profile, here are the key compliance areas
                to be aware of.
              </p>

              {snapshotLoading ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
                  <p className="mt-4 text-sm text-gray-500">
                    Analysing your company profile...
                  </p>
                </div>
              ) : (
                <>
                  <div className="space-y-3">
                    {snapshotInsights.map((insight) => {
                      const severityConfig = {
                        info: {
                          icon: Info,
                          bg: "bg-blue-50",
                          border: "border-blue-200",
                          iconColor: "text-blue-600",
                          label: "Info",
                          labelBg: "bg-blue-100 text-blue-700",
                        },
                        warning: {
                          icon: AlertTriangle,
                          bg: "bg-[var(--color-risk-amber-bg)]",
                          border: "border-[var(--color-risk-amber-border)]",
                          iconColor: "text-[var(--color-risk-amber)]",
                          label: "Attention",
                          labelBg:
                            "bg-[var(--color-risk-amber-bg)] text-[var(--color-risk-amber)]",
                        },
                        critical: {
                          icon: AlertOctagon,
                          bg: "bg-[var(--color-risk-red-bg)]",
                          border: "border-[var(--color-risk-red-border)]",
                          iconColor: "text-[var(--color-risk-red)]",
                          label: "Critical",
                          labelBg:
                            "bg-[var(--color-risk-red-bg)] text-[var(--color-risk-red)]",
                        },
                      };
                      const config = severityConfig[insight.severity];
                      const SeverityIcon = config.icon;

                      return (
                        <div
                          key={insight.id}
                          className={`rounded-xl border p-4 ${config.bg} ${config.border}`}
                        >
                          <div className="flex items-start gap-3">
                            <SeverityIcon
                              className={`w-5 h-5 shrink-0 mt-0.5 ${config.iconColor}`}
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1 flex-wrap">
                                <h3 className="text-sm font-semibold text-gray-900">
                                  {insight.title}
                                </h3>
                                <span
                                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.labelBg}`}
                                >
                                  {config.label}
                                </span>
                              </div>
                              <p className="text-xs text-gray-600 leading-relaxed">
                                {insight.description}
                              </p>
                              {insight.regulation && (
                                <p className="mt-1.5 text-xs text-gray-400">
                                  Ref: {insight.regulation}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="mt-6">
                    <button
                      onClick={handleSnapshotContinue}
                      className="w-full px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all font-medium shadow-lg shadow-blue-500/25"
                    >
                      Continue to Dashboard
                    </button>
                    <p className="mt-2 text-xs text-gray-400 text-center">
                      You can explore these topics in detail with Arbor Advisory
                    </p>
                  </div>
                </>
              )}
            </div>
          )}

          {step === 3 && (
            /* Success step */
            <div className="p-8 text-center">
              <div className="mx-auto w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mb-6">
                <CheckCircle2 className="w-8 h-8 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-3">
                You&apos;re all set!
              </h2>
              <p className="text-gray-600">
                Your company is ready. The full HR management suite is now
                unlocked.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
