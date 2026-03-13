"use client";

import { useState } from "react";
import {
  AppButton,
  AppCard,
  ChatBubble,
  RiskTierBadge,
  SourceCitation,
  EmptyState,
} from "@/components/design-system";
import type { RiskTierLevel } from "@/components/design-system";
import {
  AlertCircle,
  ArrowLeft,
  Check,
  ChevronDown,
  ChevronRight,
  Clock,
  MessageSquare,
} from "lucide-react";
import {
  useQaSessionConversations,
  useConversationHistory,
} from "@/hooks/api/useQa";
import { EvaluationForm } from "./EvaluationForm";
import type {
  QASession,
  QASessionConversation,
  AdvisoryMessage,
} from "@/types/api";

/* ── Props ───────────────────────────────────────────────── */

interface ConversationBrowserProps {
  session: QASession;
  onClose: () => void;
}

/* ── Skeleton ────────────────────────────────────────────── */

function ListSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="animate-pulse flex items-center gap-3 p-3">
          <div className="h-4 w-4 bg-[var(--color-gray-200)] rounded-full" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3.5 w-3/4 bg-[var(--color-gray-200)] rounded" />
            <div className="h-3 w-1/3 bg-[var(--color-gray-200)] rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="animate-pulse space-y-4 p-4">
      <div className="h-10 w-2/3 bg-[var(--color-gray-200)] rounded-xl ml-auto" />
      <div className="h-24 w-full bg-[var(--color-gray-200)] rounded-xl" />
      <div className="h-10 w-1/2 bg-[var(--color-gray-200)] rounded-xl ml-auto" />
      <div className="h-32 w-full bg-[var(--color-gray-200)] rounded-xl" />
    </div>
  );
}

/* ── Risk tier helper ────────────────────────────────────── */

function toRiskTierLevel(tier: string): RiskTierLevel {
  if (tier === "green" || tier === "amber" || tier === "red") return tier;
  return "green";
}

/* ── Expandable section ──────────────────────────────────── */

function ExpandableSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-2 border-t border-[var(--color-gray-100)] pt-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] transition-colors"
      >
        {open ? (
          <ChevronDown className="h-3.5 w-3.5" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5" />
        )}
        {title}
      </button>
      {open && <div className="mt-2">{children}</div>}
    </div>
  );
}

/* ── Conversation list item ──────────────────────────────── */

