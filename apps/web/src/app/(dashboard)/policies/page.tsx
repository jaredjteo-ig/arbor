"use client";

import { useState, useEffect } from "react";
import { AppCard } from "@/components/design-system";
import {
  FileText,
  ChevronDown,
  ChevronRight,
  Palmtree,
  Laptop,
  BookOpen,
  ShieldCheck,
  Info,
} from "lucide-react";
import { employeesApi, type CompanyPolicy } from "@/services/api/employees";

/* -- Types --------------------------------------------------------- */

interface PolicySection {
  id: string;
  title: string;
  icon: typeof Palmtree;
  summary: string;
  content: string[];
}

/* -- Standard Singapore policies (regulatory content) -------------- */

const STANDARD_POLICIES: PolicySection[] = [
  {
    id: "leave",
    title: "Leave Policy",
    icon: Palmtree,
    summary:
      "Annual, sick, and hospitalisation leave entitlements under the Employment Act.",
    content: [
      "Annual Leave: Employees are entitled to 7 days of annual leave after completing 12 months of service with the same employer. Entitlements increase progressively by 1 day per year of service, up to a maximum of 14 days.",
      "Sick Leave: Employees are entitled to 14 days of paid outpatient sick leave per year if they have been employed for at least 6 months. A valid medical certificate from a registered doctor is required.",
      "Hospitalisation Leave: Employees are entitled to up to 60 days of paid hospitalisation leave per year (inclusive of the 14 days outpatient sick leave). This applies to employees covered under the Employment Act.",
      "Pro-rated Leave: For employees who have not completed 12 months of service, leave entitlements are pro-rated based on the number of completed months of service.",
    ],
  },
  {
    id: "fwa",
    title: "Flexible Work Arrangements (FWA)",
    icon: Laptop,
    summary:
      "Guidelines for requesting and managing flexible work arrangements per MOM Tripartite Guidelines.",
    content: [
      "Eligibility: All employees who have completed their probation period may apply for flexible work arrangements. Requests should be submitted to your direct supervisor at least 2 weeks in advance.",
      "Types of FWA: The company supports various flexible work arrangements including flexi-time (varying start and end times), flexi-place (working from home or other locations), and flexi-load (part-time or job sharing arrangements).",
      "Request Process: Submit your FWA request through the HR portal or to your manager. The company will respond within 2 weeks. If declined, reasons will be provided in writing.",
      "Trial Period: New FWA arrangements are subject to a 3-month trial period. Performance will be reviewed regularly to ensure work objectives continue to be met.",
    ],
  },
  {
    id: "handbook",
    title: "Employee Handbook",
    icon: BookOpen,
    summary: "General employment terms, code of conduct, and company policies.",
    content: [
      "Working Hours: Standard working hours are from 9:00 AM to 6:00 PM, Monday through Friday, with a 1-hour lunch break. Overtime work may be required from time to time with prior approval from your supervisor.",
      "Notice Period: The notice period for termination of employment is aligned with the Employment Act. For employees with less than 26 weeks of service, 1 day notice is required. For 26 weeks to 2 years, 1 week. For 2 to 5 years, 2 weeks. For 5 years and above, 4 weeks.",
      "Code of Conduct: All employees are expected to maintain professional standards, respect colleagues, protect company property and confidential information, and comply with all relevant Singapore laws and regulations.",
      "Grievance Procedure: Employees who have concerns or grievances should first discuss them with their direct supervisor. If unresolved, they may escalate to HR or use the company's formal grievance process.",
    ],
  },
  {
    id: "safety",
    title: "Workplace Safety and Health",
    icon: ShieldCheck,
    summary:
      "Safety policies and reporting procedures under the Workplace Safety and Health Act.",
    content: [
      "General Safety: All employees are responsible for maintaining a safe working environment. Report any unsafe conditions immediately to your supervisor or the safety officer.",
      "Incident Reporting: All workplace incidents, injuries, and near-misses must be reported within 24 hours. Use the incident report form available on the HR portal or contact the safety officer directly.",
      "Emergency Procedures: Familiarise yourself with the emergency evacuation plan for your work area. Fire drills are conducted quarterly. Assembly points are clearly marked at all exits.",
      "Health and Wellness: The company provides annual health screening for all employees. Mental health support is available through our Employee Assistance Programme (EAP).",
    ],
  },
];

