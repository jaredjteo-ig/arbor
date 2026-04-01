"use client";

import { useState, useEffect } from "react";
import { AppCard } from "@/components/design-system";
import {
  CalendarDays,
  Palmtree,
  Thermometer,
  Hospital,
  Info,
} from "lucide-react";
import { employeesApi, type LeaveBalance } from "@/services/api/employees";

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

  useEffect(() => {
    let cancelled = false;

    async function fetchLeaveBalances() {
      try {
        const data = await employeesApi.leaveBalances();
        if (!cancelled && data.balances && data.balances.length > 0) {
          setLeaveTypes(data.balances.map(mapBalanceToLeaveType));
          setIsStatutoryFallback(false);
        } else {
          if (!cancelled) {
            setLeaveTypes(STATUTORY_DEFAULTS);
            setIsStatutoryFallback(true);
          }
        }
      } catch {
        if (!cancelled) {
          setLeaveTypes(STATUTORY_DEFAULTS);
          setIsStatutoryFallback(true);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    fetchLeaveBalances();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
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
            View your leave balances and entitlements
          </p>
        </div>
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
    </div>
  );
}
