"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ClipboardCheck,
  AlertCircle,
  Loader2,
} from "lucide-react";
import {
  AppCard,
  AppButton,
  RiskTierBadge,
  AlertBanner,
  SourceCitation,
} from "@/components/design-system";
import type { RiskTierLevel } from "@/components/design-system";
import { AskArborButton } from "@/components/shared/AskArborButton";
import { InlineAnnotation } from "@/components/shadow-agent";
import type { AnnotationData } from "@/components/shadow-agent";
import { useAuth } from "@/contexts/AuthContext";
import {
  useComplianceStatus,
  useComplianceCheck,
} from "@/hooks/api/useCompliance";
import type {
  ComplianceStatusResponse,
  ComplianceCheckResponse,
} from "@/types/api";

/* -- Types -------------------------------------------------------- */

interface Finding {
  domain: string;
  issue: string;
  severity: "critical" | "high" | "medium" | "low";
  recommendation: string;
  provision_id: string;
  deadline: string;
}

interface InspectionItem {
  category: string;
  item: string;
  status: "pass" | "fail" | "unknown";
  provision: string;
}

interface CombinedResult {
  score: number;
  risk_tier: string;
  findings: Finding[];
  action_items: string[];
  domains_checked: string[];
  inspection_readiness: InspectionItem[];
  backendStatus: ComplianceCheckResponse | null;
}

/* -- Domain labels ------------------------------------------------ */

const DOMAIN_LABELS: Record<string, string> = {
  employment_act: "Employment Act",
  cpf: "Central Provident Fund (CPF)",
  foreign_manpower: "Foreign Manpower (EFMA)",
  tax: "Tax / IRAS",
  wsh: "Workplace Safety and Health (WSH)",
};

function domainStatusToTier(status: string): RiskTierLevel {
  if (status === "covered") return "green";
  if (status === "sparse") return "amber";
  return "red";
}

/* -- Client-side checklist logic ---------------------------------- */

