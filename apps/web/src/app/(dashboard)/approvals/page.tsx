"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  ClipboardCheck,
  Timer,
  Package,
  Check,
  X,
  RefreshCw,
  CheckCheck,
} from "lucide-react";
import { projectsApi, type TimesheetEntry } from "@/services/api/projects";
import { inventoryApi, type InventoryRequest } from "@/services/api/inventory";
import { AdminGuard } from "@/components/auth/AdminGuard";

/* ── Helpers ──────────────────────────────────────────────── */

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-SG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/* ── Status badge ─────────────────────────────────────────── */

const STATUS_STYLES: Record<string, string> = {
  submitted: "bg-amber-50 text-amber-700 border-amber-200",
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
  issued: "bg-blue-50 text-blue-700 border-blue-200",
};

function StatusBadge({ status }: { status: string }) {
  const s = status || "pending";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[s] || "bg-gray-50 text-gray-600 border-gray-200"}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

/* ── Loading skeleton ─────────────────────────────────────── */

function TableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 5 }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-5 border-b border-[var(--color-gray-100)] last:border-0"
        >
          <div className="h-4 w-5 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-28 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-12 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded" />
          <div className="h-8 w-20 bg-[var(--color-gray-200)] rounded ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* ── Reject Reason Modal ──────────────────────────────────── */

function RejectModal({
  onConfirm,
  onCancel,
  title,
}: {
  onConfirm: (reason: string) => void;
  onCancel: () => void;
  title: string;
}) {
  const [reason, setReason] = useState("");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-[var(--color-surface-card)] rounded-[12px] border border-[var(--color-gray-200)] shadow-lg max-w-md w-full mx-4 p-6">
        <h3 className="text-base font-semibold text-[var(--color-gray-900)] mb-2">
          {title}
        </h3>
        <p className="text-sm text-[var(--color-gray-500)] mb-4">
          Please provide a reason for this action.
        </p>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Enter reason..."
          rows={3}
          className="
            w-full rounded-[8px] border px-3 py-2 text-sm
            bg-[var(--color-surface-input)] text-[var(--foreground)]
            border-[var(--color-surface-input-border)]
            focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
            focus:border-[var(--color-surface-input-focus)]
            resize-none
          "
        />
        <div className="flex justify-end gap-2 mt-4">
          <AppButton variant="outlined" size="sm" onClick={onCancel}>
            Cancel
          </AppButton>
          <AppButton
            variant="primary"
            size="sm"
            onClick={() => onConfirm(reason)}
            disabled={!reason.trim()}
          >
            Confirm
          </AppButton>
        </div>
      </div>
    </div>
  );
}

/* ── Timesheet Approvals Tab ──────────────────────────────── */

