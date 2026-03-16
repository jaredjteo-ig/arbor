"use client";

/* ── Advisory History Page ──────────────────────────────── */
/* Lists past advisory conversations in reverse chronological */
/* order with search, risk-tier filtering, and CSV export.    */

import { useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Download,
  MessageSquare,
  Clock,
  ArrowLeft,
  FileText,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import {
  AppCard,
  AppButton,
  RiskTierBadge,
  LoadingState,
  EmptyState,
  ErrorState,
} from "@/components/design-system";
import type { RiskTierLevel } from "@/components/design-system";
import { useConversationList } from "@/hooks/useAdvisoryHistory";
import type { ConversationListItem } from "@/types/api";

/* ── Types ──────────────────────────────────────────────── */

type RiskFilter = "all" | "green" | "amber" | "red";

/* ── Helpers ────────────────────────────────────────────── */

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-SG", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trimEnd() + "...";
}

function normaliseRiskTier(tier: string | undefined): RiskTierLevel {
  if (tier === "green" || tier === "amber" || tier === "red") return tier;
  return "green";
}

/* ── CSV Export ─────────────────────────────────────────── */

/**
 * Sanitize a cell value to prevent CSV injection.
 * Prefixes dangerous characters (=, +, -, @, \t, \r) with a single quote
 * so spreadsheet applications don't interpret them as formulas.
 */