function runLocalComplianceCheck(
  inputs: Record<string, boolean>,
  companySize: number,
  hasForeign: boolean,
): {
  findings: Finding[];
  action_items: string[];
  inspection_readiness: InspectionItem[];
} {
  const findings: Finding[] = [];
  const action_items: string[] = [];

  if (!inputs.ket) {
    findings.push({
      domain: "Employment Act",
      issue: "Key Employment Terms (KET) not issued to employees",
      severity: "critical",
      recommendation:
        "Issue KET to all employees within 14 days of employment start. Fine up to $5,000 per offence.",
      provision_id: "EA-S95-KETs",
      deadline: "Immediate",
    });
    action_items.push("Issue KET documents to all current employees");
  }
  if (!inputs.contracts) {
    findings.push({
      domain: "Employment Act",
      issue: "No written employment contracts in place",
      severity: "high",
      recommendation: "Provide written contracts to all employees.",
      provision_id: "EA-KET",
      deadline: "Within 30 days",
    });
    action_items.push("Prepare and issue written employment contracts");
  }
  if (!inputs.payslips) {
    findings.push({
      domain: "Employment Act",
      issue: "No itemised payslip system in place",
      severity: "critical",
      recommendation:
        "Implement itemised payslips for every salary payment. Fine up to $5,000 per offence (EA s88A).",
      provision_id: "EA-S88A-payslip",
      deadline: "Immediate",
    });
    action_items.push("Set up itemised payslip system");
  }
  if (!inputs.leave) {
    findings.push({
      domain: "Employment Act",
      issue: "No leave records maintained",
      severity: "high",
      recommendation: "Maintain accurate leave records for all employees.",
      provision_id: "EA-PART-X-annual-leave",
      deadline: "Within 14 days",
    });
    action_items.push("Set up leave tracking system");
  }
  if (!inputs.ot) {
    findings.push({
      domain: "Employment Act",
      issue: "No overtime records maintained",
      severity: "high",
      recommendation: "Maintain OT records for all Part IV eligible employees.",
      provision_id: "EA-PART-IV-hours",
      deadline: "Within 14 days",
    });
    action_items.push("Set up overtime tracking");
  }
  if (!inputs.safety && (hasForeign || companySize >= 10)) {
    findings.push({
      domain: "Workplace Safety & Health",
      issue: "No workplace safety and health policy",
      severity: "high",
      recommendation: "Develop and implement a WSH policy.",
      provision_id: "WSHA-S12",
      deadline: "Within 30 days",
    });
    action_items.push("Develop workplace safety policy");
  }
  if (!inputs.grievance) {
    findings.push({
      domain: "Fair Employment",
      issue: "No formal grievance handling process",
      severity: "medium",
      recommendation: "Establish a grievance handling process per TGFEP.",
      provision_id: "TGFEP-GRIEVANCE",
      deadline: "Within 60 days",
    });
    action_items.push("Establish grievance handling process");
  }
  if (!inputs.fwa) {
    findings.push({
      domain: "Fair Employment",
      issue: "No FWA policy in place",
      severity: "medium",
      recommendation:
        "Implement FWA policy per TG-FWAR guidelines (effective 1 Dec 2024).",
      provision_id: "TGFWAR-request-process",
      deadline: "Within 60 days",
    });
    action_items.push("Draft FWA policy");
  }

  const inspection_readiness: InspectionItem[] = [
    {
      category: "Employment Records",
      item: "KET issued to all employees",
      status: inputs.ket ? "pass" : "fail",
      provision: "EA s95A",
    },
    {
      category: "Employment Records",
      item: "Written contracts available",
      status: inputs.contracts ? "pass" : "fail",
      provision: "EA",
    },
    {
      category: "Salary Records",
      item: "Itemised payslips issued",
      status: inputs.payslips ? "pass" : "fail",
      provision: "EA s88A",
    },
    {
      category: "Leave & Hours",
      item: "Leave records maintained",
      status: inputs.leave ? "pass" : "fail",
      provision: "EA Part XII",
    },
    {
      category: "Leave & Hours",
      item: "Overtime records maintained",
      status: inputs.ot ? "pass" : "fail",
      provision: "EA Part IV",
    },
    {
      category: "Safety",
      item: "WSH policy in place",
      status: inputs.safety ? "pass" : companySize >= 10 ? "fail" : "unknown",
      provision: "WSH Act",
    },
    {
      category: "Fair Employment",
      item: "Grievance process",
      status: inputs.grievance ? "pass" : "unknown",
      provision: "TGFEP",
    },
    {
      category: "Fair Employment",
      item: "FWA policy",
      status: inputs.fwa ? "pass" : "unknown",
      provision: "TG-FWAR",
    },
  ];

  return { findings, action_items, inspection_readiness };
}

/* -- Checklist items --------------------------------------------- */

const CHECKS = [
  {
    key: "ket",
    label: "KET issued to all employees",
    help: "Key Employment Terms document per EA s95A",
  },
  {
    key: "contracts",
    label: "Written employment contracts in place",
    help: "For all employees",
  },
  {
    key: "payslips",
    label: "Itemised payslip system operational",
    help: "EA s88A requirement",
  },
  {
    key: "leave",
    label: "Leave records maintained",
    help: "EA Part XII compliance",
  },
  {
    key: "ot",
    label: "Overtime records maintained",
    help: "EA Part IV for eligible employees",
  },
  {
    key: "safety",
    label: "Workplace safety policy in place",
    help: "WSH Act requirement",
  },
  {
    key: "grievance",
    label: "Grievance handling process established",
    help: "TGFEP recommendation",
  },
  {
    key: "fwa",
    label: "FWA policy implemented",
    help: "TG-FWAR effective Dec 2024",
  },
] as const;

/* -- Compliance annotation map (T122) ----------------------------- */

