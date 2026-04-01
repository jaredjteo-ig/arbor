"use client";

import { useState } from "react";
import {
  FileText,
  Clock,
  Send,
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
  ChevronRight,
  X,
  Loader2,
} from "lucide-react";
import {
  AppCard,
  AppButton,
  LoadingState,
  ErrorState,
  EmptyState,
  toast,
} from "@/components/design-system";
import { useFilings, useSagaDetail, useRetryFiling } from "@/hooks/api";
import type {
  GovernmentFiling,
  FilingStatus,
  SagaStep,
  SagaStepStatus,
} from "@/services/api/integrations";

/* ── Status Config ───────────────────────────────────────── */

const FILING_STATUS_CONFIG: Record<
  FilingStatus,
  { icon: typeof Clock; color: string; bg: string; label: string }
> = {
  pending: {
    icon: Clock,
    color: "text-[var(--color-warning)]",
    bg: "bg-[var(--color-warning-bg)]",
    label: "Pending",
  },
  submitted: {
    icon: Send,
    color: "text-[var(--color-info)]",
    bg: "bg-[var(--color-info-bg)]",
    label: "Submitted",
  },
  confirmed: {
    icon: CheckCircle,
    color: "text-[var(--color-success)]",
    bg: "bg-[var(--color-success-bg)]",
    label: "Confirmed",
  },
  failed: {
    icon: XCircle,
    color: "text-[var(--color-error)]",
    bg: "bg-[var(--color-error-bg)]",
    label: "Failed",
  },
};

const STEP_STATUS_CONFIG: Record<
  SagaStepStatus,
  { icon: typeof Clock; color: string }
> = {
  pending: { icon: Clock, color: "text-[var(--color-gray-400)]" },
  running: { icon: Loader2, color: "text-[var(--color-info)]" },
  completed: { icon: CheckCircle, color: "text-[var(--color-success)]" },
  failed: { icon: XCircle, color: "text-[var(--color-error)]" },
  skipped: { icon: AlertCircle, color: "text-[var(--color-gray-400)]" },
};

/* ── Filing Status Badge ─────────────────────────────────── */