function sanitizeCsvCell(value: string): string {
  const escaped = value.replace(/"/g, '""');
  if (/^[=+\-@\t\r]/.test(escaped)) {
    return `"'${escaped}"`;
  }
  return `"${escaped}"`;
}

function exportToCsv(conversations: ConversationListItem[]) {
  const headers = ["Date", "Time", "Title", "Preview", "Risk Tier", "Messages"];
  const rows = conversations.map((c) => [
    formatDate(c.timestamp),
    formatTime(c.timestamp),
    sanitizeCsvCell(c.title),
    sanitizeCsvCell(c.last_message),
    c.risk_tier ?? "green",
    String(c.message_count),
  ]);

  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `advisory-history-${new Date().toISOString().split("T")[0]}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/* ── Risk Filter Buttons ───────────────────────────────── */

const RISK_FILTERS: { value: RiskFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "green", label: "Green" },
  { value: "amber", label: "Amber" },
  { value: "red", label: "Red" },
];

function RiskFilterBar({
  active,
  onChange,
}: {
  active: RiskFilter;
  onChange: (filter: RiskFilter) => void;
}) {
  return (
    <div className="flex gap-2" role="group" aria-label="Filter by risk tier">
      {RISK_FILTERS.map((f) => (
        <button
          key={f.value}
          type="button"
          onClick={() => onChange(f.value)}
          aria-pressed={active === f.value}
          className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
            active === f.value
              ? "bg-[var(--color-primary)] text-white"
              : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:bg-[var(--color-gray-200)]"
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}

/* ── Skeleton ──────────────────────────────────────────── */

function HistorySkeleton() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="h-8 w-48 rounded bg-[var(--color-gray-200)] animate-pulse" />
      <div className="h-10 w-full rounded-lg bg-[var(--color-gray-200)] animate-pulse" />
      <div className="flex gap-2">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-9 w-16 rounded-lg bg-[var(--color-gray-200)] animate-pulse"
          />
        ))}
      </div>
      <LoadingState variant="list" count={5} />
    </div>
  );
}

/* ── Conversation Row ──────────────────────────────────── */

function ConversationRow({
  conversation,
  onClick,
}: {
  conversation: ConversationListItem;
  onClick: () => void;
}) {
  const tier = normaliseRiskTier(conversation.risk_tier);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className="group flex items-start gap-4 p-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] hover:shadow-[var(--shadow-card)] hover:border-[var(--color-gray-300)] transition-all cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
    >
      {/* Icon */}
      <div className="shrink-0 mt-0.5 p-2 rounded-lg bg-[var(--color-gray-100)] group-hover:bg-[var(--color-primary-bg)] transition-colors">
        <MessageSquare
          className="h-4 w-4 text-[var(--color-gray-500)] group-hover:text-[var(--color-primary)] transition-colors"
          aria-hidden="true"
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)] truncate">
            {conversation.title}
          </h3>
          <RiskTierBadge tier={tier} className="text-xs" />
        </div>

        <p className="mt-1 text-sm text-[var(--color-gray-500)] line-clamp-2">
          {truncate(conversation.last_message, 120)}
        </p>

        <div className="flex items-center gap-4 mt-2 text-xs text-[var(--color-gray-400)]">
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3 w-3" aria-hidden="true" />
            {formatDate(conversation.timestamp)} at{" "}
            {formatTime(conversation.timestamp)}
          </span>
          <span className="inline-flex items-center gap-1">
            <FileText className="h-3 w-3" aria-hidden="true" />
            {conversation.message_count} message
            {conversation.message_count !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────── */

export default function AdvisoryHistoryPage() {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useConversationList();
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("all");

  const conversations = data?.conversations ?? [];

  /* Filter and sort */
  const filtered = useMemo(() => {
    let items = [...conversations];

    /* Search filter */
    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (c) =>
          c.title.toLowerCase().includes(q) ||
          c.last_message.toLowerCase().includes(q),
      );
    }

    /* Risk tier filter */
    if (riskFilter !== "all") {
      items = items.filter(
        (c) => normaliseRiskTier(c.risk_tier) === riskFilter,
      );
    }

    /* Reverse chronological */
    items.sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    );

    return items;
  }, [conversations, search, riskFilter]);

  const handleRowClick = useCallback(
    (id: number) => {
      router.push(`/advisory?conversation=${id}`);
    },
    [router],
  );

  /* Loading state */
  if (isLoading) {
    return <HistorySkeleton />;
  }

  /* Error state */
  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <ErrorState
          variant="server"
          title="Unable to load conversation history"
          description="We could not retrieve your past advisory conversations. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Back link */}
      <Link
        href="/advisory"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-primary)] hover:underline"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Advisory
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <ShieldCheck
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Advisory History
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Browse and search your past advisory conversations.
            </p>
          </div>
        </div>

        {/* CSV Export */}
        {filtered.length > 0 && (
          <AppButton
            variant="outlined"
            size="sm"
            onClick={() => exportToCsv(filtered)}
          >
            <Download className="h-4 w-4" />
            Export CSV
          </AppButton>
        )}
      </div>

      {/* Search */}
      <div className="flex items-center gap-2 rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-surface-input)] px-3 py-2">
        <Search
          className="h-4 w-4 text-[var(--color-gray-400)] shrink-0"
          aria-hidden="true"
        />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search conversations..."
          className="flex-1 bg-transparent text-sm text-[var(--foreground)] placeholder:text-[var(--color-gray-400)] outline-none"
          aria-label="Search conversations"
        />
      </div>

      {/* Risk tier filter */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <RiskFilterBar active={riskFilter} onChange={setRiskFilter} />
        <p className="text-sm text-[var(--color-gray-400)]">
          {filtered.length} conversation{filtered.length !== 1 ? "s" : ""}
        </p>
      </div>

      {/* Conversation list */}
      {filtered.length === 0 ? (
        <EmptyState
          message={
            search || riskFilter !== "all"
              ? "No matching conversations"
              : "No advisory conversations yet"
          }
          description={
            search || riskFilter !== "all"
              ? "Try adjusting your search or filter criteria."
              : "Start a new conversation from the Advisory page to see it here."
          }
          action={
            !search && riskFilter === "all" ? (
              <AppButton
                variant="primary"
                onClick={() => router.push("/advisory")}
              >
                Start a Conversation
              </AppButton>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((conv) => (
            <ConversationRow
              key={conv.id}
              conversation={conv}
              onClick={() => handleRowClick(conv.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
