"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  DatePicker,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  CalendarDays,
  Plus,
  Check,
  X,
  Palmtree,
  Thermometer,
  Hospital,
  ChevronDown,
  ChevronUp,
  Users,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  leaveApi,
  type LeaveApplication,
  type LeaveBalance,
  type LeaveType,
} from "@/services/api/leave";

/* -- Status badge -------------------------------------------------- */

const STATUS_STYLES: Record<string, string> = {
  draft:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
  withdrawn:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]",
  cancelled:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]",
};

function StatusBadge({ status }: { status: string }) {
  const s = status || "pending";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[s] || STATUS_STYLES.draft}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

/* -- Icon map for leave types --------------------------------------- */

const LEAVE_ICON_MAP: Record<
  string,
  { icon: typeof Palmtree; color: string; bgColor: string }
> = {
  "Annual Leave": {
    icon: Palmtree,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
  },
  "Sick Leave": {
    icon: Thermometer,
    color: "text-amber-600",
    bgColor: "bg-amber-50",
  },
  "Hospitalisation Leave": {
    icon: Hospital,
    color: "text-red-600",
    bgColor: "bg-red-50",
  },
};

const DEFAULT_LEAVE_ICON = {
  icon: CalendarDays,
  color: "text-blue-600",
  bgColor: "bg-blue-50",
};

/* -- Loading skeletons ---------------------------------------------- */

function BalanceCardSkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse">
        <div className="flex items-center gap-3 mb-3">
          <div className="h-9 w-9 rounded-lg bg-[var(--color-gray-200)]" />
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[1, 2, 3].map((n) => (
            <div key={n} className="p-2 rounded-lg bg-[var(--color-gray-50)]">
              <div className="h-5 w-8 bg-[var(--color-gray-200)] rounded mx-auto mb-1" />
              <div className="h-2 w-12 bg-[var(--color-gray-100)] rounded mx-auto" />
            </div>
          ))}
        </div>
      </div>
    </AppCard>
  );
}

function TableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-5 border-b border-[var(--color-gray-100)] last:border-0"
        >
          <div className="h-4 w-28 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-12 bg-[var(--color-gray-200)] rounded" />
          <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* -- Leave Balance Card --------------------------------------------- */

