"use client";

import { useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Gavel,
  HeartPulse,
  UserX,
  FileSearch,
  ShieldAlert,
  Download,
  Phone,
  CheckSquare,
  Square,
  ChevronRight,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  AppCard,
  AppButton,
  SourceCitation,
  AlertBanner,
} from "@/components/design-system";
import type { AuthorityLevel } from "@/components/design-system";
import {
  useEmergencyScenarios,
  useEmergencyEscalate,
} from "@/hooks/api/useEmergency";
import type { EmergencyScenario } from "@/types/api";

/* ── Icon mapping (Material icon names to Lucide components) ──── */

const ICON_MAP: Record<string, typeof Gavel> = {
  gavel: Gavel,
  local_hospital: HeartPulse,
  person_off: UserX,
  policy: FileSearch,
  report_problem: AlertTriangle,
  security: ShieldAlert,
};

/* ── Provision authority mapping ─────────────────────────────── */

function getAuthorityLevel(provision: string): AuthorityLevel {
  if (
    provision.startsWith("EA-") ||
    provision.startsWith("WICA-") ||
    provision.startsWith("WSH-") ||
    provision.startsWith("PDPA-") ||
    provision.startsWith("EFMA-") ||
    provision.startsWith("TADM-") ||
    provision.startsWith("WFA-")
  ) {
    return "statutory";
  }
  if (
    provision.startsWith("TGFEP-") ||
    provision.startsWith("TAFEP-") ||
    provision.startsWith("TGFWAR-")
  ) {
    return "guideline";
  }
  return "best-practice";
}

/* ── Topic display order ─────────────────────────────────────── */

const TOPIC_ORDER = [
  "tadm-claim",
  "workplace-injury",
  "wrongful-dismissal",
  "mom-inspection",
  "discrimination-complaint",
  "data-breach",
] as const;

/* ── Loading skeleton ────────────────────────────────────────── */

function EmergencySkeleton() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-7 w-7 rounded bg-[var(--color-gray-200)] animate-pulse" />
        <div className="space-y-2">
          <div className="h-6 w-56 rounded bg-[var(--color-gray-200)] animate-pulse" />
          <div className="h-4 w-72 rounded bg-[var(--color-gray-200)] animate-pulse" />
        </div>
      </div>
      <div className="h-16 rounded-xl bg-amber-50 animate-pulse" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className="h-32 rounded-xl bg-[var(--color-gray-200)] animate-pulse"
          />
        ))}
      </div>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────── */