function TimesheetApprovalsTab() {
  const [entries, setEntries] = useState<TimesheetEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [actionInProgress, setActionInProgress] = useState<number | null>(null);
  const [batchInProgress, setBatchInProgress] = useState(false);
  const [rejectingId, setRejectingId] = useState<number | null>(null);

  const fetchEntries = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await projectsApi.listTimesheets({ status: "submitted" });
      setEntries(data.entries ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load timesheet entries.";
      setError(message);
      setEntries([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selected.size === entries.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(entries.map((e) => e.id)));
    }
  }

  async function handleApprove(id: number) {
    setActionInProgress(id);
    try {
      await projectsApi.approveTimesheet(id);
      toast.success("Timesheet approved");
      setEntries((prev) => prev.filter((e) => e.id !== id));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to approve timesheet.";
      toast.error(message);
    } finally {
      setActionInProgress(null);
    }
  }

  async function handleReject(id: number, reason: string) {
    setActionInProgress(id);
    setRejectingId(null);
    try {
      await projectsApi.rejectTimesheet(id, reason);
      toast.success("Timesheet rejected");
      setEntries((prev) => prev.filter((e) => e.id !== id));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to reject timesheet.";
      toast.error(message);
    } finally {
      setActionInProgress(null);
    }
  }

  async function handleBatchApprove() {
    if (selected.size === 0) return;
    setBatchInProgress(true);
    let successCount = 0;
    let failCount = 0;

    for (const id of selected) {
      try {
        await projectsApi.approveTimesheet(id);
        successCount++;
      } catch {
        failCount++;
      }
    }

    if (successCount > 0) {
      toast.success(`${successCount} timesheet(s) approved`);
    }
    if (failCount > 0) {
      toast.error(`${failCount} timesheet(s) failed to approve`);
    }

    setSelected(new Set());
    setBatchInProgress(false);
    fetchEntries();
  }

  if (isLoading) {
    return (
      <AppCard variant="standard">
        <div className="-mx-5 -my-4">
          <TableSkeleton />
        </div>
      </AppCard>
    );
  }

  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-8 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchEntries}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<Timer className="h-12 w-12" aria-hidden="true" />}
        message="No pending timesheets"
        description="All timesheet submissions have been reviewed."
      />
    );
  }

  return (
    <>
      {rejectingId !== null && (
        <RejectModal
          title="Reject Timesheet"
          onConfirm={(reason) => handleReject(rejectingId, reason)}
          onCancel={() => setRejectingId(null)}
        />
      )}

      {/* Batch actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <p className="text-sm text-[var(--color-gray-500)]">
          {entries.length} pending submission{entries.length !== 1 ? "s" : ""}
          {selected.size > 0 && (
            <span className="ml-2 font-medium text-[var(--color-gray-700)]">
              ({selected.size} selected)
            </span>
          )}
        </p>
        <div className="flex flex-wrap gap-2">
          <AppButton
            variant="outlined"
            size="sm"
            onClick={fetchEntries}
            disabled={isLoading}
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Refresh
          </AppButton>
          {selected.size > 0 && (
            <AppButton
              variant="primary"
              size="sm"
              onClick={handleBatchApprove}
              loading={batchInProgress}
            >
              <CheckCheck className="h-3.5 w-3.5 mr-1" />
              Approve Selected
            </AppButton>
          )}
        </div>
      </div>

      <AppCard variant="standard">
        <div className="overflow-x-auto -mx-5 -my-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-gray-200)]">
                <th className="py-3 px-4 w-10">
                  <input
                    type="checkbox"
                    checked={
                      selected.size === entries.length && entries.length > 0
                    }
                    onChange={toggleSelectAll}
                    className="rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
                  />
                </th>
                <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                  Employee
                </th>
                <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                  Project
                </th>
                <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                  Date
                </th>
                <th className="text-right py-3 px-3 font-medium text-[var(--color-gray-500)]">
                  Hours
                </th>
                <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                  Description
                </th>
                <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr
                  key={entry.id}
                  className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                >
                  <td className="py-3 px-4">
                    <input
                      type="checkbox"
                      checked={selected.has(entry.id)}
                      onChange={() => toggleSelect(entry.id)}
                      className="rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
                    />
                  </td>
                  <td className="py-3 px-3 font-medium text-[var(--color-gray-900)]">
                    {entry.employee_name || `Employee #${entry.employee_id}`}
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)]">
                    {entry.project_name || `Project #${entry.project_id}`}
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)]">
                    {formatDate(entry.entry_date)}
                  </td>
                  <td className="py-3 px-3 text-right text-[var(--color-gray-900)] font-medium">
                    {entry.hours}h
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)] max-w-[200px] truncate">
                    {entry.description || "-"}
                  </td>
                  <td className="py-3 px-5">
                    <div className="flex items-center justify-center gap-1.5">
                      <AppButton
                        variant="primary"
                        size="sm"
                        onClick={() => handleApprove(entry.id)}
                        loading={actionInProgress === entry.id}
                        disabled={actionInProgress !== null}
                      >
                        <Check className="h-3.5 w-3.5" />
                      </AppButton>
                      <AppButton
                        variant="outlined"
                        size="sm"
                        onClick={() => setRejectingId(entry.id)}
                        disabled={actionInProgress !== null}
                      >
                        <X className="h-3.5 w-3.5" />
                      </AppButton>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AppCard>
    </>
  );
}

/* ── Inventory Requests Tab ───────────────────────────────── */

function InventoryRequestsTab() {
  const [requests, setRequests] = useState<InventoryRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<number | null>(null);
  const [denyingId, setDenyingId] = useState<number | null>(null);

  const fetchRequests = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await inventoryApi.listRequests();
      /* Filter to pending only on the client side */
      const pending = (data.requests ?? []).filter(
        (r) => r.status === "pending",
      );
      setRequests(pending);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load inventory requests.";
      setError(message);
      setRequests([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  async function handleApprove(id: number) {
    setActionInProgress(id);
    try {
      await inventoryApi.approveRequest(id);
      toast.success("Request approved");
      setRequests((prev) => prev.filter((r) => r.id !== id));
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to approve request.";
      toast.error(message);
    } finally {
      setActionInProgress(null);
    }
  }

  async function handleDeny(id: number, reason: string) {
    setActionInProgress(id);
    setDenyingId(null);
    try {
      await inventoryApi.rejectRequest(id, reason);
      toast.success("Request denied");
      setRequests((prev) => prev.filter((r) => r.id !== id));
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to deny request.";
      toast.error(message);
    } finally {
      setActionInProgress(null);
    }
  }

  if (isLoading) {
    return (
      <AppCard variant="standard">
        <div className="-mx-5 -my-4">
          <TableSkeleton />
        </div>
      </AppCard>
    );
  }

  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-8 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchRequests}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  if (requests.length === 0) {
    return (
      <EmptyState
        icon={<Package className="h-12 w-12" aria-hidden="true" />}
        message="No pending requests"
        description="All inventory requests have been reviewed."
      />
    );
  }

  return (
    <>
      {denyingId !== null && (
        <RejectModal
          title="Deny Inventory Request"
          onConfirm={(reason) => handleDeny(denyingId, reason)}
          onCancel={() => setDenyingId(null)}
        />
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <p className="text-sm text-[var(--color-gray-500)]">
          {requests.length} pending request{requests.length !== 1 ? "s" : ""}
        </p>
        <AppButton
          variant="outlined"
          size="sm"
          onClick={fetchRequests}
          disabled={isLoading}
        >
          <RefreshCw className="h-3.5 w-3.5 mr-1" />
          Refresh
        </AppButton>
      </div>

      <AppCard variant="standard">
        <div className="overflow-x-auto -mx-5 -my-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-gray-200)]">
                <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                  Employee
                </th>
                <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                  Category
                </th>
                <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                  Item
                </th>
                <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                  Reason
                </th>
                <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                  Requested
                </th>
                <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {requests.map((req) => (
                <tr
                  key={req.id}
                  className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                >
                  <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                    {req.employee_name || `Employee #${req.employee_id}`}
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)]">
                    {req.category_name || "-"}
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)]">
                    {req.item_name || "-"}
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)] max-w-[200px] truncate">
                    {req.description || "-"}
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)]">
                    {formatDate(req.created_at)}
                  </td>
                  <td className="py-3 px-5">
                    <div className="flex items-center justify-center gap-1.5">
                      <AppButton
                        variant="primary"
                        size="sm"
                        onClick={() => handleApprove(req.id)}
                        loading={actionInProgress === req.id}
                        disabled={actionInProgress !== null}
                      >
                        <Check className="h-3.5 w-3.5" />
                      </AppButton>
                      <AppButton
                        variant="outlined"
                        size="sm"
                        onClick={() => setDenyingId(req.id)}
                        disabled={actionInProgress !== null}
                      >
                        <X className="h-3.5 w-3.5" />
                      </AppButton>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AppCard>
    </>
  );
}

