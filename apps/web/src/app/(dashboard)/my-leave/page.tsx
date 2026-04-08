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
  Palmtree,
  Thermometer,
  Hospital,
  Info,
  Plus,
  X,
  Clock,
} from "lucide-react";
import { employeesApi, type LeaveBalance } from "@/services/api/employees";
import {
  leaveApi,
  type LeaveApplication,
  type LeaveType as ApiLeaveType,
} from "@/services/api/leave";

/* -- Types --------------------------------------------------------- */

interface LeaveType {
  name: string;
  icon: typeof Palmtree;
  color: string;
  bgColor: string;
  entitlement: number;
  used: number;
  pending: number;
}

/* -- Statutory defaults (Singapore Employment Act minimums) --------- */

const STATUTORY_DEFAULTS: LeaveType[] = [
  {
    name: "Annual Leave",
    icon: Palmtree,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    entitlement: 7,
    used: 0,
    pending: 0,
  },
  {
    name: "Sick Leave",
    icon: Thermometer,
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    entitlement: 14,
    used: 0,
    pending: 0,
  },
  {
    name: "Hospitalisation Leave",
    icon: Hospital,
    color: "text-red-600",
    bgColor: "bg-red-50",
    entitlement: 60,
    used: 0,
    pending: 0,
  },
];

/* -- Icon mapping for API data ------------------------------------- */

const LEAVE_TYPE_LABELS: Record<string, string> = {
  annual: "Annual Leave",
  sick: "Sick Leave",
  hospitalization: "Hospitalisation Leave",
};

const ICON_MAP: Record<
  string,
  { icon: typeof Palmtree; color: string; bgColor: string }
> = {
  annual: {
    icon: Palmtree,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
  },
  sick: {
    icon: Thermometer,
    color: "text-amber-600",
    bgColor: "bg-amber-50",
  },
  hospitalization: {
    icon: Hospital,
    color: "text-red-600",
    bgColor: "bg-red-50",
  },
};

const DEFAULT_ICON = {
  icon: CalendarDays,
  color: "text-blue-600",
  bgColor: "bg-blue-50",
};

function mapBalanceToLeaveType(balance: LeaveBalance): LeaveType {
  const leaveType = balance.leave_type ?? "";
  const iconInfo = ICON_MAP[leaveType] ?? DEFAULT_ICON;
  const label =
    LEAVE_TYPE_LABELS[leaveType] ??
    leaveType.charAt(0).toUpperCase() + leaveType.slice(1);
  return {
    name: label,
    icon: iconInfo.icon,
    color: iconInfo.color,
    bgColor: iconInfo.bgColor,
    entitlement: balance.entitlement_days ?? 0,
    used: balance.used_days ?? 0,
    pending: balance.pending_days ?? 0,
  };
}

/* -- Loading skeleton ---------------------------------------------- */

function LeaveCardSkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse">
        <div className="flex items-start gap-3 mb-4">
          <div className="h-9 w-9 rounded-lg bg-[var(--color-gray-200)]" />
          <div>
            <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded mb-1" />
            <div className="h-3 w-32 bg-[var(--color-gray-100)] rounded" />
          </div>
        </div>
        <div className="h-3 w-full bg-[var(--color-gray-200)] rounded-full mb-4" />
        <div className="grid grid-cols-3 gap-2">
          {[1, 2, 3].map((n) => (
            <div key={n} className="p-2 rounded-lg bg-[var(--color-gray-50)]">
              <div className="h-5 w-8 bg-[var(--color-gray-200)] rounded mx-auto mb-1" />
              <div className="h-2 w-16 bg-[var(--color-gray-100)] rounded mx-auto" />
            </div>
          ))}
        </div>
      </div>
    </AppCard>
  );
}

/* -- Leave Balance Card -------------------------------------------- */

