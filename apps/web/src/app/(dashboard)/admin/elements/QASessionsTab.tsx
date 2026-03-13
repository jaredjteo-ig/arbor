"use client";

import { useState } from "react";
import { AppButton, AppCard, EmptyState } from "@/components/design-system";
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Plus,
} from "lucide-react";
import { useQaSessions } from "@/hooks/api/useQa";
import { NewSessionModal } from "./NewSessionModal";
import { SessionSummary } from "./SessionSummary";
import { ConversationBrowser } from "./ConversationBrowser";
import { SessionSummaryView } from "./SessionSummaryView";
import type { QASession, QASessionStatus } from "@/types/api";

/* ── Constants ───────────────────────────────────────────── */

const PAGE_SIZE = 10;

/* ── Status badge ────────────────────────────────────────── */

const STATUS_STYLES: Record<QASessionStatus, string> = {
  active:
    "bg-[var(--color-info-bg)] text-[var(--color-info)] border-[var(--color-info)]",
  completed:
    "bg-[var(--color-success-bg)] text-[var(--color-success)] border-[var(--color-success)]",
};

function StatusBadge({ status }: { status: QASessionStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${STATUS_STYLES[status]}`}
    >
      {status === "active" ? "Active" : "Completed"}
    </span>
  );
}

/* ── Skeleton ────────────────────────────────────────────── */

function TableSkeleton() {
  return (
    <AppCard variant="flat" className="overflow-hidden">
      <div className="animate-pulse space-y-4 py-4 px-4">
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="flex items-center gap-4">
            <div className="h-4 w-28 bg-[var(--color-gray-200)] rounded" />
            <div className="h-4 flex-1 bg-[var(--color-gray-200)] rounded" />
            <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded" />
            <div className="h-6 w-20 bg-[var(--color-gray-200)] rounded-full" />
          </div>
        ))}
      </div>
    </AppCard>
  );
}

/* ── Session row ─────────────────────────────────────────── */

function SessionRow({
  session,
  onViewSummary,
  onReview,
}: {
  session: QASession;
  onViewSummary: (session: QASession) => void;
  onReview: (session: QASession) => void;
}) {
  const createdDate = new Date(session.created_at).toLocaleDateString();
  const completedDate = session.completed_at
    ? new Date(session.completed_at).toLocaleDateString()
    : "--";

  return (
    <tr className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors">
      <td className="px-4 py-3 text-sm text-[var(--color-gray-900)] font-medium">
        {session.reviewer_name}
      </td>
      <td className="px-4 py-3 text-sm text-[var(--color-gray-500)] whitespace-nowrap">
        {createdDate}
      </td>
      <td className="px-4 py-3 text-sm text-[var(--color-gray-500)] whitespace-nowrap">
        {completedDate}
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={session.status} />
      </td>
      <td className="px-4 py-3 text-sm text-[var(--color-gray-700)] text-center">
        {session.conversation_count}
      </td>
      <td className="px-4 py-3 text-sm text-[var(--color-gray-700)] text-center">
        {session.status === "completed" &&
        session.average_overall_score !== null
          ? session.average_overall_score.toFixed(1)
          : "--"}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          {session.status === "active" && (
            <button
              type="button"
              onClick={() => onReview(session)}
              className="text-xs font-medium text-[var(--color-primary)] hover:underline"
            >
              Review
            </button>
          )}
          {session.status === "completed" && (
            <button
              type="button"
              onClick={() => onViewSummary(session)}
              className="text-xs font-medium text-[var(--color-primary)] hover:underline"
            >
              View
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

/* ── Main Tab ────────────────────────────────────────────── */

type ViewMode = "list" | "review" | "summary" | "completedSummary";

export function QASessionsTab() {
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedSession, setSelectedSession] = useState<QASession | null>(
    null,
  );
  const [viewMode, setViewMode] = useState<ViewMode>("list");

  const { data, isLoading, error } = useQaSessions(undefined, page, PAGE_SIZE);

  /* ── If reviewing an active session's conversations ──────── */
  if (selectedSession && viewMode === "review") {
    return (
      <ConversationBrowser
        session={selectedSession}
        onClose={() => {
          setSelectedSession(null);
          setViewMode("list");
        }}
      />
    );
  }

  /* ── If viewing the pre-completion summary ────────────────── */
  if (selectedSession && viewMode === "summary") {
    return (
      <SessionSummaryView
        session={selectedSession}
        onCompleted={() => {
          setSelectedSession(null);
          setViewMode("list");
        }}
      />
    );
  }

  /* ── If viewing a completed session's scorecard ────────────── */
  if (selectedSession && viewMode === "completedSummary") {
    return (
      <SessionSummary
        session={selectedSession}
        onClose={() => {
          setSelectedSession(null);
          setViewMode("list");
        }}
      />
    );
  }

  /* ── Loading ───────────────────────────────────────────── */
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="animate-pulse h-5 w-40 bg-[var(--color-gray-200)] rounded" />
        <TableSkeleton />
      </div>
    );
  }

  /* ── Error ─────────────────────────────────────────────── */
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
              Failed to load QA sessions
            </p>
            <p className="text-xs text-[var(--color-gray-500)]">
              {error.message}
            </p>
          </div>
        </div>
      </AppCard>
    );
  }

  const sessions = data?.sessions ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  /* Sort: active sessions first, then by created_at desc */
  const sorted = [...sessions].sort((a, b) => {
    if (a.status === "active" && b.status !== "active") return -1;
    if (a.status !== "active" && b.status === "active") return 1;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            QA Review Sessions
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            {total} session{total !== 1 ? "s" : ""} total
          </p>
        </div>
        <AppButton size="sm" onClick={() => setModalOpen(true)}>
          <Plus className="h-4 w-4" />
          Start New Session
        </AppButton>
      </div>

      {/* Table or empty state */}
      {sorted.length === 0 ? (
        <EmptyState
          icon={<ClipboardCheck className="h-12 w-12" aria-hidden="true" />}
          message="No QA sessions yet"
          description="Start a new session to begin reviewing conversation quality."
          action={
            <AppButton size="sm" onClick={() => setModalOpen(true)}>
              <Plus className="h-4 w-4" />
              Start New Session
            </AppButton>
          }
        />
      ) : (
        <AppCard variant="flat" className="overflow-hidden">
          <div className="overflow-x-auto -mx-5 -my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-gray-100)]">
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Reviewer
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Created
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Completed
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Status
                  </th>
                  <th className="text-center px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Conversations
                  </th>
                  <th className="text-center px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Avg Score
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((session) => (
                  <SessionRow
                    key={session.id}
                    session={session}
                    onViewSummary={(s) => {
                      setSelectedSession(s);
                      setViewMode("completedSummary");
                    }}
                    onReview={(s) => {
                      setSelectedSession(s);
                      setViewMode("review");
                    }}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </AppCard>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-[var(--color-gray-500)]">
            Page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <AppButton
              variant="outlined"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </AppButton>
            <AppButton
              variant="outlined"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </AppButton>
          </div>
        </div>
      )}

      {/* New session modal */}
      <NewSessionModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
}