/* -- Icon mapping for API policies --------------------------------- */

const ICON_MAP: Record<string, typeof Palmtree> = {
  leave: Palmtree,
  fwa: Laptop,
  handbook: BookOpen,
  safety: ShieldCheck,
};

function mapApiPolicyToSection(policy: CompanyPolicy): PolicySection {
  return {
    id: policy.id,
    title: policy.title,
    icon: ICON_MAP[policy.id] ?? ICON_MAP[policy.category ?? ""] ?? FileText,
    summary: policy.summary,
    content: policy.content,
  };
}

/* -- Loading skeleton ---------------------------------------------- */

function PolicySkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse flex items-start gap-3">
        <div className="h-9 w-9 rounded-lg bg-[var(--color-gray-200)]" />
        <div className="flex-1">
          <div className="h-4 w-40 bg-[var(--color-gray-200)] rounded mb-2" />
          <div className="h-3 w-64 bg-[var(--color-gray-100)] rounded" />
        </div>
      </div>
    </AppCard>
  );
}

/* -- Expandable Policy Card ---------------------------------------- */

function PolicyCard({ policy }: { policy: PolicySection }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const Icon = policy.icon;

  return (
    <AppCard variant="flat" className="overflow-hidden">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-start gap-3 text-left"
      >
        <div className="p-2 rounded-lg bg-[var(--color-primary-bg)] shrink-0">
          <Icon className="h-5 w-5 text-[var(--color-primary)]" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-[var(--color-gray-900)]">
            {policy.title}
          </p>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            {policy.summary}
          </p>
        </div>
        <div className="shrink-0 mt-1 text-[var(--color-gray-400)]">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-[var(--color-gray-200)] space-y-3">
          {policy.content.map((paragraph, index) => (
            <p
              key={index}
              className="text-sm text-[var(--color-gray-700)] leading-relaxed"
            >
              {paragraph}
            </p>
          ))}
        </div>
      )}
    </AppCard>
  );
}

/* -- Page ---------------------------------------------------------- */

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<PolicySection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isStandardFallback, setIsStandardFallback] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchPolicies() {
      try {
        const data = await employeesApi.policies();
        if (!cancelled && data.policies && data.policies.length > 0) {
          setPolicies(data.policies.map(mapApiPolicyToSection));
          setIsStandardFallback(false);
        } else {
          if (!cancelled) {
            setPolicies(STANDARD_POLICIES);
            setIsStandardFallback(true);
          }
        }
      } catch {
        if (!cancelled) {
          setPolicies(STANDARD_POLICIES);
          setIsStandardFallback(true);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    fetchPolicies();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <FileText
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Company Policies
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Review company policies and employment guidelines. Click to expand
            each section.
          </p>
        </div>
      </div>

      {/* Standard policies notice */}
      {!isLoading && isStandardFallback && (
        <div className="flex items-start gap-2 rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-gray-50)] px-4 py-3">
          <Info className="h-4 w-4 text-[var(--color-gray-500)] mt-0.5 shrink-0" />
          <p className="text-sm text-[var(--color-gray-600)]">
            Standard Singapore employment policies. Your company may have
            additional policies.
          </p>
        </div>
      )}

      {/* Policy cards */}
      <div className="space-y-4">
        {isLoading
          ? [1, 2, 3, 4].map((n) => <PolicySkeleton key={n} />)
          : policies.map((policy) => (
              <PolicyCard key={policy.id} policy={policy} />
            ))}
      </div>
    </div>
  );
}