/* ── Page ──────────────────────────────────────────────────── */

type TabKey = "timesheets" | "inventory";

const TABS: { key: TabKey; label: string; icon: typeof Timer }[] = [
  { key: "timesheets", label: "Timesheet Approvals", icon: Timer },
  { key: "inventory", label: "Inventory Requests", icon: Package },
];

export default function ApprovalsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("timesheets");

  return (
    <AdminGuard>
      <div className="max-w-5xl mx-auto space-y-6 pb-8">
        {/* Header */}
        <div className="flex items-center gap-3">
          <ClipboardCheck
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Approvals
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Review and action pending timesheet entries and inventory requests
            </p>
          </div>
        </div>

        {/* Tabs — horizontally scrollable on narrow viewports so the row never breaks */}
        <div className="flex gap-1 border-b border-[var(--color-gray-200)] overflow-x-auto -mx-5 px-5 sm:mx-0 sm:px-0">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`
                flex items-center gap-2 px-4 py-2.5 text-sm font-medium
                border-b-2 transition-colors -mb-px
                ${
                  isActive
                    ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                    : "border-transparent text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] hover:border-[var(--color-gray-300)]"
                }
              `}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab content */}
        {activeTab === "timesheets" ? (
          <TimesheetApprovalsTab />
        ) : (
          <InventoryRequestsTab />
        )}
      </div>
    </AdminGuard>
  );
}
