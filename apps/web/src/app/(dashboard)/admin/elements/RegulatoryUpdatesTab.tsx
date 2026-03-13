"use client";

import { useState } from "react";
import { AppButton, AppCard } from "@/components/design-system";
import { Plus, Loader2, AlertCircle } from "lucide-react";
import type { UpdateStatus, UpdateUrgency } from "@/types/api";
import {
  useRegulatoryUpdates,
  useSubmitForReview,
  useApproveUpdate,
  useRejectUpdate,
  usePublishUpdate,
} from "@/hooks/api/useAdmin";
import { CreateUpdateForm } from "./CreateUpdateForm";

/* ── Status badge ─────────────────────────────────────────── */

const STATUS_STYLES: Record<UpdateStatus, string> = {
  draft:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-700)] border-[var(--color-gray-300)]",
  in_review: "bg-blue-50 text-blue-700 border-blue-200",
  approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  published:
    "bg-[var(--color-risk-green-bg)] text-[var(--color-risk-green)] border-[var(--color-risk-green-border)]",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

const STATUS_LABELS: Record<UpdateStatus, string> = {
  draft: "Draft",
  in_review: "In Review",
  approved: "Approved",
  published: "Published",
  rejected: "Rejected",
};

function StatusBadge({ status }: { status: UpdateStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

/* ── Urgency indicator ────────────────────────────────────── */

const URGENCY_STYLES: Record<UpdateUrgency, string> = {
  low: "text-[var(--color-gray-500)]",
  medium: "text-[var(--color-risk-amber)]",
  high: "text-[var(--color-risk-amber)] font-semibold",
  critical: "text-[var(--color-risk-red)] font-semibold",
};

/* ── Loading skeleton ─────────────────────────────────────── */

function TableSkeleton() {
  return (
    <AppCard variant="flat" className="overflow-hidden">
      <div className="animate-pulse space-y-4 py-4 px-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-4">
            <div className="h-4 flex-1 bg-[var(--color-gray-200)] rounded" />
            <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
            <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded" />
            <div className="h-6 w-20 bg-[var(--color-gray-200)] rounded-full" />
            <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
            <div className="h-8 w-24 bg-[var(--color-gray-200)] rounded" />
          </div>
        ))}
      </div>
    </AppCard>
  );
}

/* ── Action buttons per row ───────────────────────────────── */

function RowActions({
  updateId,
  status,
  onAction,
  isActioning,
}: {
  updateId: string;
  status: UpdateStatus;
  onAction: (updateId: string, action: string) => void;
  isActioning: boolean;
}) {
  if (isActioning) {
    return (
      <Loader2 className="h-4 w-4 animate-spin text-[var(--color-gray-400)]" />
    );
  }

  switch (status) {
    case "draft":
      return (
        <AppButton
          size="sm"
          variant="outlined"
          onClick={() => onAction(updateId, "submit")}
        >
          Submit for Review
        </AppButton>
      );
    case "in_review":
      return (
        <div className="flex gap-2">
          <AppButton
            size="sm"
            variant="primary"
            onClick={() => onAction(updateId, "approve")}
          >
            Approve
          </AppButton>
          <AppButton
            size="sm"
            variant="danger"
            onClick={() => onAction(updateId, "reject")}
          >
            Reject
          </AppButton>
        </div>
      );
    case "approved":
      return (
        <AppButton
          size="sm"
          variant="primary"
          onClick={() => onAction(updateId, "publish")}
        >
          Publish
        </AppButton>
      );
    case "published":
      return (
        <AppButton
          size="sm"
          variant="text"
          onClick={() => onAction(updateId, "view")}
        >
          View
        </AppButton>
      );
    case "rejected":
      return (
        <AppButton
          size="sm"
          variant="outlined"
          onClick={() => onAction(updateId, "edit")}
        >
          Edit
        </AppButton>
      );
  }
}

/* ── Regulatory Updates Tab ───────────────────────────────── */

export function RegulatoryUpdatesTab() {
  const [showForm, setShowForm] = useState(false);
  const [actioningId, setActioningId] = useState<string | null>(null);

  const { data: updates, isLoading, error } = useRegulatoryUpdates();

  const submitMutation = useSubmitForReview();
  const approveMutation = useApproveUpdate();
  const rejectMutation = useRejectUpdate();
  const publishMutation = usePublishUpdate();

  async function handleAction(updateId: string, action: string) {
    if (action === "view" || action === "edit") return;

    setActioningId(updateId);
    try {
      switch (action) {
        case "submit":
          await submitMutation.mutateAsync(updateId);
          break;
        case "approve":
          await approveMutation.mutateAsync({
            updateId,
            data: { reviewer: "admin", notes: "" },
          });
          break;
        case "reject":
          await rejectMutation.mutateAsync({
            updateId,
            data: { reviewer: "admin", notes: "" },
          });
          break;
        case "publish":
          await publishMutation.mutateAsync(updateId);
          break;
      }
    } finally {
      setActioningId(null);
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Regulatory Updates
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Manage regulatory changes and their impact on the knowledge base
          </p>
        </div>
        <AppButton
          size="sm"
          variant="primary"
          onClick={() => setShowForm(true)}
          disabled={showForm}
        >
          <Plus className="h-4 w-4" />
          Create Update
        </AppButton>
      </div>

      {/* Inline form */}
      {showForm && <CreateUpdateForm onClose={() => setShowForm(false)} />}

      {/* Error state */}
      {error && (
        <AppCard
          variant="flat"
          className="border-l-4 border-l-[var(--color-risk-red)]"
        >
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-[var(--color-risk-red)]" />
            <div>
              <p className="text-sm font-medium text-[var(--color-gray-900)]">
                Failed to load regulatory updates
              </p>
              <p className="text-xs text-[var(--color-gray-500)]">
                {error.message}
              </p>
            </div>
          </div>
        </AppCard>
      )}

      {/* Loading state */}
      {isLoading && <TableSkeleton />}

      {/* Table */}
      {updates && (
        <AppCard variant="flat" className="overflow-hidden">
          <div className="overflow-x-auto -mx-5 -my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-gray-100)]">
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Title
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Source
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Urgency
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Status
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Effective Date
                  </th>
                  <th className="text-right px-4 py-3 font-medium text-[var(--color-gray-700)]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {updates.map((update) => (
                  <tr
                    key={update.id}
                    className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-[var(--color-gray-900)]">
                          {update.title}
                        </p>
                        <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                          {update.affected_provisions_count} provisions affected
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[var(--color-gray-700)]">
                      {update.source}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`capitalize ${URGENCY_STYLES[update.urgency]}`}
                      >
                        {update.urgency}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={update.status} />
                    </td>
                    <td className="px-4 py-3 text-[var(--color-gray-700)]">
                      {update.effective_date}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <RowActions
                        updateId={update.id}
                        status={update.status}
                        onAction={handleAction}
                        isActioning={actioningId === update.id}
                      />
                    </td>
                  </tr>
                ))}
                {updates.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-8 text-center text-sm text-[var(--color-gray-500)]"
                    >
                      No regulatory updates found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </AppCard>
      )}
    </div>
  );
}
