"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChatBubble,
  SourceCitation,
  RiskTierBadge,
  FeedbackButtons,
  AppButton,
} from "@/components/design-system";
import type { RiskTier } from "@/components/design-system";
import type { AuthorityLevel } from "@/components/design-system/SourceCitation";
import type { ProvisionCited } from "@/types/api";
import { AlertOctagon, PhoneCall, ArrowUpRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import { ProvisionViewer } from "./ProvisionViewer";
import { EscalationDialog } from "./EscalationDialog";
import type { EscalationUrgency } from "@/types/api";

interface SystemMessageProps {
  content: string;
  riskTier?: string;
  confidenceScore?: number;
  provisionsCited?: ProvisionCited[];
  /** Follow-up suggestions shown as tappable chips */
  suggestions?: string[];
  onSuggestionClick?: (suggestion: string) => void;
  onFeedback?: (rating: "up" | "down", text?: string) => void;
  /** Whether the message is still streaming (hides feedback buttons) */
  streaming?: boolean;
  messageId?: string;
}

function riskTierLabel(tier: string): string {
  switch (tier) {
    case "red":
      return "High Risk — Action Required";
    case "amber":
      return "Medium Risk — Attention Needed";
    case "green":
      return "Low Risk";
    default:
      return "";
  }
}

/**
 * Derive the authority level for a provision.
 *
 * Uses the backend-provided authority_level when available.
 * Falls back to deriving from the provision ID prefix, which encodes
 * the source act (e.g. "EA-" = Employment Act = statutory).
 *
 * This replaces the old relevance-score-based mapping which incorrectly
 * treated relevance as authority -- a statute with low relevance was
 * mislabelled as "best-practice".
 */
function resolveAuthority(provision: ProvisionCited): AuthorityLevel {
  const raw = provision.authority_level;
  if (
    raw === "statutory" ||
    raw === "guideline" ||
    raw === "best-practice" ||
    raw === "company-policy"
  ) {
    return raw;
  }
  /* Company policy provisions from the backend use source_type */
  if (provision.source_type === "company_policy") {
    return "company-policy";
  }
  return deriveAuthorityFromId(provision.provision_id);
}

/**
 * Map provision ID prefix to its inherent authority level.
 * Authority is a property of the source legislation, not a score.
 */
function deriveAuthorityFromId(provisionId: string): AuthorityLevel {
  const id = provisionId.toUpperCase();
  if (id.startsWith("EA-")) return "statutory";
  if (id.startsWith("CPFA-") || id.startsWith("CPF-")) return "statutory";
  if (id.startsWith("EFMA-")) return "statutory";
  if (id.startsWith("WSH-") || id.startsWith("WSHA-")) return "statutory";
  if (id.startsWith("WICA-")) return "statutory";
  if (id.startsWith("IRAS-")) return "statutory";
  if (id.startsWith("WFA-")) return "statutory";
  if (id.startsWith("TGFEP-") || id.startsWith("TAFEP-")) return "guideline";
  return "guideline";
}

/* ── Confidence Display Helpers ────────────────────────────── */

interface ConfidenceLevel {
  label: string;
  colorClass: string;
}

function getConfidenceLevel(score: number): ConfidenceLevel {
  const pct = Math.round(score * 100);
  if (pct >= 80) {
    return {
      label: "High confidence",
      colorClass: "text-[var(--color-risk-green)]",
    };
  }
  if (pct >= 60) {
    return {
      label: "Moderate confidence",
      colorClass: "text-[var(--color-risk-amber)]",
    };
  }
  return {
    label: "Low confidence \u2014 verify with specialist",
    colorClass: "text-[var(--color-risk-red)]",
  };
}

function ConfidenceBadge({ score }: { score: number }) {
  const { label, colorClass } = getConfidenceLevel(score);
  const pct = Math.round(score * 100);

  return (
    <span
      className={`text-xs font-medium ${colorClass}`}
      title={`Based on ${pct}% confidence score from knowledge base coverage`}
    >
      {label}
    </span>
  );
}

export function SystemMessage({
  content,
  riskTier,
  confidenceScore,
  provisionsCited,
  suggestions,
  onSuggestionClick,
  onFeedback,
  streaming = false,
  messageId,
}: SystemMessageProps) {
  const router = useRouter();
  const [selectedProvision, setSelectedProvision] =
    useState<ProvisionCited | null>(null);
  const [escalationOpen, setEscalationOpen] = useState(false);
  const [escalationUrgency, setEscalationUrgency] =
    useState<EscalationUrgency>("urgent");

  const isRed = riskTier === "red";
  const isAmber = riskTier === "amber";
  const validTier = (
    riskTier === "green" || riskTier === "amber" || riskTier === "red"
      ? riskTier
      : undefined
  ) as RiskTier | undefined;

  function handleCitationClick(p: ProvisionCited) {
    /* Company policy citations navigate to the policy detail page */
    if (
      p.source_type === "company_policy" ||
      p.authority_level === "company-policy"
    ) {
      if (p.policy_id) {
        router.push(`/policies/${p.policy_id}`);
        return;
      }
    }
    /* All other citations open the provision viewer */
    setSelectedProvision(p);
  }

  const sources =
    provisionsCited && provisionsCited.length > 0 ? (
      <>
        {provisionsCited.map((p) => (
          <SourceCitation
            key={p.provision_id}
            label={p.title}
            authority={resolveAuthority(p)}
            onClick={() => handleCitationClick(p)}
          />
        ))}
      </>
    ) : undefined;

  return (
    <div className="space-y-2">
      <ChatBubble role="system" riskTier={validTier} sources={sources}>
        {/* AI badge */}
        <div className="flex items-center gap-1.5 mb-2">
          <span className="text-[10px] font-medium bg-[var(--color-primary-bg)] text-[var(--color-primary)] px-1.5 py-0.5 rounded">
            AI
          </span>
        </div>

        {/* Risk tier header for RED responses */}
        {isRed && (
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-[var(--color-risk-red)]/20">
            <AlertOctagon className="h-5 w-5 text-[var(--color-risk-red)]" />
            <span className="text-sm font-semibold text-[var(--color-risk-red)]">
              {riskTierLabel("red")}
            </span>
          </div>
        )}

        {/* Risk tier badge + confidence (all tiers including red) */}
        {(validTier || confidenceScore !== undefined) && (
          <div className="flex items-center gap-2 mb-2">
            {validTier && !isRed && <RiskTierBadge tier={validTier} />}
            {confidenceScore !== undefined && (
              <ConfidenceBadge score={confidenceScore} />
            )}
          </div>
        )}

        {/* Main content — rendered as styled markdown */}
        <div className="text-sm text-[var(--color-gray-800)] leading-relaxed">
          <ReactMarkdown
            rehypePlugins={[rehypeSanitize]}
            components={{
              p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
              ul: ({ children }) => (
                <ul className="mb-3 space-y-1.5 pl-1">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="mb-3 space-y-1.5 pl-1 list-none counter-reset-[item]">
                  {children}
                </ol>
              ),
              li: ({ children }) => (
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[var(--color-primary)] shrink-0" />
                  <span className="flex-1">{children}</span>
                </li>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-[var(--color-gray-900)]">
                  {children}
                </strong>
              ),
              h1: ({ children }) => (
                <h2 className="text-base font-bold text-[var(--color-gray-900)] mt-5 mb-2 pb-1.5 border-b border-[var(--color-gray-200)]">
                  {children}
                </h2>
              ),
              h2: ({ children }) => (
                <h3 className="text-[13px] font-bold text-[var(--color-gray-900)] mt-4 mb-1.5 flex items-center gap-2">
                  <span className="w-1 h-4 rounded-full bg-[var(--color-primary)]" />
                  {children}
                </h3>
              ),
              h3: ({ children }) => (
                <h4 className="text-[13px] font-semibold text-[var(--color-gray-800)] mt-3 mb-1">
                  {children}
                </h4>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-[var(--color-primary)] pl-3 my-3 text-[var(--color-gray-600)] italic">
                  {children}
                </blockquote>
              ),
              hr: () => (
                <hr className="border-t border-[var(--color-gray-200)] my-4" />
              ),
              code: ({ children }) => (
                <code className="bg-[var(--color-gray-100)] text-[var(--color-gray-800)] px-1.5 py-0.5 rounded text-xs font-mono">
                  {children}
                </code>
              ),
              a: ({ href, children }) => (
                <a
                  href={href}
                  className="text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] underline underline-offset-2"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {children}
                </a>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
          {/* Streaming cursor */}
          {streaming && (
            <span className="inline-block w-2 h-4 bg-[var(--color-primary)] animate-pulse rounded-sm ml-0.5 align-middle" />
          )}
        </div>

        {/* Low confidence caveat */}
        {!streaming &&
          confidenceScore !== undefined &&
          Math.round(confidenceScore * 100) < 60 && (
            <div className="mt-3 pl-3 border-l-2 border-[var(--color-risk-amber)]">
              <p className="text-xs text-[var(--color-risk-amber)]">
                This response has lower confidence. The situation may involve
                nuances not fully covered in the current knowledge base.
                Consider consulting a qualified practitioner.
              </p>
            </div>
          )}

        {/* RED: Connect to specialist CTA */}
        {isRed && !streaming && (
          <div className="mt-4 pt-3 border-t border-[var(--color-gray-200)]">
            <AppButton
              variant="danger"
              size="sm"
              onClick={() => {
                setEscalationUrgency("urgent");
                setEscalationOpen(true);
              }}
            >
              <PhoneCall className="h-4 w-4 mr-1.5" />
              Connect to Employment Law Specialist
            </AppButton>
          </div>
        )}

        {/* AMBER: Get professional guidance link */}
        {isAmber && !streaming && (
          <div className="mt-3">
            <button
              type="button"
              onClick={() => {
                setEscalationUrgency("within-24h");
                setEscalationOpen(true);
              }}
              className="inline-flex items-center gap-1 text-sm text-[var(--color-risk-amber)] hover:text-[var(--color-risk-amber)]/80 underline underline-offset-2 transition-colors"
            >
              <ArrowUpRight className="h-3.5 w-3.5" />
              Get professional guidance
            </button>
          </div>
        )}
      </ChatBubble>

      {/* Follow-up suggestions */}
      {!streaming && suggestions && suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 pl-0">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onSuggestionClick?.(s)}
              className="inline-flex items-center whitespace-nowrap rounded-full px-3 py-1.5 text-sm min-h-[36px] border border-[var(--color-gray-300)] bg-[var(--color-surface-card)] text-[var(--color-gray-700)] hover:bg-[var(--color-gray-100)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Feedback buttons */}
      {!streaming && onFeedback && (
        <FeedbackButtons
          onFeedback={(fb) => onFeedback(fb.rating, fb.text)}
          className="pl-0"
        />
      )}

      {/* Provision detail modal */}
      {selectedProvision && (
        <ProvisionViewer
          provisionId={selectedProvision.provision_id}
          title={selectedProvision.title}
          authorityLevel={selectedProvision.authority_level}
          onClose={() => setSelectedProvision(null)}
        />
      )}

      {/* Escalation dialog */}
      <EscalationDialog
        open={escalationOpen}
        onClose={() => setEscalationOpen(false)}
        defaultSituation={content}
        defaultUrgency={escalationUrgency}
      />
    </div>
  );
}