export default function EmergencyPage() {
  const { data, isPending, error } = useEmergencyScenarios();
  const escalateMutation = useEmergencyEscalate();

  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [checkedDocs, setCheckedDocs] = useState<Record<string, boolean>>({});

  const scenarios = data?.scenarios ?? [];

  // Build lookup map
  const scenarioMap: Record<string, EmergencyScenario> = {};
  for (const s of scenarios) {
    scenarioMap[s.topic_id] = s;
  }

  const toggleDoc = (doc: string) =>
    setCheckedDocs((prev) => ({ ...prev, [doc]: !prev[doc] }));

  const resetToHub = () => {
    setSelectedTopic(null);
    setCheckedDocs({});
  };

  /* ── Loading / Error states ────────────────────────────────── */

  if (isPending) return <EmergencySkeleton />;

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <AppCard variant="standard">
          <div className="text-center py-8">
            <AlertCircle className="h-10 w-10 text-red-400 mx-auto mb-3" />
            <p className="text-[var(--color-gray-700)] font-medium">
              Unable to load emergency guides
            </p>
            <p className="text-sm text-[var(--color-gray-500)] mt-1">
              {error.message}
            </p>
          </div>
        </AppCard>
      </div>
    );
  }

  /* ── Detail View ─────────────────────────────────────────── */

  if (selectedTopic) {
    const topic = scenarioMap[selectedTopic];
    if (!topic) {
      setSelectedTopic(null);
      return null;
    }

    const TopicIcon = ICON_MAP[topic.icon] ?? AlertTriangle;

    return (
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Back button */}
        <button
          onClick={resetToHub}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-gray-600)] hover:text-[var(--color-gray-900)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to Emergency Hub
        </button>

        {/* Red-styled header */}
        <div
          className="rounded-[12px] px-6 py-5"
          style={{
            backgroundColor: "var(--color-risk-red-bg)",
            border: "1px solid var(--color-risk-red)",
          }}
        >
          <div className="flex items-start gap-4">
            <div
              className="flex items-center justify-center w-12 h-12 rounded-full shrink-0"
              style={{ backgroundColor: "var(--color-risk-red)" }}
            >
              <TopicIcon className="h-6 w-6 text-white" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[var(--color-gray-900)]">
                {topic.title}
              </h1>
              <p className="text-sm text-[var(--color-gray-700)] mt-1">
                {topic.description}
              </p>
            </div>
          </div>
        </div>

        {/* Section 1: Immediate Obligations */}
        <AppCard variant="standard">
          <h2 className="text-base font-bold text-[var(--color-gray-900)] mb-4">
            Your Immediate Obligations
          </h2>
          <div className="space-y-4">
            {topic.immediate_obligations.map((step) => (
              <div key={step.step_number} className="flex items-start gap-4">
                <div
                  className="flex items-center justify-center w-8 h-8 rounded-full shrink-0 text-sm font-bold text-white"
                  style={{ backgroundColor: "var(--color-risk-red)" }}
                >
                  {step.step_number}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-[var(--color-gray-900)]">
                      {step.action}
                    </p>
                    <span
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold"
                      style={{
                        backgroundColor: "var(--color-risk-red-bg)",
                        color: "var(--color-risk-red)",
                        border: "1px solid var(--color-risk-red)",
                      }}
                    >
                      {step.deadline}
                    </span>
                  </div>
                  <p className="text-sm text-[var(--color-gray-600)] mt-1">
                    {step.detail}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </AppCard>

        {/* Section 2: Documents You Need to Gather */}
        <AppCard variant="standard">
          <h2 className="text-base font-bold text-[var(--color-gray-900)] mb-4">
            Documents You Need to Gather
          </h2>
          <div className="space-y-2">
            {topic.documents_needed.map((doc) => {
              const isChecked = checkedDocs[doc] ?? false;
              return (
                <label
                  key={doc}
                  className="flex items-start gap-3 p-2.5 rounded-lg hover:bg-[var(--color-gray-50)] cursor-pointer transition-colors"
                >
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={isChecked}
                    onClick={() => toggleDoc(doc)}
                    className="shrink-0 mt-0.5"
                  >
                    {isChecked ? (
                      <CheckSquare
                        className="h-5 w-5"
                        style={{ color: "var(--color-risk-green, #16a34a)" }}
                        aria-hidden="true"
                      />
                    ) : (
                      <Square
                        className="h-5 w-5 text-[var(--color-gray-400)]"
                        aria-hidden="true"
                      />
                    )}
                  </button>
                  <span
                    className={`text-sm ${
                      isChecked
                        ? "text-[var(--color-gray-400)] line-through"
                        : "text-[var(--color-gray-700)]"
                    }`}
                  >
                    {doc}
                  </span>
                </label>
              );
            })}
          </div>
          <div className="mt-3 pt-3 border-t border-[var(--color-gray-200)]">
            <p className="text-xs text-[var(--color-gray-500)]">
              {Object.values(checkedDocs).filter(Boolean).length} of{" "}
              {topic.documents_needed.length} documents gathered
            </p>
          </div>
        </AppCard>

        {/* Section 3: Step-by-Step Process */}
        <AppCard variant="standard">
          <h2 className="text-base font-bold text-[var(--color-gray-900)] mb-4">
            Step-by-Step Process
          </h2>
          <div className="relative">
            {/* Vertical timeline line */}
            <div
              className="absolute left-[15px] top-4 bottom-4 w-0.5"
              style={{ backgroundColor: "var(--color-gray-200)" }}
            />
            <div className="space-y-6">
              {topic.process_steps.map((step, idx) => (
                <div
                  key={step.step_number}
                  className="relative flex items-start gap-4"
                >
                  {/* Step circle on the timeline */}
                  <div
                    className="relative z-10 flex items-center justify-center w-8 h-8 rounded-full shrink-0 text-sm font-bold border-2"
                    style={{
                      borderColor: "var(--color-primary)",
                      backgroundColor:
                        idx === 0
                          ? "var(--color-primary)"
                          : "var(--color-surface-card, white)",
                      color: idx === 0 ? "white" : "var(--color-primary)",
                    }}
                  >
                    {step.step_number}
                  </div>
                  <div className="flex-1 min-w-0 pb-1">
                    <p className="text-sm font-semibold text-[var(--color-gray-900)]">
                      {step.action}
                    </p>
                    <span
                      className="inline-flex items-center mt-1.5 px-2 py-0.5 rounded text-xs font-medium"
                      style={{
                        backgroundColor: "var(--color-primary-bg)",
                        color: "var(--color-primary)",
                      }}
                    >
                      {step.deadline}
                    </span>
                    <p className="text-sm text-[var(--color-gray-600)] mt-1.5">
                      {step.detail}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </AppCard>

        {/* Section 4: When to Get Professional Help */}
        <AppCard
          variant="standard"
          className="border-l-4"
          style={{
            borderLeftColor: "var(--color-risk-amber)",
          }}
        >
          <h2 className="text-base font-bold text-[var(--color-gray-900)] mb-4">
            When to Get Professional Help
          </h2>
          <div className="space-y-3">
            {topic.when_to_get_help.map((item) => (
              <div key={item} className="flex items-start gap-3">
                <AlertTriangle
                  className="h-4 w-4 shrink-0 mt-0.5"
                  style={{ color: "var(--color-risk-amber)" }}
                  aria-hidden="true"
                />
                <p className="text-sm text-[var(--color-gray-700)]">{item}</p>
              </div>
            ))}
          </div>
          <div className="mt-5">
            <AppButton
              variant="danger"
              size="lg"
              className="w-full sm:w-auto"
              onClick={() => {
                escalateMutation.mutate({
                  topic_id: topic.topic_id,
                  description: `Emergency escalation requested for: ${topic.title}`,
                  urgency: "high",
                });
              }}
              disabled={escalateMutation.isPending}
            >
              {escalateMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Phone className="h-4 w-4" aria-hidden="true" />
              )}
              Connect to Employment Law Specialist
            </AppButton>
            {escalateMutation.isSuccess && (
              <p className="text-sm text-green-700 mt-2">
                {escalateMutation.data.message}
              </p>
            )}
            {escalateMutation.isError && (
              <p className="text-sm text-red-600 mt-2">
                Unable to submit escalation. Please try again.
              </p>
            )}
          </div>
        </AppCard>

        {/* Footer: Provisions and Download */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-2 pb-4">
          <div className="flex flex-wrap gap-2">
            {topic.key_provisions.map((provision) => (
              <SourceCitation
                key={provision}
                label={provision}
                authority={getAuthorityLevel(provision)}
              />
            ))}
          </div>
          <AppButton
            variant="outlined"
            size="sm"
            onClick={() => {
              const printWindow = window.open("", "_blank");
              if (!printWindow) return;

              const obligationsHtml = topic.immediate_obligations
                .map(
                  (step) =>
                    `<tr>
                      <td style="padding:8px;border:1px solid #ddd;text-align:center;font-weight:bold;">${step.step_number}</td>
                      <td style="padding:8px;border:1px solid #ddd;"><strong>${step.action}</strong><br/><span style="color:#666;">${step.detail}</span></td>
                      <td style="padding:8px;border:1px solid #ddd;color:#dc2626;font-weight:600;">${step.deadline}</td>
                    </tr>`,
                )
                .join("");

              const documentsHtml = topic.documents_needed
                .map(
                  (doc) =>
                    `<li style="padding:4px 0;border-bottom:1px solid #eee;">${doc}</li>`,
                )
                .join("");

              const processHtml = topic.process_steps
                .map(
                  (step) =>
                    `<tr>
                      <td style="padding:8px;border:1px solid #ddd;text-align:center;font-weight:bold;">${step.step_number}</td>
                      <td style="padding:8px;border:1px solid #ddd;"><strong>${step.action}</strong><br/><span style="color:#666;">${step.detail}</span></td>
                      <td style="padding:8px;border:1px solid #ddd;">${step.deadline}</td>
                    </tr>`,
                )
                .join("");

              const helpHtml = topic.when_to_get_help
                .map((item) => `<li style="padding:4px 0;">${item}</li>`)
                .join("");

              const provisionsHtml = topic.key_provisions
                .map(
                  (p) =>
                    `<span style="display:inline-block;margin:2px 4px;padding:2px 8px;border:1px solid #999;border-radius:4px;font-size:12px;">${p}</span>`,
                )
                .join("");

              printWindow.document.write(`<!DOCTYPE html>
<html>
<head>
  <title>${topic.title} - Emergency Guide</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 20px; color: #111; }
    h1 { color: #dc2626; margin-bottom: 4px; }
    h2 { color: #333; border-bottom: 2px solid #dc2626; padding-bottom: 6px; margin-top: 32px; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0; }
    ul { list-style: none; padding: 0; }
    .footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }
    @media print { body { padding: 0; } }
  </style>
</head>
<body>
  <h1>${topic.title}</h1>
  <p style="color:#555;">${topic.description}</p>

  <h2>Immediate Obligations</h2>
  <table>
    <thead><tr>
      <th style="padding:8px;border:1px solid #ddd;background:#f9f9f9;width:50px;">Step</th>
      <th style="padding:8px;border:1px solid #ddd;background:#f9f9f9;">Action &amp; Detail</th>
      <th style="padding:8px;border:1px solid #ddd;background:#f9f9f9;width:120px;">Deadline</th>
    </tr></thead>
    <tbody>${obligationsHtml}</tbody>
  </table>

  <h2>Documents You Need to Gather</h2>
  <ul>${documentsHtml}</ul>

  <h2>Step-by-Step Process</h2>
  <table>
    <thead><tr>
      <th style="padding:8px;border:1px solid #ddd;background:#f9f9f9;width:50px;">Step</th>
      <th style="padding:8px;border:1px solid #ddd;background:#f9f9f9;">Action &amp; Detail</th>
      <th style="padding:8px;border:1px solid #ddd;background:#f9f9f9;width:120px;">Deadline</th>
    </tr></thead>
    <tbody>${processHtml}</tbody>
  </table>

  <h2>When to Get Professional Help</h2>
  <ul style="list-style:disc;padding-left:20px;">${helpHtml}</ul>

  <h2>Key Provisions</h2>
  <div>${provisionsHtml}</div>

  <div class="footer">
    <p>Generated from AITE Emergency HR Guide on ${new Date().toLocaleDateString("en-SG", { year: "numeric", month: "long", day: "numeric" })}.</p>
    <p>This guide provides immediate steps only. For complex situations, always consult an employment law specialist.</p>
  </div>
</body>
</html>`);
              printWindow.document.close();
              printWindow.focus();
              printWindow.print();
            }}
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            Download as PDF
          </AppButton>
        </div>
      </div>
    );
  }

  /* ── Hub View (default) ────────────────────────────────────── */

  // Order scenarios according to TOPIC_ORDER, then append any extras
  const orderedScenarios: EmergencyScenario[] = [];
  for (const topicId of TOPIC_ORDER) {
    if (scenarioMap[topicId]) orderedScenarios.push(scenarioMap[topicId]);
  }
  for (const s of scenarios) {
    if (!TOPIC_ORDER.includes(s.topic_id as (typeof TOPIC_ORDER)[number])) {
      orderedScenarios.push(s);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <AlertTriangle
          className="h-7 w-7"
          style={{ color: "var(--color-risk-red)" }}
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Emergency HR Situations
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Get immediate guidance for urgent HR situations.
          </p>
        </div>
      </div>

      {/* Disclaimer banner */}
      <AlertBanner
        variant="warning"
        title="Important Disclaimer"
        description="These guides provide immediate steps. For complex situations, always consult an employment law specialist."
      />

      {/* Emergency topic grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {orderedScenarios.map((topic) => {
          const TopicIcon = ICON_MAP[topic.icon] ?? AlertTriangle;

          return (
            <AppCard
              key={topic.topic_id}
              variant="standard"
              className="border-l-4 cursor-pointer transition-shadow hover:shadow-lg"
              style={{ borderLeftColor: "var(--color-risk-red)" }}
              onClick={() => setSelectedTopic(topic.topic_id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e: React.KeyboardEvent) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setSelectedTopic(topic.topic_id);
                }
              }}
            >
              <div className="flex items-start gap-3">
                <div
                  className="flex items-center justify-center w-10 h-10 rounded-lg shrink-0"
                  style={{
                    backgroundColor: "var(--color-risk-red-bg)",
                    color: "var(--color-risk-red)",
                  }}
                >
                  <TopicIcon className="h-5 w-5" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-bold text-[var(--color-gray-900)]">
                    {topic.title}
                  </h3>
                  <p className="text-xs text-[var(--color-gray-600)] mt-1 line-clamp-2">
                    {topic.description}
                  </p>
                  <span
                    className="inline-flex items-center gap-1 mt-3 text-xs font-semibold"
                    style={{ color: "var(--color-risk-red)" }}
                  >
                    View Guide
                    <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                </div>
              </div>
            </AppCard>
          );
        })}
      </div>
    </div>
  );
}