function LeaveBalanceCard({
  leave,
  isStatutoryFallback,
}: {
  leave: LeaveType;
  isStatutoryFallback: boolean;
}) {
  const remaining = leave.entitlement - leave.used - leave.pending;
  const usedPercent =
    leave.entitlement > 0 ? (leave.used / leave.entitlement) * 100 : 0;
  const pendingPercent =
    leave.entitlement > 0 ? (leave.pending / leave.entitlement) * 100 : 0;
  const Icon = leave.icon;

  return (
    <AppCard variant="flat">
      <div className="flex items-start gap-3 mb-4">
        <div className={`p-2 rounded-lg ${leave.bgColor} shrink-0`}>
          <Icon className={`h-5 w-5 ${leave.color}`} />
        </div>
        <div>
          <p className="text-sm font-semibold text-[var(--color-gray-900)]">
            {leave.name}
          </p>
          <p className="text-xs text-[var(--color-gray-500)]">
            {isStatutoryFallback ? "Statutory minimum" : "Per Employment Act"}
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="h-3 rounded-full bg-[var(--color-gray-100)] overflow-hidden flex">
          <div
            className="h-full bg-[var(--color-primary)] transition-all"
            style={{ width: `${usedPercent}%` }}
          />
          {leave.pending > 0 && (
            <div
              className="h-full bg-[var(--color-primary)] opacity-40 transition-all"
              style={{ width: `${pendingPercent}%` }}
            />
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="p-2 rounded-lg bg-[var(--color-gray-50)]">
          <p className="text-lg font-bold text-[var(--color-gray-900)]">
            {leave.entitlement}
          </p>
          <p className="text-[10px] font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Entitlement
          </p>
        </div>
        <div className="p-2 rounded-lg bg-[var(--color-gray-50)]">
          <p className="text-lg font-bold text-[var(--color-primary)]">
            {leave.used}
          </p>
          <p className="text-[10px] font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Used
          </p>
        </div>
        <div className="p-2 rounded-lg bg-[var(--color-gray-50)]">
          <p className="text-lg font-bold text-emerald-600">{remaining}</p>
          <p className="text-[10px] font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Remaining
          </p>
        </div>
      </div>

      {leave.pending > 0 && (
        <p className="text-xs text-[var(--color-gray-500)] mt-3 text-center">
          {leave.pending} day{leave.pending !== 1 ? "s" : ""} pending approval
        </p>
      )}
    </AppCard>
  );
}

/* -- Page ---------------------------------------------------------- */

export default function MyLeavePage() {
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isStatutoryFallback, setIsStatutoryFallback] = useState(false);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [apiLeaveTypes, setApiLeaveTypes] = useState<ApiLeaveType[]>([]);
  const [applications, setApplications] = useState<LeaveApplication[]>([]);

  const fetchData = useCallback(async () => {
    try {
      const [balancesData, typesData, appsData] = await Promise.all([
        employeesApi.leaveBalances(),
        leaveApi.listTypes().catch(() => ({ leave_types: [] })),
        leaveApi.listApplications().catch(() => ({ applications: [] })),
      ]);

      if (balancesData.balances && balancesData.balances.length > 0) {
        setLeaveTypes(balancesData.balances.map(mapBalanceToLeaveType));
        setIsStatutoryFallback(false);
      } else {
        setLeaveTypes(STATUTORY_DEFAULTS);
        setIsStatutoryFallback(true);
      }
      setApiLeaveTypes(typesData.leave_types || []);
      setApplications(appsData.applications || []);
    } catch {
      setLeaveTypes(STATUTORY_DEFAULTS);
      setIsStatutoryFallback(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CalendarDays
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              My Leave
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              View your leave balances and apply for leave
            </p>
          </div>
        </div>
        <AppButton onClick={() => setShowApplyModal(true)}>
          <Plus className="h-4 w-4" />
          Apply for Leave
        </AppButton>
      </div>

      {/* Statutory fallback notice */}
      {!isLoading && isStatutoryFallback && (
        <div className="flex items-start gap-2 rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-gray-50)] px-4 py-3">
          <Info className="h-4 w-4 text-[var(--color-gray-500)] mt-0.5 shrink-0" />
          <p className="text-sm text-[var(--color-gray-600)]">
            These are statutory minimums under Singapore law. Your actual
            balances may differ — contact HR for details.
          </p>
        </div>
      )}

      {/* Leave cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading
          ? [1, 2, 3].map((n) => <LeaveCardSkeleton key={n} />)
          : leaveTypes.map((leave) => (
              <LeaveBalanceCard
                key={leave.name}
                leave={leave}
                isStatutoryFallback={isStatutoryFallback}
              />
            ))}
      </div>

      {/* Summary table */}
      {!isLoading && leaveTypes.length > 0 && (
        <AppCard
          variant="standard"
          header={
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Leave Summary
            </h2>
          }
        >
          <div className="overflow-x-auto -mx-5">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)]">
                  <th className="text-left py-2 px-5 font-medium text-[var(--color-gray-500)]">
                    Leave Type
                  </th>
                  <th className="text-center py-2 px-3 font-medium text-[var(--color-gray-500)]">
                    Entitlement
                  </th>
                  <th className="text-center py-2 px-3 font-medium text-[var(--color-gray-500)]">
                    Used
                  </th>
                  <th className="text-center py-2 px-3 font-medium text-[var(--color-gray-500)]">
                    Pending
                  </th>
                  <th className="text-center py-2 px-5 font-medium text-[var(--color-gray-500)]">
                    Remaining
                  </th>
                </tr>
              </thead>
              <tbody>
                {leaveTypes.map((leave) => {
                  const remaining =
                    leave.entitlement - leave.used - leave.pending;
                  return (
                    <tr
                      key={leave.name}
                      className="border-b border-[var(--color-gray-100)] last:border-0"
                    >
                      <td className="py-3 px-5 text-[var(--color-gray-900)] font-medium">
                        {leave.name}
                      </td>
                      <td className="py-3 px-3 text-center text-[var(--color-gray-700)]">
                        {leave.entitlement}
                      </td>
                      <td className="py-3 px-3 text-center text-[var(--color-primary)]">
                        {leave.used}
                      </td>
                      <td className="py-3 px-3 text-center text-[var(--color-gray-500)]">
                        {leave.pending}
                      </td>
                      <td className="py-3 px-5 text-center font-semibold text-emerald-600">
                        {remaining}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </AppCard>
      )}

      {/* Application History */}
      <div>
        <h2 className="text-lg font-semibold text-[var(--color-gray-900)] mb-3">
          Application History
        </h2>
        {applications.length === 0 ? (
          <EmptyState
            icon={<Clock className="h-10 w-10 text-[var(--color-gray-300)]" />}
            message="No leave applications"
            description="You have not applied for any leave yet."
          />
        ) : (
          <div className="space-y-2">
            {applications.map((app) => (
              <AppCard key={app.id} variant="standard">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-[var(--color-gray-900)]">
                      {app.leave_type_name || "Leave"}
                    </p>
                    <p className="text-sm text-[var(--color-gray-500)]">
                      {app.start_date} to {app.end_date}
                      {app.reason && ` — ${app.reason}`}
                    </p>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      app.status === "approved"
                        ? "bg-emerald-50 text-emerald-700"
                        : app.status === "rejected"
                          ? "bg-red-50 text-red-700"
                          : app.status === "withdrawn"
                            ? "bg-gray-100 text-gray-600"
                            : "bg-amber-50 text-amber-700"
                    }`}
                  >
                    {app.status.charAt(0).toUpperCase() + app.status.slice(1)}
                  </span>
                </div>
              </AppCard>
            ))}
          </div>
        )}
      </div>

      {/* Apply Leave Modal */}
      {showApplyModal && (
        <ApplyLeaveModal
          onClose={() => setShowApplyModal(false)}
          onSuccess={() => {
            setShowApplyModal(false);
            fetchData();
          }}
          leaveTypes={apiLeaveTypes}
        />
      )}
    </div>
  );
}

/* -- Apply Leave Modal --------------------------------------------- */

function ApplyLeaveModal({
  onClose,
  onSuccess,
  leaveTypes,
}: {
  onClose: () => void;
  onSuccess: () => void;
  leaveTypes: ApiLeaveType[];
}) {
  const [leaveTypeId, setLeaveTypeId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDayStart, setHalfDayStart] = useState(false);
  const [halfDayEnd, setHalfDayEnd] = useState(false);
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!leaveTypeId || !startDate || !endDate) return;

    setIsSubmitting(true);
    try {
      await leaveApi.applyLeave({
        leave_type_id: Number(leaveTypeId),
        start_date: startDate,
        end_date: endDate,
        start_half: halfDayStart ? "am" : "full_day",
        end_half: halfDayEnd ? "pm" : "full_day",
        reason,
      });
      toast.success("Leave application submitted successfully");
      onSuccess();
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
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
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
                className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)]"
              />
              Half-day (start)
            </label>
            <label className="flex items-center gap-2 text-sm text-[var(--color-gray-700)] cursor-pointer">
              <input
                type="checkbox"
                checked={halfDayEnd}
                onChange={(e) => setHalfDayEnd(e.target.checked)}
                className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)]"
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
              variant="secondary"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </AppButton>
            <AppButton type="submit" disabled={isSubmitting} className="flex-1">
              {isSubmitting ? "Submitting..." : "Submit Application"}
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}