const COMPLIANCE_ANNOTATIONS: Record<string, AnnotationData> = {
  ket: {
    id: "anno-ket",
    text: "Employers must issue KET within 14 days of employment start. Non-compliance may result in a fine.",
    severity: "high",
    provision: "EA s95A",
    fineAmount: "Up to $5,000 per offence",
  },
  contracts: {
    id: "anno-contracts",
    text: "Written contracts are a best practice and support KET compliance. Strongly recommended for all employees.",
    severity: "medium",
    provision: "EA Part II",
  },
  payslips: {
    id: "anno-payslips",
    text: "Itemised payslips must be provided for every salary payment. Non-compliance may result in a fine.",
    severity: "high",
    provision: "EA s88A",
    fineAmount: "Up to $5,000 per offence",
  },
  leave: {
    id: "anno-leave",
    text: "Employers must maintain leave records for at least 2 years. MOM may request these during inspections.",
    severity: "medium",
    provision: "EA Part XII",
    fineAmount: "Up to $5,000",
  },
  ot: {
    id: "anno-ot",
    text: "Overtime records are mandatory for Part IV employees (salary up to $2,600). OT pay is 1.5x hourly rate.",
    severity: "medium",
    provision: "EA Part IV",
    fineAmount: "Up to $5,000",
  },
  safety: {
    id: "anno-safety",
    text: "Employers must ensure a safe workplace. Higher obligations for companies with 10+ employees or hazardous work.",
    severity: "high",
    provision: "WSH Act s12",
    fineAmount: "Up to $200,000 and/or 12 months jail",
  },
  grievance: {
    id: "anno-grievance",
    text: "A formal grievance process is recommended under the Tripartite Guidelines on Fair Employment Practices.",
    severity: "low",
    provision: "TGFEP",
  },
  fwa: {
    id: "anno-fwa",
    text: "From 1 Dec 2024, employers must have a process to fairly consider FWA requests under TG-FWAR.",
    severity: "low",
    provision: "TG-FWAR",
  },
};

/* -- Loading skeleton -------------------------------------------- */

function ComplianceSkeleton() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-7 w-7 rounded bg-[var(--color-gray-200)] animate-pulse" />
        <div className="space-y-2">
          <div className="h-6 w-56 rounded bg-[var(--color-gray-200)] animate-pulse" />
          <div className="h-4 w-80 rounded bg-[var(--color-gray-200)] animate-pulse" />
        </div>
      </div>
      <div className="h-24 rounded-xl bg-[var(--color-gray-200)] animate-pulse" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-16 rounded-lg bg-[var(--color-gray-200)] animate-pulse"
            />
          ))}
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 rounded-lg bg-[var(--color-gray-200)] animate-pulse"
            />
          ))}
        </div>
      </div>
    </div>
  );
}

/* -- Page -------------------------------------------------------- */

