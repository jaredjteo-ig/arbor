"use client";

import { AppCard } from "@/components/design-system";
import { CalendarDays, Palmtree, Thermometer, Hospital } from "lucide-react";

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

/* -- Placeholder data ---------------------------------------------- */

const LEAVE_TYPES: LeaveType[] = [
  {
    name: "Annual Leave",
    icon: Palmtree,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    entitlement: 14,
    used: 5,
    pending: 1,
  },
  {
    name: "Sick Leave",
    icon: Thermometer,
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    entitlement: 14,
    used: 2,
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

/* -- Leave Balance Card -------------------------------------------- */

function LeaveBalanceCard({ leave }: { leave: LeaveType }) {
  const remaining = leave.entitlement - leave.used - leave.pending;
  const usedPercent = (leave.used / leave.entitlement) * 100;
  const pendingPercent = (leave.pending / leave.entitlement) * 100;
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
            Per Employment Act
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

      {/* Leave cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {LEAVE_TYPES.map((leave) => (
          <LeaveBalanceCard key={leave.name} leave={leave} />
        ))}
      </div>

      {/* Summary table */}
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
              {LEAVE_TYPES.map((leave) => {
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
    </div>
  );
}