function ConversationItem({
  conversation,
  isSelected,
  onSelect,
}: {
  conversation: QASessionConversation;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left px-3 py-2.5 transition-colors border-b border-[var(--color-gray-100)] last:border-0 ${
        isSelected
          ? "bg-[var(--color-primary)]/5 border-l-2 border-l-[var(--color-primary)]"
          : "hover:bg-[var(--color-gray-50)]"
      }`}
    >
      <div className="flex items-start gap-2">
        <div className="mt-0.5 shrink-0">
          {conversation.reviewed ? (
            <Check className="h-4 w-4 text-[var(--color-risk-green)]" />
          ) : (
            <Clock className="h-4 w-4 text-[var(--color-gray-400)]" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-[var(--color-gray-900)] truncate">
            {conversation.query_snippet.length > 60
              ? `${conversation.query_snippet.slice(0, 60)}...`
              : conversation.query_snippet}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <RiskTierBadge
              tier={toRiskTierLevel(conversation.risk_tier)}
              className="!text-xs !px-2 !py-0.5"
            />
            <span className="text-xs text-[var(--color-gray-500)]">
              {(conversation.confidence_score * 100).toFixed(0)}% confidence
            </span>
          </div>
        </div>
      </div>
    </button>
  );
}

/* ── Conversation detail (right panel) ───────────────────── */

function ConversationDetail({
  conversation,
  session,
  onEvaluationSubmitted,
}: {
  conversation: QASessionConversation;
  session: QASession;
  onEvaluationSubmitted: () => void;
}) {
  const { data, isLoading, error } = useConversationHistory(
    conversation.conversation_id,
  );

  if (isLoading) return <DetailSkeleton />;

  if (error) {
    return (
      <AppCard
        variant="flat"
        className="border-l-4 border-l-[var(--color-risk-red)]"
      >
        <div className="flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-[var(--color-risk-red)]" />
          <div>
            <p className="text-sm font-medium text-[var(--color-gray-900)]">
              Failed to load conversation
            </p>
            <p className="text-xs text-[var(--color-gray-500)]">
              {error.message}
            </p>
          </div>
        </div>
      </AppCard>
    );
  }

  const messages = data?.messages ?? [];

  /* Find last assistant turn number for evaluation */
  const assistantTurns = messages.filter((m) => m.role === "assistant");
  const lastTurnNumber = assistantTurns.length;

  /* Gather all provisions from assistant messages */
  const allProvisions = messages
    .filter(
      (
        m,
      ): m is AdvisoryMessage & {
        provisions_cited: NonNullable<AdvisoryMessage["provisions_cited"]>;
      } =>
        m.role === "assistant" &&
        Array.isArray(m.provisions_cited) &&
        m.provisions_cited.length > 0,
    )
    .flatMap((m) => m.provisions_cited);

  /* Deduplicate provisions by provision_id */
  const uniqueProvisions = Array.from(
    new Map(allProvisions.map((p) => [p.provision_id, p])).values(),
  );

  return (
    <div className="space-y-4">
      {/* Chat messages */}
      <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-1">
        {messages.length === 0 ? (
          <p className="text-sm text-[var(--color-gray-500)] text-center py-8">
            No messages found for this conversation.
          </p>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx}>
              {msg.role === "user" ? (
                <ChatBubble role="user">
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </ChatBubble>
              ) : (
                <>
                  <ChatBubble
                    role="system"
                    riskTier={
                      msg.risk_tier ? toRiskTierLevel(msg.risk_tier) : undefined
                    }
                    sources={
                      msg.provisions_cited &&
                      msg.provisions_cited.length > 0 ? (
                        <>
                          {msg.provisions_cited.map((p) => (
                            <SourceCitation
                              key={p.provision_id}
                              label={p.provision_id}
                              authority="statutory"
                            />
                          ))}
                        </>
                      ) : undefined
                    }
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </ChatBubble>

                  {/* Expandable sections for assistant messages */}
                  <div className="ml-0 mt-1 space-y-0">
                    {/* Specialist Outputs */}
                    {msg.provisions_cited &&
                      msg.provisions_cited.length > 0 && (
                        <ExpandableSection title="Specialist Outputs">
                          <div className="space-y-2 pl-2">
                            {msg.provisions_cited.map((p) => (
                              <div
                                key={p.provision_id}
                                className="flex items-center gap-2 text-xs text-[var(--color-gray-600)]"
                              >
                                <span className="font-mono font-medium">
                                  {p.provision_id}
                                </span>
                                <span>{p.title}</span>
                                <span className="ml-auto text-[var(--color-gray-400)]">
                                  {(p.relevance * 100).toFixed(0)}% relevant
                                </span>
                              </div>
                            ))}
                          </div>
                        </ExpandableSection>
                      )}

                    {/* Trust Chain */}
                    {msg.confidence_score !== undefined && (
                      <ExpandableSection title="Trust Chain">
                        <div className="space-y-1.5 pl-2 text-xs text-[var(--color-gray-600)]">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">
                              Chain confidence:
                            </span>
                            <span>
                              {(msg.confidence_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          {msg.risk_tier && (
                            <div className="flex items-center gap-2">
                              <span className="font-medium">Risk tier:</span>
                              <RiskTierBadge
                                tier={toRiskTierLevel(msg.risk_tier)}
                                className="!text-xs !px-2 !py-0.5"
                              />
                            </div>
                          )}
                        </div>
                      </ExpandableSection>
                    )}
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>

      {/* Evaluation form -- only if not already reviewed */}
      {!conversation.reviewed && (
        <EvaluationForm
          sessionId={Number(session.id)}
          conversationId={String(conversation.conversation_id)}
          turnNumber={lastTurnNumber}
          provisions={uniqueProvisions}
          onSubmitted={onEvaluationSubmitted}
        />
      )}

      {conversation.reviewed && (
        <AppCard variant="flat">
          <div className="flex items-center gap-2 text-sm text-[var(--color-risk-green)]">
            <Check className="h-4 w-4" />
            <span className="font-medium">
              This conversation has been evaluated.
            </span>
            {conversation.overall_score !== null && (
              <span className="ml-auto text-[var(--color-gray-700)]">
                Score: {conversation.overall_score.toFixed(1)} / 5
              </span>
            )}
          </div>
        </AppCard>
      )}
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────── */

export function ConversationBrowser({
  session,
  onClose,
}: ConversationBrowserProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const {
    data: conversationsData,
    isLoading,
    error,
    refetch,
  } = useQaSessionConversations(String(session.id));

  const conversations = conversationsData?.conversations ?? [];
  const total = conversationsData?.total ?? 0;
  const evaluatedCount = conversations.filter((c) => c.reviewed).length;

  /* Sort: unevaluated first, then by lowest confidence */
  const sorted = [...conversations].sort((a, b) => {
    if (a.reviewed !== b.reviewed) return a.reviewed ? 1 : -1;
    return a.confidence_score - b.confidence_score;
  });

  const selectedConversation = sorted.find(
    (c) => c.conversation_id === selectedId,
  );

  /* Auto-advance to next pending conversation after evaluation */
  function handleEvaluationSubmitted() {
    refetch().then(() => {
      /* Find next unevaluated conversation */
      const nextPending = sorted.find(
        (c) => !c.reviewed && c.conversation_id !== selectedId,
      );
      if (nextPending) {
        setSelectedId(nextPending.conversation_id);
      }
    });
  }

  return (
    <div className="space-y-4">
      {/* Back link + header */}
      <div className="flex items-center gap-3">
        <AppButton variant="text" size="sm" onClick={onClose}>
          <ArrowLeft className="h-4 w-4" />
          Back to sessions
        </AppButton>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Review Conversations
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Session by {session.reviewer_name} &middot; {evaluatedCount} of{" "}
            {total} evaluated
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${
              evaluatedCount === total && total > 0
                ? "bg-[var(--color-success-bg)] text-[var(--color-success)] border-[var(--color-success)]"
                : "bg-[var(--color-info-bg)] text-[var(--color-info)] border-[var(--color-info)]"
            }`}
          >
            {evaluatedCount}/{total} reviewed
          </span>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-4">
            <AppCard variant="flat">
              <ListSkeleton />
            </AppCard>
          </div>
          <div className="lg:col-span-8">
            <AppCard variant="flat">
              <DetailSkeleton />
            </AppCard>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <AppCard
          variant="flat"
          className="border-l-4 border-l-[var(--color-risk-red)]"
        >
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-[var(--color-risk-red)]" />
            <div>
              <p className="text-sm font-medium text-[var(--color-gray-900)]">
                Failed to load conversations
              </p>
              <p className="text-xs text-[var(--color-gray-500)]">
                {error.message}
              </p>
            </div>
          </div>
        </AppCard>
      )}

      {/* Two-panel layout */}
      {!isLoading && !error && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Left panel: conversation list */}
          <div className="lg:col-span-4">
            <AppCard variant="flat" className="overflow-hidden">
              {sorted.length === 0 ? (
                <EmptyState
                  icon={
                    <MessageSquare className="h-10 w-10" aria-hidden="true" />
                  }
                  message="No conversations"
                  description="This session has no conversations to review."
                />
              ) : (
                <div className="-mx-5 -my-4 max-h-[70vh] overflow-y-auto">
                  {sorted.map((conv) => (
                    <ConversationItem
                      key={conv.conversation_id}
                      conversation={conv}
                      isSelected={selectedId === conv.conversation_id}
                      onSelect={() => setSelectedId(conv.conversation_id)}
                    />
                  ))}
                </div>
              )}
            </AppCard>
          </div>

          {/* Right panel: conversation detail + evaluation */}
          <div className="lg:col-span-8">
            {selectedConversation ? (
              <ConversationDetail
                conversation={selectedConversation}
                session={session}
                onEvaluationSubmitted={handleEvaluationSubmitted}
              />
            ) : (
              <AppCard variant="flat">
                <div className="text-center py-12">
                  <MessageSquare className="h-10 w-10 mx-auto text-[var(--color-gray-300)] mb-3" />
                  <p className="text-sm text-[var(--color-gray-500)]">
                    Select a conversation from the list to begin reviewing.
                  </p>
                </div>
              </AppCard>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