export default function CompliancePage() {
  const router = useRouter();
  const { user } = useAuth();
  const companyId = user?.company_id ?? 0;

  /* Backend compliance status */
  const {
    data: backendStatus,
    isPending: statusLoading,
    error: statusError,
  } = useComplianceStatus(companyId);

  /* Backend compliance check mutation */
  const complianceCheckMutation = useComplianceCheck();

  /* Checklist state */
  const [inputs, setInputs] = useState<Record<string, boolean>>(
    Object.fromEntries(CHECKS.map((c) => [c.key, false])),
  );
  const [companySize, setCompanySize] = useState("10");
  const [hasForeign, setHasForeign] = useState(false);
  const [result, setResult] = useState<CombinedResult | null>(null);
  const [activeTab, setActiveTab] = useState<"findings" | "inspection">(
    "findings",
  );

  const toggle = (key: string) =>
    setInputs((prev) => ({ ...prev, [key]: !prev[key] }));

  /* Run combined compliance check */
  const handleCheck = async () => {
    const local = runLocalComplianceCheck(
      inputs,
      parseInt(companySize) || 10,
      hasForeign,
    );

    let backendCheckResult: ComplianceCheckResponse | null = null;

    /* If the user has a company, also call the backend */
    if (companyId > 0) {
      try {
        backendCheckResult = await complianceCheckMutation.mutateAsync({
          company_id: companyId,
        });
      } catch {
        /* Backend call failed; we still show local results */
      }
    }

    /* Score: start from 100, deduct for local findings */
    let score = 100;
    const deductions: Record<string, number> = {
      critical: 20,
      high: 10,
      medium: 5,
      low: 2,
    };
    for (const f of local.findings) score -= deductions[f.severity] ?? 0;

    /* Also deduct for backend gaps if any */
    if (backendCheckResult) {
      for (const finding of backendCheckResult.findings) {
        if (
          finding.status === "missing" ||
          (finding.gaps && finding.gaps > 0)
        ) {
          score -= 10;
        }
      }
    }
    score = Math.max(0, score);

    const risk_tier = score >= 80 ? "green" : score >= 50 ? "amber" : "red";
    const domains_checked = [
      "Employment Act",
      "CPF",
      "Workplace Safety & Health",
      "Fair Employment",
    ];
    if (hasForeign) domains_checked.push("Foreign Manpower");

    setResult({
      score,
      risk_tier,
      findings: local.findings,
      action_items: local.action_items,
      domains_checked,
      inspection_readiness: local.inspection_readiness,
      backendStatus: backendCheckResult,
    });
  };

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

  /* No company ID: prompt user to set up profile */
  if (!user?.company_id) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <Shield
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Compliance Health Check
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Verify your compliance posture across Singapore employment
              regulations.
            </p>
          </div>
        </div>

        <AlertBanner
          variant="info"
          title="Company Profile Required"
          description="Set up your company profile to run compliance checks against the knowledge base and get personalised compliance status."
        />

        <AppButton
          variant="primary"
          onClick={() => router.push("/profile")}
          className="w-full sm:w-auto"
        >
          Set Up Company Profile
        </AppButton>

        <div className="pt-2">
          <p className="text-sm text-[var(--color-gray-500)]">
            You can still run a quick self-assessment checklist below while you
            set up your profile.
          </p>
        </div>

        {/* Still show the checklist form for users without a company */}
        <ChecklistForm
          inputs={inputs}
          companySize={companySize}
          hasForeign={hasForeign}
          onToggle={toggle}
          onCompanySizeChange={setCompanySize}
          onHasForeignChange={setHasForeign}
          onCheck={handleCheck}
          isChecking={complianceCheckMutation.isPending}
        />

        {result && (
          <ResultsView
            result={result}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onReset={() => setResult(null)}
            severityColor={severityColor}
            severityBg={severityBg}
          />
        )}
      </div>
    );
  }

  /* Loading backend status */
  if (statusLoading) {
    return <ComplianceSkeleton />;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Shield
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Compliance Health Check
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Verify your compliance posture across Singapore employment
            regulations.
          </p>
        </div>
      </div>

      {/* Backend compliance status overview */}
      {backendStatus && <BackendStatusOverview status={backendStatus} />}

      {statusError && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>
            Unable to load compliance status from the knowledge base. The
            self-assessment checklist below is still available.
          </span>
        </div>
      )}

      {/* Checklist input form */}
      {!result && (
        <ChecklistForm
          inputs={inputs}
          companySize={companySize}
          hasForeign={hasForeign}
          onToggle={toggle}
          onCompanySizeChange={setCompanySize}
          onHasForeignChange={setHasForeign}
          onCheck={handleCheck}
          isChecking={complianceCheckMutation.isPending}
        />
      )}

      {/* Combined results */}
      {result && (
        <ResultsView
          result={result}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onReset={() => setResult(null)}
          severityColor={severityColor}
          severityBg={severityBg}
        />
      )}
    </div>
  );
}

/* -- Backend Status Overview ------------------------------------- */

