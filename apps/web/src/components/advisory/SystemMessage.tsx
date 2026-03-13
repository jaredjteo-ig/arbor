"use client";

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
import { AlertOctagon, PhoneCall } from "lucide-react";

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

function mapAuthority(relevance: number): AuthorityLevel {
  if (relevance >= 0.8) return "statutory";
  if (relevance >= 0.5) return "guideline";
  return "best-practice";
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
  const isRed = riskTier === "red";
  const validTier = (
    riskTier === "green" || riskTier === "amber" || riskTier === "red"
      ? riskTier
      : undefined
  ) as RiskTier | undefined;

  const sources =
    provisionsCited && provisionsCited.length > 0 ? (
      <>
        {provisionsCited.map((p) => (
          <SourceCitation
            key={p.provision_id}
            label={p.title}
            authority={mapAuthority(p.relevance)}
          />
        ))}
      </>
    ) : undefined;

  return (
    <div className="space-y-2">
      <ChatBubble role="system" riskTier={validTier} sources={sources}>
        {/* Risk tier header for RED responses */}
        {isRed && (
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-[var(--color-risk-red)]/20">
            <AlertOctagon className="h-5 w-5 text-[var(--color-risk-red)]" />
            <span className="text-sm font-semibold text-[var(--color-risk-red)]">
              {riskTierLabel("red")}
            </span>
          </div>
        )}

        {/* Risk tier badge (non-red) */}
        {validTier && !isRed && (
          <div className="flex items-center gap-2 mb-2">
            <RiskTierBadge tier={validTier} />
            {confidenceScore !== undefined && (
              <span className="text-xs text-[var(--color-gray-400)]">
                Confidence: {Math.round(confidenceScore * 100)}%
              </span>
            )}
          </div>
        )}

        {/* Main content — rendered as HTML-safe prose */}
        <div className="whitespace-pre-wrap">{content}</div>

        {/* Streaming indicator */}
        {streaming && (
          <span className="inline-block w-2 h-4 bg-[var(--color-primary)] animate-pulse rounded-sm ml-0.5" />
        )}

        {/* RED: Connect to specialist CTA */}
        {isRed && !streaming && (
          <div className="mt-4 pt-3 border-t border-[var(--color-gray-200)]">
            <AppButton
              variant="danger"
              size="sm"
              onClick={() => {
                /* Will connect to specialist flow */
              }}
            >
              <PhoneCall className="h-4 w-4 mr-1.5" />
              Connect to Employment Law Specialist
            </AppButton>
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
    </div>
  );
}
