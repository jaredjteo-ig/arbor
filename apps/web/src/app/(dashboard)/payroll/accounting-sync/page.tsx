"use client";

import {
  BookOpen,
  CheckCircle,
  Clock,
  XCircle,
  AlertCircle,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import {
  AppCard,
  AppButton,
  LoadingState,
  ErrorState,
  EmptyState,
  toast,
} from "@/components/design-system";
import { useAccountingSync, useSyncPayrollRun } from "@/hooks/api";
import type {
  AccountingSyncRecord,
  SyncStatus,
} from "@/services/api/integrations";

/* ── Status Config ───────────────────────────────────────── */

const SYNC_STATUS_CONFIG: Record<
  SyncStatus,
  { icon: typeof CheckCircle; color: string; bg: string; label: string }
> = {
  synced: {
    icon: CheckCircle,
    color: "text-[var(--color-success)]",
    bg: "bg-[var(--color-success-bg)]",
    label: "Synced",
  },
  pending: {
    icon: Clock,
    color: "text-[var(--color-warning)]",
    bg: "bg-[var(--color-warning-bg)]",
    label: "Pending",
  },
  failed: {
    icon: XCircle,
    color: "text-[var(--color-error)]",
    bg: "bg-[var(--color-error-bg)]",
    label: "Failed",
  },
  not_synced: {
    icon: AlertCircle,
    color: "text-[var(--color-gray-400)]",
    bg: "bg-[var(--color-gray-100)]",
    label: "Not Synced",
  },
};

function SyncStatusBadge({ status }: { status: SyncStatus }) {
  const config = SYNC_STATUS_CONFIG[status];
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

/* ── Reconciliation Summary ──────────────────────────────── */

function ReconciliationSummary({ record }: { record: AccountingSyncRecord }) {
  const formatCurrency = (amount: number | null) => {
    if (amount === null) return "-";
    return new Intl.NumberFormat("en-SG", {
      style: "currency",
      currency: "SGD",
    }).format(amount);
  };

  const hasVariance =
    record.variance !== null && Math.abs(record.variance) > 0.01;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
      <div className="rounded-lg bg-[var(--color-gray-50)] p-3">
        <p className="text-xs text-[var(--color-gray-500)]">Payroll</p>
        <p className="text-sm font-semibold text-[var(--color-gray-900)]">
          {formatCurrency(record.payroll_amount)}
        </p>
      </div>
      <div className="rounded-lg bg-[var(--color-gray-50)] p-3">
        <p className="text-xs text-[var(--color-gray-500)]">Accounting</p>
        <p className="text-sm font-semibold text-[var(--color-gray-900)]">
          {formatCurrency(record.accounting_amount)}
        </p>
      </div>
      <div className="rounded-lg bg-[var(--color-gray-50)] p-3">
        <p className="text-xs text-[var(--color-gray-500)]">Bank</p>
        <p className="text-sm font-semibold text-[var(--color-gray-900)]">
          {formatCurrency(record.bank_amount)}
        </p>
      </div>
      <div
        className={`rounded-lg p-3 ${hasVariance ? "bg-[var(--color-error-bg)]" : "bg-[var(--color-success-bg)]"}`}
      >
        <p className="text-xs text-[var(--color-gray-500)]">Variance</p>
        <p
          className={`text-sm font-semibold ${hasVariance ? "text-[var(--color-error)]" : "text-[var(--color-success)]"}`}
        >
          {formatCurrency(record.variance)}
        </p>
      </div>
    </div>
  );
}

/* ── Sync Record Card ────────────────────────────────────── */

function SyncRecordCard({ record }: { record: AccountingSyncRecord }) {
  const syncRun = useSyncPayrollRun();

  const handleSync = async () => {
    try {
      await syncRun.mutateAsync(record.run_id);
      toast.success("Sync initiated for this payroll run.");
    } catch {
      toast.error("Sync failed. Please try again.");
    }
  };

  return (
    <AppCard variant="standard">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <p className="text-sm font-semibold text-[var(--color-gray-900)]">
              {record.period}
            </p>
            <SyncStatusBadge status={record.sync_status} />
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--color-gray-500)]">
            <span>Run #{record.run_id}</span>
            <span>Provider: {record.provider}</span>
            {record.journal_reference && (
              <span>Journal: {record.journal_reference}</span>
            )}
            {record.synced_at && (
              <span>
                Synced:{" "}
                {new Date(record.synced_at).toLocaleString("en-SG", {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {record.sync_status !== "synced" && (
            <AppButton
              variant="primary"
              size="sm"
              onClick={handleSync}
              loading={syncRun.isPending}
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Sync Now
            </AppButton>
          )}
          {record.journal_url && (
            <a
              href={record.journal_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              <AppButton variant="outlined" size="sm">
                View Journal
                <ExternalLink className="h-3 w-3" aria-hidden="true" />
              </AppButton>
            </a>
          )}
        </div>
      </div>

      {/* Reconciliation */}
      <ReconciliationSummary record={record} />
    </AppCard>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function AccountingSyncPage() {
  const { data, isPending, error, refetch } = useAccountingSync();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BookOpen
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Accounting Sync
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Sync payroll runs to your accounting software and reconcile amounts.
          </p>
        </div>
      </div>

      {/* Content */}
      {isPending && <LoadingState variant="card" count={3} />}

      {error && (
        <ErrorState
          variant="server"
          title="Could not load sync status"
          description="We had trouble reaching the accounting sync service."
          onRetry={() => refetch()}
        />
      )}

      {data && data.records.length === 0 && (
        <EmptyState
          message="No payroll runs to sync"
          description="Run payroll first, then come back here to sync to your accounting software."
        />
      )}

      {data &&
        data.records.map((record) => (
          <SyncRecordCard key={record.run_id} record={record} />
        ))}
    </div>
  );
}