function BackendStatusOverview({
  status,
}: {
  status: ComplianceStatusResponse;
}) {
  const domainEntries = Object.entries(status.domains);
  const coveredCount = domainEntries.filter(
    ([, d]) => d.status === "covered",
  ).length;
  const totalDomains = domainEntries.length;
  const scorePercent =
    totalDomains > 0 ? Math.round((coveredCount / totalDomains) * 100) : 0;

  const overallTier: RiskTierLevel =
    status.overall_status === "compliant"
      ? "green"
      : status.overall_status === "review_needed"
        ? "amber"
        : "red";

  return (
    <AppCard variant="elevated">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
              Knowledge Base Compliance Status
            </p>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-3xl font-bold text-[var(--color-gray-900)]">
                {coveredCount}/{totalDomains}
              </span>
              <span className="text-sm text-[var(--color-gray-500)]">
                domains covered
              </span>
              <RiskTierBadge tier={overallTier} />
            </div>
            <p className="text-xs text-[var(--color-gray-400)] mt-1">
              {status.total_provisions} total provisions in knowledge base
            </p>
          </div>
          <div
            className="w-16 h-16 rounded-full border-4 flex items-center justify-center"
            style={{
              borderColor:
                overallTier === "green"
                  ? "var(--color-risk-green)"
                  : overallTier === "amber"
                    ? "var(--color-risk-amber)"
                    : "var(--color-risk-red)",
            }}
          >
            <span className="text-lg font-bold">{scorePercent}%</span>
          </div>
        </div>

        {/* Per-domain status */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {domainEntries.map(([domain, domainStatus]) => {
            const tier = domainStatusToTier(domainStatus.status);
            const domainLabel = DOMAIN_LABELS[domain] ?? domain;
            return (
              <div
                key={domain}
                className="flex flex-col gap-2 p-2.5 rounded-lg bg-[var(--color-surface-card)] border border-[var(--color-gray-200)]"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--color-gray-900)] truncate">
                      {domainLabel}
                    </p>
                    <p className="text-xs text-[var(--color-gray-400)]">
                      {domainStatus.provisions_count} provision
                      {domainStatus.provisions_count !== 1 ? "s" : ""}
                    </p>
                  </div>
                  <RiskTierBadge tier={tier} className="text-xs shrink-0" />
                </div>
                {(tier === "amber" || tier === "red") && (
                  <AskArborButton
                    question={`My ${domainLabel} compliance is ${tier === "amber" ? "medium risk" : "high risk"}. What do I need to fix?`}
                    variant="subtle"
                    className="text-xs"
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </AppCard>
  );
}

/* -- Checklist Form ---------------------------------------------- */

function ChecklistForm({
  inputs,
  companySize,
  hasForeign,
  onToggle,
  onCompanySizeChange,
  onHasForeignChange,
  onCheck,
  isChecking,
}: {
  inputs: Record<string, boolean>;
  companySize: string;
  hasForeign: boolean;
  onToggle: (key: string) => void;
  onCompanySizeChange: (value: string) => void;
  onHasForeignChange: (value: boolean) => void;
  onCheck: () => void;
  isChecking: boolean;
}) {
  return (
    <>
      <AppCard variant="standard">
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Company Profile
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-1">
                Number of employees
              </label>
              <input
                type="number"
                value={companySize}
                onChange={(e) => onCompanySizeChange(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-gray-200)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                min="1"
              />
            </div>
            <div className="flex items-center gap-3 pt-6">
              <input
                type="checkbox"
                id="foreign"
                checked={hasForeign}
                onChange={() => onHasForeignChange(!hasForeign)}
                className="h-4 w-4 rounded border-[var(--color-gray-300)]"
              />
              <label
                htmlFor="foreign"
                className="text-sm text-[var(--color-gray-700)]"
              >
                Company employs foreign workers
              </label>
            </div>
          </div>
        </div>
      </AppCard>

      <AppCard variant="standard">
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Compliance Checklist
          </h3>
          <p className="text-xs text-[var(--color-gray-500)]">
            Check each item that your company currently has in place. This will
            be combined with knowledge base analysis for a complete compliance
            picture.
          </p>
          {CHECKS.map((check) => {
            const annotation = COMPLIANCE_ANNOTATIONS[check.key];
            return (
              <div key={check.key}>
                <label className="flex items-start gap-3 p-3 rounded-lg hover:bg-[var(--color-gray-50)] cursor-pointer transition-colors">
                  <input
                    type="checkbox"
                    checked={inputs[check.key]}
                    onChange={() => onToggle(check.key)}
                    className="h-4 w-4 rounded border-[var(--color-gray-300)] mt-0.5"
                  />
                  <div>
                    <p className="text-sm font-medium text-[var(--color-gray-900)]">
                      {check.label}
                    </p>
                    <p className="text-xs text-[var(--color-gray-500)]">
                      {check.help}
                    </p>
                  </div>
                </label>
                {annotation && (
                  <div className="ml-7 mt-1 mb-2">
                    <InlineAnnotation annotation={annotation} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </AppCard>

      <AppButton
        onClick={onCheck}
        className="w-full sm:w-auto"
        disabled={isChecking}
      >
        {isChecking ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Running Compliance Check...
          </>
        ) : (
          "Run Compliance Check"
        )}
      </AppButton>
    </>
  );
}

/* -- Results View ------------------------------------------------ */

function ResultsView({
  result,
  activeTab,
  onTabChange,
  onReset,
  severityColor,
  severityBg,
}: {
  result: CombinedResult;
  activeTab: "findings" | "inspection";
  onTabChange: (tab: "findings" | "inspection") => void;
  onReset: () => void;
  severityColor: Record<string, string>;
  severityBg: Record<string, string>;
}) {
  return (
    <>
      {/* Score gauge */}
      <AppCard variant="elevated">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-[var(--color-gray-500)]">
              Combined Compliance Score
            </p>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-4xl font-bold text-[var(--color-gray-900)]">
                {result.score}
              </span>
              <span className="text-lg text-[var(--color-gray-400)]">
                / 100
              </span>
              <RiskTierBadge tier={result.risk_tier as RiskTierLevel} />
            </div>
            <p className="text-xs text-[var(--color-gray-500)] mt-1">
              {result.findings.length} finding
              {result.findings.length !== 1 ? "s" : ""} across{" "}
              {result.domains_checked.length} domains
              {result.backendStatus && " (includes KB analysis)"}
            </p>
          </div>
          <div
            className="w-20 h-20 rounded-full border-4 flex items-center justify-center"
            style={{
              borderColor:
                result.risk_tier === "green"
                  ? "var(--color-risk-green)"
                  : result.risk_tier === "amber"
                    ? "var(--color-risk-amber)"
                    : "var(--color-risk-red)",
            }}
          >
            <span className="text-xl font-bold">{result.score}%</span>
          </div>
        </div>
      </AppCard>

      {/* Backend KB findings */}
      {result.backendStatus && (
        <AppCard variant="standard">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
            Knowledge Base Coverage
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mb-3">
            The knowledge base was checked for regulatory provisions in each
            domain. Domains marked as missing or sparse need more provisions
            loaded.
          </p>
          <div className="space-y-2">
            {result.backendStatus.findings.map((finding, i) => (
              <div
                key={i}
                className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-[var(--color-surface-card)] border border-[var(--color-gray-200)]"
              >
                <div className="flex items-center gap-2">
                  {finding.status === "covered" ? (
                    <CheckCircle2 className="h-4 w-4 text-[var(--color-risk-green)]" />
                  ) : (
                    <XCircle className="h-4 w-4 text-[var(--color-risk-red)]" />
                  )}
                  <span className="text-sm text-[var(--color-gray-900)]">
                    {DOMAIN_LABELS[finding.domain] ?? finding.domain}
                  </span>
                </div>
                <span className="text-xs text-[var(--color-gray-400)]">
                  {finding.provisions_checked} provision
                  {finding.provisions_checked !== 1 ? "s" : ""}
                </span>
              </div>
            ))}
          </div>
          {result.backendStatus.recommendations &&
            result.backendStatus.recommendations.length > 0 && (
              <div className="mt-3 p-3 rounded-lg bg-amber-50 border border-amber-200">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-700 mb-1">
                  KB Recommendations
                </h4>
                <ul className="space-y-1">
                  {result.backendStatus.recommendations.map((rec, i) => (
                    <li
                      key={i}
                      className="text-sm text-amber-900 leading-relaxed"
                    >
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
        </AppCard>
      )}

      {/* Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => onTabChange("findings")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeTab === "findings"
              ? "bg-[var(--color-primary)] text-white"
              : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)]"
          }`}
        >
          Findings ({result.findings.length})
        </button>
        <button
          onClick={() => onTabChange("inspection")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
            activeTab === "inspection"
              ? "bg-[var(--color-primary)] text-white"
              : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)]"
          }`}
        >
          <ClipboardCheck className="h-4 w-4" /> MOM Inspection Readiness
        </button>
      </div>

      {/* Findings tab */}
      {activeTab === "findings" && (
        <div className="space-y-3">
          {(["critical", "high", "medium", "low"] as const).map((sev) => {
            const items = result.findings.filter((f) => f.severity === sev);
            if (items.length === 0) return null;
            return (
              <div key={sev}>
                <p
                  className="text-xs font-semibold uppercase tracking-wider mb-2"
                  style={{ color: severityColor[sev] }}
                >
                  {sev} ({items.length})
                </p>
                {items.map((f, i) => (
                  <AppCard key={i} variant="standard">
                    <div className="flex items-start gap-3">
                      <div
                        className="px-2 py-0.5 rounded text-xs font-semibold uppercase shrink-0"
                        style={{
                          backgroundColor: severityBg[f.severity],
                          color: severityColor[f.severity],
                        }}
                      >
                        {f.severity}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[var(--color-gray-900)]">
                          {f.issue}
                        </p>
                        <p className="text-xs text-[var(--color-gray-600)] mt-1">
                          {f.recommendation}
                        </p>
                        <div className="flex items-center gap-3 mt-2">
                          <span className="text-xs text-[var(--color-gray-400)]">
                            {f.domain}
                          </span>
                          <span className="text-xs text-[var(--color-gray-400)]">
                            Deadline: {f.deadline}
                          </span>
                          <SourceCitation
                            label={f.provision_id}
                            authority="statutory"
                          />
                        </div>
                      </div>
                    </div>
                  </AppCard>
                ))}
              </div>
            );
          })}

          {/* Action items */}
          {result.action_items.length > 0 && (
            <AppCard variant="standard">
              <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-2">
                Action Items
              </h3>
              <div className="space-y-2">
                {result.action_items.map((item, i) => (
                  <label key={i} className="flex items-start gap-2">
                    <input type="checkbox" className="h-4 w-4 rounded mt-0.5" />
                    <span className="text-sm text-[var(--color-gray-700)]">
                      {item}
                    </span>
                  </label>
                ))}
              </div>
            </AppCard>
          )}
        </div>
      )}

      {/* Inspection readiness tab */}
      {activeTab === "inspection" && (
        <div className="space-y-3">
          {[
            "Employment Records",
            "Salary Records",
            "Leave & Hours",
            "Safety",
            "Fair Employment",
          ].map((cat) => {
            const items = result.inspection_readiness.filter(
              (i) => i.category === cat,
            );
            if (items.length === 0) return null;
            return (
              <AppCard key={cat} variant="standard">
                <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
                  {cat}
                </h3>
                <div className="space-y-2">
                  {items.map((item, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between py-1.5"
                    >
                      <div className="flex items-center gap-2">
                        {item.status === "pass" && (
                          <CheckCircle2 className="h-4 w-4 text-[var(--color-risk-green)]" />
                        )}
                        {item.status === "fail" && (
                          <XCircle className="h-4 w-4 text-[var(--color-risk-red)]" />
                        )}
                        {item.status === "unknown" && (
                          <HelpCircle className="h-4 w-4 text-[var(--color-gray-400)]" />
                        )}
                        <span className="text-sm text-[var(--color-gray-700)]">
                          {item.item}
                        </span>
                      </div>
                      <span className="text-xs text-[var(--color-gray-400)]">
                        {item.provision}
                      </span>
                    </div>
                  ))}
                </div>
              </AppCard>
            );
          })}
        </div>
      )}

      {/* Ask Arbor about compliance results */}
      {(result.risk_tier === "amber" || result.risk_tier === "red") && (
        <AskArborButton
          question={`My compliance score is ${result.score}/100 (${result.risk_tier === "amber" ? "medium" : "high"} risk) with ${result.findings.length} findings. What should I prioritise fixing?`}
        />
      )}

      {/* Reset */}
      <AppButton variant="text" onClick={onReset}>
        Run Another Check
      </AppButton>
    </>
  );
}