function FilingStatusBadge({ status }: { status: FilingStatus }) {
  const config = FILING_STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.color}`}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      {config.label}
    </span>
  );
}

/* ── Saga Step Row ───────────────────────────────────────── */

function SagaStepRow({ step }: { step: SagaStep }) {
  const config = STEP_STATUS_CONFIG[step.status];
  const Icon = config.icon;

  return (
    <div className="flex items-start gap-3 py-3 border-b border-[var(--color-gray-100)] last:border-b-0">
      <Icon
        className={`h-4 w-4 mt-0.5 shrink-0 ${config.color} ${
          step.status === "running" ? "animate-spin" : ""
        }`}
        aria-hidden="true"
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--color-gray-900)]">
          {step.step_name}
        </p>
        {step.started_at && (
          <p className="text-xs text-[var(--color-gray-400)] mt-0.5">
            Started:{" "}
            {new Date(step.started_at).toLocaleString("en-SG", {
              dateStyle: "medium",
              timeStyle: "short",
            })}
            {step.completed_at &&
              ` | Completed: ${new Date(step.completed_at).toLocaleString("en-SG", { dateStyle: "medium", timeStyle: "short" })}`}
          </p>
        )}
        {step.error_message && (
          <p className="text-xs text-[var(--color-error)] mt-1">
            {step.error_message}
          </p>
        )}
      </div>
      <span className="text-xs text-[var(--color-gray-500)] shrink-0 capitalize">
        {step.status}
      </span>
    </div>
  );
}

/* ── Detail Drawer ───────────────────────────────────────── */

function FilingDetailDrawer({
  filingId,
  onClose,
}: {
  filingId: string;
  onClose: () => void;
}) {
  const { data, isPending, error } = useSagaDetail(filingId);
  const retryFiling = useRetryFiling();

  const handleRetry = async () => {
    try {
      await retryFiling.mutateAsync(filingId);
      toast.success("Filing retry initiated.");
    } catch {
      toast.error("Retry failed. Please try again later.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="fixed inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-lg bg-[var(--color-surface-card)] shadow-[var(--shadow-modal)] overflow-y-auto">
        {/* Drawer Header */}
        <div className="sticky top-0 bg-[var(--color-surface-card)] border-b border-[var(--color-gray-200)] px-6 py-4 flex items-center justify-between z-10">
          <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
            Filing Details
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="flex items-center justify-center rounded-lg p-2 min-h-[36px] min-w-[36px]
              text-[var(--color-gray-500)] hover:bg-[var(--color-gray-100)] transition-colors
              focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            aria-label="Close details"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="px-6 py-4 space-y-6">
          {isPending && <LoadingState variant="list" count={4} />}

          {error && (
            <ErrorState
              variant="server"
              title="Could not load filing details"
              description="Please try again."
              onRetry={() => {}}
            />
          )}

          {data && (
            <>
              {/* Summary */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-[var(--color-gray-500)]">
                    Saga ID
                  </p>
                  <p className="text-sm font-mono text-[var(--color-gray-900)]">
                    {data.saga_id}
                  </p>
                </div>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-[var(--color-gray-500)]">Status</p>
                  <p className="text-sm font-medium text-[var(--color-gray-900)] capitalize">
                    {data.status}
                  </p>
                </div>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-[var(--color-gray-500)]">
                    Started
                  </p>
                  <p className="text-sm text-[var(--color-gray-900)]">
                    {new Date(data.started_at).toLocaleString("en-SG", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </p>
                </div>
              </div>

              {/* Steps */}
              <div>
                <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
                  Processing Steps
                </h3>
                <div className="rounded-[8px] border border-[var(--color-gray-200)] divide-y divide-[var(--color-gray-100)] px-4">
                  {(data.steps ?? []).map((step, i) => (
                    <SagaStepRow key={i} step={step} />
                  ))}
                </div>
              </div>

              {/* Retry button for failed sagas */}
              {data.status === "failed" && (
                <AppButton
                  variant="primary"
                  size="md"
                  onClick={handleRetry}
                  loading={retryFiling.isPending}
                  className="w-full"
                >
                  <RefreshCw className="h-4 w-4" aria-hidden="true" />
                  Retry Filing
                </AppButton>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Filing Row ──────────────────────────────────────────── */

function FilingRow({
  filing,
  onViewDetail,
}: {
  filing: GovernmentFiling;
  onViewDetail: () => void;
}) {
  const retryFiling = useRetryFiling();

  const handleRetry = async () => {
    try {
      await retryFiling.mutateAsync(filing.id);
      toast.success("Filing retry initiated.");
    } catch {
      toast.error("Retry failed. Please try again later.");
    }
  };

  return (
    <tr className="border-b border-[var(--color-gray-100)] hover:bg-[var(--color-gray-50)] transition-colors">
      <td className="py-3 px-4">
        <p className="text-sm font-medium text-[var(--color-gray-900)]">
          {filing.submission_type}
        </p>
      </td>
      <td className="py-3 px-4">
        <p className="text-sm text-[var(--color-gray-700)]">{filing.period}</p>
      </td>
      <td className="py-3 px-4">
        <FilingStatusBadge status={filing.status} />
      </td>
      <td className="py-3 px-4">
        <p className="text-sm text-[var(--color-gray-500)]">
          {filing.submitted_at
            ? new Date(filing.submitted_at).toLocaleString("en-SG", {
                dateStyle: "medium",
                timeStyle: "short",
              })
            : "-"}
        </p>
      </td>
      <td className="py-3 px-4">
        <p className="text-xs font-mono text-[var(--color-gray-500)]">
          {filing.reference_id ?? "-"}
        </p>
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-2 justify-end">
          {filing.status === "failed" && (
            <AppButton
              variant="outlined"
              size="sm"
              onClick={handleRetry}
              loading={retryFiling.isPending}
            >
              <RefreshCw className="h-3 w-3" aria-hidden="true" />
              Retry
            </AppButton>
          )}
          <button
            type="button"
            onClick={onViewDetail}
            className="inline-flex items-center justify-center rounded-[8px] p-2 min-h-[32px] min-w-[32px]
              text-[var(--color-gray-500)] hover:bg-[var(--color-gray-100)] transition-colors
              focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            aria-label="View filing details"
          >
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </td>
    </tr>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function GovernmentFilingsPage() {
  const { data, isPending, error, refetch } = useFilings();
  const [selectedFilingId, setSelectedFilingId] = useState<string | null>(null);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <FileText
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Government Filings
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Track CPF, IRAS, and MOM submission status.
          </p>
        </div>
      </div>

      {/* Content */}
      {isPending && <LoadingState variant="card" count={3} />}

      {error && (
        <ErrorState
          variant="server"
          title="Could not load filing status"
          description="We had trouble loading your government filings."
          onRetry={() => refetch()}
        />
      )}

      {data && (data.filings?.length ?? 0) === 0 && (
        <EmptyState
          message="No filings yet"
          description="Government filings will appear here once you run payroll and submit statutory reports."
        />
      )}

      {data && (data.filings?.length ?? 0) > 0 && (
        <AppCard variant="standard">
          <div className="overflow-x-auto -mx-5 -my-4">
            <table className="w-full min-w-[700px]">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-gray-50)]">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                    Type
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                    Period
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                    Submitted
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                    Reference
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {(data.filings ?? []).map((filing) => (
                  <FilingRow
                    key={filing.id}
                    filing={filing}
                    onViewDetail={() => setSelectedFilingId(filing.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </AppCard>
      )}

      {/* Detail Drawer */}
      {selectedFilingId && (
        <FilingDetailDrawer
          filingId={selectedFilingId}
          onClose={() => setSelectedFilingId(null)}
        />
      )}
    </div>
  );
}