function LeaveBalanceCard({ balance }: { balance: LeaveBalance }) {
  const iconInfo =
    LEAVE_ICON_MAP[balance.leave_type_name] ?? DEFAULT_LEAVE_ICON;
  const Icon = iconInfo.icon;

  return (
    <AppCard variant="flat">
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 rounded-lg ${iconInfo.bgColor} shrink-0`}>
          <Icon className={`h-5 w-5 ${iconInfo.color}`} />
        </div>
        <p className="text-sm font-semibold text-[var(--color-gray-900)]">
          {balance.leave_type_name}
        </p>
      </div>

      <div className="mb-3">
        <div className="h-2 rounded-full bg-[var(--color-gray-100)] overflow-hidden flex">
          <div
            className="h-full bg-[var(--color-primary)] transition-all"
            style={{
              width: `${balance.entitlement > 0 ? (balance.used / balance.entitlement) * 100 : 0}%`,
            }}
          />
          {balance.pending > 0 && (
            <div
              className="h-full bg-[var(--color-primary)] opacity-40 transition-all"
              style={{
                width: `${balance.entitlement > 0 ? (balance.pending / balance.entitlement) * 100 : 0}%`,
              }}
            />
          )}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-1.5 text-center">
        <div className="p-1.5 rounded-lg bg-[var(--color-gray-50)]">
          <p className="text-base font-bold text-[var(--color-gray-900)]">
            {balance.entitlement}
          </p>
          <p className="text-[9px] font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Total
          </p>
        </div>
        <div className="p-1.5 rounded-lg bg-[var(--color-gray-50)]">
          <p className="text-base font-bold text-[var(--color-primary)]">
            {balance.used}
          </p>
          <p className="text-[9px] font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Used
          </p>
        </div>
        <div className="p-1.5 rounded-lg bg-[var(--color-gray-50)]">
          <p className="text-base font-bold text-amber-600">
            {balance.pending}
          </p>
          <p className="text-[9px] font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Pending
          </p>
        </div>
        <div className="p-1.5 rounded-lg bg-[var(--color-gray-50)]">
          <p className="text-base font-bold text-emerald-600">
            {balance.remaining}
          </p>
          <p className="text-[9px] font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Left
          </p>
        </div>
      </div>
    </AppCard>
  );
}

/* -- Apply Leave Modal ---------------------------------------------- */

function ApplyLeaveModal({
  isOpen,
  onClose,
  onSuccess,
  leaveTypes,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  leaveTypes: LeaveType[];
}) {
  const [leaveTypeId, setLeaveTypeId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDayStart, setHalfDayStart] = useState(false);
  const [halfDayEnd, setHalfDayEnd] = useState(false);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!leaveTypeId || !startDate || !endDate) return;

    setIsSubmitting(true);
    try {
      await leaveApi.applyLeave({
        leave_type_id: Number(leaveTypeId),
        start_date: startDate,
        end_date: endDate,
        half_day_start: halfDayStart,
        half_day_end: halfDayEnd,
        reason,
      });
      toast.success("Leave application submitted successfully");
      setLeaveTypeId("");
      setStartDate("");
      setEndDate("");
      setHalfDayStart(false);
      setHalfDayEnd(false);
      setReason("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to submit leave application";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <CalendarDays className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Apply for Leave
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="leave-type"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Leave Type
            </label>
            <select
              id="leave-type"
              value={leaveTypeId}
              onChange={(e) => setLeaveTypeId(e.target.value)}
              className="
                w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                transition-colors
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                focus:border-[var(--color-surface-input-focus)]
              "
              required
            >
              <option value="">Select leave type</option>
              {leaveTypes.map((lt) => (
                <option key={lt.id} value={lt.id}>
                  {lt.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <DatePicker
              label="Start Date"
              value={startDate}
              onChange={setStartDate}
              required
            />
            <DatePicker
              label="End Date"
              value={endDate}
              onChange={setEndDate}
              min={startDate}
              required
            />
          </div>

          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm text-[var(--color-gray-700)] cursor-pointer">
              <input
                type="checkbox"
                checked={halfDayStart}
                onChange={(e) => setHalfDayStart(e.target.checked)}
                className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
              />
              Half-day (start)
            </label>
            <label className="flex items-center gap-2 text-sm text-[var(--color-gray-700)] cursor-pointer">
              <input
                type="checkbox"
                checked={halfDayEnd}
                onChange={(e) => setHalfDayEnd(e.target.checked)}
                className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
              />
              Half-day (end)
            </label>
          </div>

          <AppInput
            variant="textarea"
            label="Reason"
            value={reason}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
              setReason(e.target.value)
            }
            placeholder="Optional reason for leave"
          />

          <p className="text-xs text-[var(--color-gray-500)]">
            You can upload supporting documents (e.g. medical certificate) after
            submitting.
          </p>

          <div className="flex gap-3 pt-2">
            <AppButton
              type="button"
              variant="outlined"
              size="sm"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </AppButton>
            <AppButton
              type="submit"
              variant="primary"
              size="sm"
              loading={isSubmitting}
              className="flex-1"
            >
              Submit Application
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* -- Reject Reason Modal -------------------------------------------- */

function RejectReasonModal({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
  isSubmitting: boolean;
}) {
  const [reason, setReason] = useState("");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-sm mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <h2 className="text-lg font-semibold text-[var(--color-gray-900)] mb-4">
          Reason for Rejection
        </h2>
        <AppInput
          variant="textarea"
          value={reason}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
            setReason(e.target.value)
          }
          placeholder="Enter reason for rejection..."
          required
        />
        <div className="flex gap-3 mt-4">
          <AppButton
            variant="outlined"
            size="sm"
            onClick={onClose}
            className="flex-1"
          >
            Cancel
          </AppButton>
          <AppButton
            variant="danger"
            size="sm"
            onClick={() => onConfirm(reason)}
            loading={isSubmitting}
            disabled={!reason.trim()}
            className="flex-1"
          >
            Reject
          </AppButton>
        </div>
      </div>
    </div>
  );
}

/* -- Admin Pending Approvals ---------------------------------------- */

function PendingApprovals({
  applications,
  onAction,
}: {
  applications: LeaveApplication[];
  onAction: () => void;
}) {
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [showRejectModal, setShowRejectModal] = useState<number | null>(null);

  const pending = applications.filter((a) => a.status === "pending");

  if (pending.length === 0) {
    return (
      <AppCard variant="standard">
        <div className="text-center py-4">
          <Check className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
          <p className="text-sm text-[var(--color-gray-600)]">
            No pending approvals
          </p>
        </div>
      </AppCard>
    );
  }

  async function handleApprove(id: number) {
    setActionLoading(id);
    try {
      await leaveApi.approve(id);
      toast.success("Leave approved");
      onAction();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to approve leave";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject(id: number, reason: string) {
    setActionLoading(id);
    try {
      await leaveApi.reject(id, reason);
      toast.success("Leave rejected");
      setShowRejectModal(null);
      onAction();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to reject leave";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <>
      <AppCard
        variant="standard"
        header={
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Pending Approvals
            </h2>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
              {pending.length} pending
            </span>
          </div>
        }
      >
        <div className="space-y-3 -mx-5 -my-4 px-5 py-4">
          {pending.map((app) => (
            <div
              key={app.id}
              className="flex items-center justify-between gap-3 p-3 rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-gray-50)]"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                  {app.employee_name}
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">
                  {app.leave_type_name} &middot; {app.start_date} to{" "}
                  {app.end_date} &middot; {app.total_days} day
                  {app.total_days !== 1 ? "s" : ""}
                </p>
                {app.reason && (
                  <p className="text-xs text-[var(--color-gray-500)] mt-0.5 truncate">
                    {app.reason}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <AppButton
                  variant="primary"
                  size="sm"
                  onClick={() => handleApprove(app.id)}
                  loading={actionLoading === app.id}
                  disabled={actionLoading !== null}
                >
                  <Check className="h-4 w-4" />
                </AppButton>
                <AppButton
                  variant="danger"
                  size="sm"
                  onClick={() => setShowRejectModal(app.id)}
                  disabled={actionLoading !== null}
                >
                  <X className="h-4 w-4" />
                </AppButton>
              </div>
            </div>
          ))}
        </div>
      </AppCard>

      <RejectReasonModal
        isOpen={showRejectModal !== null}
        onClose={() => setShowRejectModal(null)}
        onConfirm={(reason) => {
          if (showRejectModal !== null) {
            handleReject(showRejectModal, reason);
          }
        }}
        isSubmitting={actionLoading !== null}
      />
    </>
  );
}

/* -- Admin Quick Stats ---------------------------------------------- */

function AdminQuickStats({
  applications,
}: {
  applications: LeaveApplication[];
}) {
  const now = new Date();
  const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const todayStr = now.toISOString().split("T")[0];

  const totalPending = applications.filter(
    (a) => a.status === "pending",
  ).length;
  const approvedThisMonth = applications.filter(
    (a) => a.status === "approved" && a.approved_at?.startsWith(currentMonth),
  ).length;
  const onLeaveToday = applications.filter(
    (a) =>
      a.status === "approved" &&
      a.start_date <= todayStr &&
      a.end_date >= todayStr,
  ).length;

  const stats = [
    {
      label: "Pending",
      value: totalPending,
      color: "text-amber-600",
      bg: "bg-amber-50",
    },
    {
      label: "Approved This Month",
      value: approvedThisMonth,
      color: "text-emerald-600",
      bg: "bg-emerald-50",
    },
    {
      label: "On Leave Today",
      value: onLeaveToday,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {stats.map((stat) => (
        <AppCard key={stat.label} variant="flat">
          <div className="text-center">
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
              {stat.label}
            </p>
          </div>
        </AppCard>
      ))}
    </div>
  );
}

/* -- Application History Table -------------------------------------- */

function ApplicationHistory({
  applications,
  isLoading,
  isAdmin,
  onWithdraw,
}: {
  applications: LeaveApplication[];
  isLoading: boolean;
  isAdmin: boolean;
  onWithdraw: (id: number) => void;
}) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  if (isLoading) {
    return (
      <AppCard variant="standard">
        <div className="-mx-5 -my-4">
          <TableSkeleton />
        </div>
      </AppCard>
    );
  }

  if (applications.length === 0) {
    return (
      <EmptyState
        icon={<CalendarDays className="h-12 w-12" aria-hidden="true" />}
        message="No leave applications"
        description={
          isAdmin
            ? "No leave applications have been submitted yet."
            : "You have not applied for any leave yet."
        }
      />
    );
  }

  return (
    <AppCard variant="standard">
      <div className="overflow-x-auto -mx-5 -my-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-gray-200)]">
              {isAdmin && (
                <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                  Employee
                </th>
              )}
              <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                Leave Type
              </th>
              <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Period
              </th>
              <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Days
              </th>
              <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Status
              </th>
              <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {applications.map((app) => (
              <>
                <tr
                  key={app.id}
                  onClick={() =>
                    setExpandedId(expandedId === app.id ? null : app.id)
                  }
                  className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors cursor-pointer"
                >
                  {isAdmin && (
                    <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                      {app.employee_name}
                    </td>
                  )}
                  <td className="py-3 px-5 text-[var(--color-gray-900)]">
                    {app.leave_type_name}
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)]">
                    {app.start_date} to {app.end_date}
                  </td>
                  <td className="py-3 px-3 text-center text-[var(--color-gray-700)]">
                    {app.total_days}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <StatusBadge status={app.status} />
                  </td>
                  <td className="py-3 px-5 text-center">
                    <div className="flex items-center justify-center gap-1">
                      {!isAdmin && app.status === "pending" && (
                        <AppButton
                          variant="outlined"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            onWithdraw(app.id);
                          }}
                        >
                          Withdraw
                        </AppButton>
                      )}
                      {expandedId === app.id ? (
                        <ChevronUp className="h-4 w-4 text-[var(--color-gray-400)]" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-[var(--color-gray-400)]" />
                      )}
                    </div>
                  </td>
                </tr>
                {expandedId === app.id && (
                  <tr key={`${app.id}-detail`}>
                    <td
                      colSpan={isAdmin ? 6 : 5}
                      className="px-5 py-3 bg-[var(--color-gray-50)]"
                    >
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        {app.reason && (
                          <div>
                            <p className="text-xs font-medium text-[var(--color-gray-500)] mb-0.5">
                              Reason
                            </p>
                            <p className="text-[var(--color-gray-700)]">
                              {app.reason}
                            </p>
                          </div>
                        )}
                        {app.half_day_start && (
                          <div>
                            <p className="text-xs text-[var(--color-gray-500)]">
                              Half-day on start date
                            </p>
                          </div>
                        )}
                        {app.half_day_end && (
                          <div>
                            <p className="text-xs text-[var(--color-gray-500)]">
                              Half-day on end date
                            </p>
                          </div>
                        )}
                        {app.rejection_reason && (
                          <div>
                            <p className="text-xs font-medium text-[var(--color-gray-500)] mb-0.5">
                              Rejection Reason
                            </p>
                            <p className="text-red-700">
                              {app.rejection_reason}
                            </p>
                          </div>
                        )}
                        {app.approver_name && (
                          <div>
                            <p className="text-xs font-medium text-[var(--color-gray-500)] mb-0.5">
                              Reviewed By
                            </p>
                            <p className="text-[var(--color-gray-700)]">
                              {app.approver_name}
                            </p>
                          </div>
                        )}
                        <div>
                          <p className="text-xs font-medium text-[var(--color-gray-500)] mb-0.5">
                            Applied On
                          </p>
                          <p className="text-[var(--color-gray-700)]">
                            {app.created_at.split("T")[0]}
                          </p>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </AppCard>
  );
}

/* -- Page ---------------------------------------------------------- */

export default function LeavePage() {
  const { user } = useAuth();
  const isAdmin =
    user?.role === "owner" ||
    user?.role === "hr_manager" ||
    user?.role === "consultant";

  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([]);
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [activeTab, setActiveTab] = useState<"applications" | "policies">(
    "applications",
  );

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [typesRes, appsRes] = await Promise.all([
        leaveApi.listTypes(),
        leaveApi.listApplications(),
      ]);
      setLeaveTypes(typesRes.types ?? (typesRes as any).leave_types ?? []);
      setApplications(appsRes.applications ?? []);

      if (!isAdmin) {
        try {
          const balancesRes = await leaveApi.getBalances();
          setBalances(balancesRes.balances ?? []);
        } catch {
          setBalances([]);
        }
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load leave data. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleWithdraw(id: number) {
    try {
      await leaveApi.withdraw(id);
      toast.success("Leave application withdrawn");
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to withdraw application";
      toast.error(message);
    }
  }

  if (error && !isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <div className="flex items-center gap-3">
          <CalendarDays
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            {isAdmin ? "Leave Management" : "My Leave"}
          </h1>
        </div>
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={fetchData}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <CalendarDays
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              {isAdmin ? "Leave Management" : "My Leave"}
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              {isAdmin
                ? "Review and manage employee leave applications"
                : "View your leave balances and apply for leave"}
            </p>
          </div>
        </div>
        {!isAdmin && (
          <AppButton
            variant="primary"
            size="sm"
            onClick={() => setShowApplyModal(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Apply for Leave
          </AppButton>
        )}
      </div>

      {/* Tab bar (admin only) */}
      {isAdmin && (
        <div className="flex gap-1 border-b border-[var(--color-gray-200)]">
          {(["applications", "policies"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                  : "border-transparent text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"
              }`}
            >
              {tab === "applications" ? "Applications" : "Leave Policies"}
            </button>
          ))}
        </div>
      )}

      {/* Policies Tab (admin) */}
      {isAdmin && activeTab === "policies" && (
        <AppCard
          variant="standard"
          header={
            <div className="flex items-center gap-2">
              <CalendarDays
                className="h-4 w-4 text-[var(--color-gray-500)]"
                aria-hidden="true"
              />
              <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
                Leave Type Configuration
              </h2>
            </div>
          }
        >
          {leaveTypes.length === 0 ? (
            <p className="text-sm text-[var(--color-gray-500)]">
              No leave types configured yet.
            </p>
          ) : (
            <div className="space-y-3">
              {leaveTypes.map((lt: any) => (
                <div
                  key={lt.id || lt.name || lt.leave_type_name}
                  className="flex items-center justify-between p-3 rounded-lg border border-[var(--color-gray-200)] bg-[var(--color-surface-card)]"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--color-gray-900)]">
                      {lt.name || lt.leave_type_name || "Unnamed"}
                    </p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-[var(--color-gray-500)]">
                      <span>
                        {lt.default_days ?? lt.entitlement_days ?? 0} days
                      </span>
                      <span>{lt.is_paid !== false ? "Paid" : "Unpaid"}</span>
                      {(lt.applicable_gender || lt.gender_restriction) &&
                        (lt.applicable_gender || lt.gender_restriction) !==
                          "all" && (
                          <span className="capitalize">
                            {lt.applicable_gender || lt.gender_restriction} only
                          </span>
                        )}
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      lt.is_active !== false
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-[var(--color-gray-100)] text-[var(--color-gray-500)]"
                    }`}
                  >
                    {lt.is_active !== false ? "Active" : "Inactive"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </AppCard>
      )}

      {/* Admin View — Applications tab */}
      {isAdmin && activeTab === "applications" && (
        <>
          <AdminQuickStats applications={applications} />
          <PendingApprovals applications={applications} onAction={fetchData} />

          {/* Team on leave today */}
          {!isLoading && (
            <AppCard
              variant="standard"
              header={
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-[var(--color-gray-500)]" />
                  <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
                    On Leave Today
                  </h2>
                </div>
              }
            >
              {(() => {
                const todayStr = new Date().toISOString().split("T")[0];
                const onLeave = applications.filter(
                  (a) =>
                    a.status === "approved" &&
                    a.start_date <= todayStr &&
                    a.end_date >= todayStr,
                );
                if (onLeave.length === 0) {
                  return (
                    <p className="text-sm text-[var(--color-gray-500)] text-center py-2">
                      No one is on leave today.
                    </p>
                  );
                }
                return (
                  <div className="space-y-2">
                    {onLeave.map((a) => (
                      <div
                        key={a.id}
                        className="flex items-center justify-between text-sm p-2 rounded-lg bg-[var(--color-gray-50)]"
                      >
                        <span className="font-medium text-[var(--color-gray-900)]">
                          {a.employee_name}
                        </span>
                        <span className="text-[var(--color-gray-500)]">
                          {a.leave_type_name}
                        </span>
                      </div>
                    ))}
                  </div>
                );
              })()}
            </AppCard>
          )}
        </>
      )}

      {/* Employee View: Balances */}
      {!isAdmin && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {isLoading
            ? [1, 2, 3].map((n) => <BalanceCardSkeleton key={n} />)
            : balances.map((b) => (
                <LeaveBalanceCard key={b.leave_type_id} balance={b} />
              ))}
        </div>
      )}

      {/* Application History */}
      <div>
        <h2 className="text-base font-semibold text-[var(--color-gray-900)] mb-3">
          {isAdmin ? "All Applications" : "Application History"}
        </h2>
        <ApplicationHistory
          applications={applications}
          isLoading={isLoading}
          isAdmin={isAdmin}
          onWithdraw={handleWithdraw}
        />
      </div>

      {/* Apply Modal */}
      <ApplyLeaveModal
        isOpen={showApplyModal}
        onClose={() => setShowApplyModal(false)}
        onSuccess={fetchData}
        leaveTypes={leaveTypes}
      />
    </div>
  );
}
