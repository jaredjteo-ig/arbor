"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  Clock,
  LogIn,
  LogOut,
  Users,
  CheckCircle2,
  MinusCircle,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  attendanceApi,
  type AttendanceRecord,
  type TodayAttendance,
} from "@/services/api/attendance";

/* -- Time formatter ------------------------------------------------- */

function formatTime(isoString: string | null): string {
  if (!isoString) return "--:--";
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString("en-SG", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return isoString;
  }
}

function formatHours(hours: number | null): string {
  if (hours === null || hours === undefined) return "-";
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return `${h}h ${m}m`;
}

/* -- Status styles -------------------------------------------------- */

const ATTENDANCE_STATUS_STYLES: Record<
  string,
  { bg: string; text: string; label: string }
> = {
  present: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    label: "On Time",
  },
  late: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    label: "Late",
  },
  absent: {
    bg: "bg-red-50",
    text: "text-red-700",
    label: "Absent",
  },
  half_day: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    label: "Half Day",
  },
  on_leave: {
    bg: "bg-purple-50",
    text: "text-purple-700",
    label: "On Leave",
  },
  not_clocked_in: {
    bg: "bg-[var(--color-gray-100)]",
    text: "text-[var(--color-gray-500)]",
    label: "Not Clocked In",
  },
};

function AttendanceStatusBadge({ status }: { status: string }) {
  const style =
    ATTENDANCE_STATUS_STYLES[status] ?? ATTENDANCE_STATUS_STYLES.not_clocked_in;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  );
}

/* -- Status dot (for admin overview) -------------------------------- */

function StatusDot({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    present: "bg-emerald-500",
    late: "bg-amber-500",
    absent: "bg-red-500",
    on_leave: "bg-purple-500",
    not_clocked_in: "bg-[var(--color-gray-300)]",
  };
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${colorMap[status] || colorMap.not_clocked_in}`}
    />
  );
}

/* -- Loading skeletons ---------------------------------------------- */

function ClockCardSkeleton() {
  return (
    <AppCard variant="elevated">
      <div className="animate-pulse flex flex-col items-center py-6">
        <div className="h-16 w-16 rounded-full bg-[var(--color-gray-200)] mb-4" />
        <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded mb-2" />
        <div className="h-12 w-40 bg-[var(--color-gray-200)] rounded" />
      </div>
    </AppCard>
  );
}

function TableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 5 }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-5 border-b border-[var(--color-gray-100)] last:border-0"
        >
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-12 bg-[var(--color-gray-200)] rounded" />
          <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* -- Employee Clock In/Out Card ------------------------------------- */

function ClockCard({
  todayRecord,
  isLoading,
  onRefresh,
}: {
  todayRecord: AttendanceRecord | null;
  isLoading: boolean;
  onRefresh: () => void;
}) {
  const [actionLoading, setActionLoading] = useState(false);

  if (isLoading) return <ClockCardSkeleton />;

  const isClockedIn = todayRecord?.clock_in && !todayRecord?.clock_out;
  const isCompleted = todayRecord?.clock_in && todayRecord?.clock_out;

  async function handleClockIn() {
    setActionLoading(true);
    try {
      await attendanceApi.clockIn();
      toast.success("Clocked in successfully");
      await onRefresh();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to clock in";
      toast.error(message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleClockOut() {
    setActionLoading(true);
    try {
      await attendanceApi.clockOut();
      toast.success("Clocked out successfully");
      await onRefresh();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to clock out";
      toast.error(message);
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <AppCard variant="elevated">
      <div className="flex flex-col items-center py-4">
        {/* Status icon */}
        <div
          className={`h-16 w-16 rounded-full flex items-center justify-center mb-4 ${
            isClockedIn
              ? "bg-emerald-50"
              : isCompleted
                ? "bg-blue-50"
                : "bg-[var(--color-gray-100)]"
          }`}
        >
          {isClockedIn ? (
            <CheckCircle2 className="h-8 w-8 text-emerald-500" />
          ) : isCompleted ? (
            <Clock className="h-8 w-8 text-blue-500" />
          ) : (
            <MinusCircle className="h-8 w-8 text-[var(--color-gray-400)]" />
          )}
        </div>

        {/* Status text */}
        <p className="text-sm text-[var(--color-gray-600)] mb-1">
          {isClockedIn
            ? `Clocked in since ${formatTime(todayRecord?.clock_in ?? null)}`
            : isCompleted
              ? `Completed ${formatHours(todayRecord?.work_hours ?? null)} today`
              : "You have not clocked in today"}
        </p>

        {todayRecord && (
          <div className="flex items-center gap-4 text-xs text-[var(--color-gray-500)] mb-4">
            {todayRecord.clock_in && (
              <span>In: {formatTime(todayRecord.clock_in)}</span>
            )}
            {todayRecord.clock_out && (
              <span>Out: {formatTime(todayRecord.clock_out)}</span>
            )}
            {todayRecord.work_hours !== null &&
              todayRecord.work_hours !== undefined && (
                <span>Total: {formatHours(todayRecord.work_hours)}</span>
              )}
          </div>
        )}

        {/* Action button */}
        {!isCompleted && (
          <AppButton
            variant={isClockedIn ? "danger" : "primary"}
            size="lg"
            onClick={isClockedIn ? handleClockOut : handleClockIn}
            loading={actionLoading}
            className="min-w-[200px]"
          >
            {isClockedIn ? (
              <>
                <LogOut className="h-5 w-5 mr-2" />
                Clock Out
              </>
            ) : (
              <>
                <LogIn className="h-5 w-5 mr-2" />
                Clock In
              </>
            )}
          </AppButton>
        )}

        {isCompleted && (
          <p className="text-xs text-emerald-600 font-medium">
            Work day completed
          </p>
        )}
      </div>
    </AppCard>
  );
}

/* -- Employee History Table ----------------------------------------- */

function AttendanceHistory({
  records,
  isLoading,
}: {
  records: AttendanceRecord[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <AppCard variant="standard">
        <div className="-mx-5 -my-4">
          <TableSkeleton />
        </div>
      </AppCard>
    );
  }

  if (records.length === 0) {
    return (
      <EmptyState
        icon={<Clock className="h-12 w-12" aria-hidden="true" />}
        message="No attendance records"
        description="Your attendance records will appear here."
      />
    );
  }

  return (
    <AppCard variant="standard">
      <div className="overflow-x-auto -mx-5 -my-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-gray-200)]">
              <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                Date
              </th>
              <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Clock In
              </th>
              <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Clock Out
              </th>
              <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Hours
              </th>
              <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr
                key={record.id}
                className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
              >
                <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                  {record.date}
                </td>
                <td className="py-3 px-3 text-center text-[var(--color-gray-600)]">
                  {formatTime(record.clock_in)}
                </td>
                <td className="py-3 px-3 text-center text-[var(--color-gray-600)]">
                  {formatTime(record.clock_out)}
                </td>
                <td className="py-3 px-3 text-center text-[var(--color-gray-700)]">
                  {formatHours(record.work_hours)}
                </td>
                <td className="py-3 px-5 text-center">
                  <AttendanceStatusBadge status={record.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppCard>
  );
}

/* -- Admin Today Overview ------------------------------------------- */

function TodayOverview({
  employees,
  isLoading,
}: {
  employees: TodayAttendance[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <AppCard variant="standard">
        <div className="-mx-5 -my-4">
          <TableSkeleton />
        </div>
      </AppCard>
    );
  }

  const onTime = employees.filter((e) => e.status === "present").length;
  const late = employees.filter((e) => e.status === "late").length;
  const absent = employees.filter((e) => e.status === "absent").length;
  const onLeave = employees.filter((e) => e.status === "on_leave").length;
  const notClockedIn = employees.filter(
    (e) => e.status === "not_clocked_in",
  ).length;

  return (
    <>
      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <AppCard variant="flat">
          <div className="text-center">
            <p className="text-2xl font-bold text-emerald-600">{onTime}</p>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
              On Time
            </p>
          </div>
        </AppCard>
        <AppCard variant="flat">
          <div className="text-center">
            <p className="text-2xl font-bold text-amber-600">{late}</p>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5">Late</p>
          </div>
        </AppCard>
        <AppCard variant="flat">
          <div className="text-center">
            <p className="text-2xl font-bold text-red-600">{absent}</p>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
              Absent
            </p>
          </div>
        </AppCard>
        <AppCard variant="flat">
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-600">{onLeave}</p>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
              On Leave
            </p>
          </div>
        </AppCard>
        <AppCard variant="flat">
          <div className="text-center">
            <p className="text-2xl font-bold text-[var(--color-gray-500)]">
              {notClockedIn}
            </p>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
              Not In
            </p>
          </div>
        </AppCard>
      </div>

      {/* Employee list */}
      <AppCard
        variant="standard"
        header={
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-[var(--color-gray-500)]" />
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Today&apos;s Attendance
            </h2>
          </div>
        }
      >
        {employees.length === 0 ? (
          <p className="text-sm text-[var(--color-gray-500)] text-center py-4">
            No attendance data for today.
          </p>
        ) : (
          <div className="overflow-x-auto -mx-5 -my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)]">
                  <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                    Employee
                  </th>
                  <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Clock In
                  </th>
                  <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Clock Out
                  </th>
                  <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {employees.map((emp) => (
                  <tr
                    key={emp.employee_id}
                    className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                  >
                    <td className="py-3 px-5">
                      <div className="flex items-center gap-2">
                        <StatusDot status={emp.status} />
                        <span className="font-medium text-[var(--color-gray-900)]">
                          {emp.employee_name}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-center text-[var(--color-gray-600)]">
                      {formatTime(emp.clock_in)}
                    </td>
                    <td className="py-3 px-3 text-center text-[var(--color-gray-600)]">
                      {formatTime(emp.clock_out)}
                    </td>
                    <td className="py-3 px-5 text-center">
                      <AttendanceStatusBadge status={emp.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AppCard>
    </>
  );
}

/* -- Monthly Summary ------------------------------------------------ */

function MonthlySummary({ records }: { records: AttendanceRecord[] }) {
  if (records.length === 0) return null;

  const totalDays = records.length;
  const presentDays = records.filter(
    (r) => r.status === "present" || r.status === "late",
  ).length;
  const lateDays = records.filter((r) => r.status === "late").length;
  const absentDays = records.filter((r) => r.status === "absent").length;
  const recordsWithHours = records.filter((r) => r.work_hours !== null);
  const avgHours =
    recordsWithHours.length > 0
      ? recordsWithHours.reduce((sum, r) => sum + (r.work_hours ?? 0), 0) /
        recordsWithHours.length
      : 0;

  return (
    <AppCard
      variant="standard"
      header={
        <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
          Monthly Summary
        </h2>
      }
    >
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="text-center">
          <p className="text-xl font-bold text-[var(--color-gray-900)]">
            {presentDays}/{totalDays}
          </p>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Days Present
          </p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-amber-600">{lateDays}</p>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Late Days
          </p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-red-600">{absentDays}</p>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Absent Days
          </p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-[var(--color-primary)]">
            {formatHours(avgHours)}
          </p>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Avg Hours/Day
          </p>
        </div>
      </div>
    </AppCard>
  );
}

/* -- Page ---------------------------------------------------------- */

export default function AttendancePage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "hr_manager";

  const [todayRecord, setTodayRecord] = useState<AttendanceRecord | null>(null);
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [todayOverview, setTodayOverview] = useState<TodayAttendance[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const now = new Date();
      const currentMonth = now.getMonth() + 1;
      const currentYear = now.getFullYear();

      if (isAdmin) {
        const [overviewRes, recordsRes] = await Promise.all([
          attendanceApi.getTodayOverview(),
          attendanceApi.listRecords({
            month: currentMonth,
            year: currentYear,
          }),
        ]);
        setTodayOverview(overviewRes.employees ?? []);
        setRecords(recordsRes.records ?? []);
      } else {
        const [todayRes, recordsRes] = await Promise.all([
          attendanceApi.getToday(),
          attendanceApi.listRecords({
            month: currentMonth,
            year: currentYear,
          }),
        ]);
        setTodayRecord(todayRes.record ?? null);
        setRecords(recordsRes.records ?? []);
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load attendance data. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (error && !isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <div className="flex items-center gap-3">
          <Clock
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            {isAdmin ? "Attendance" : "My Attendance"}
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
      <div className="flex items-center gap-3">
        <Clock
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            {isAdmin ? "Attendance" : "My Attendance"}
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            {isAdmin
              ? "Monitor team attendance and timesheets"
              : "Track your attendance and working hours"}
          </p>
        </div>
      </div>

      {/* Employee View */}
      {!isAdmin && (
        <>
          <ClockCard
            todayRecord={todayRecord}
            isLoading={isLoading}
            onRefresh={fetchData}
          />

          <MonthlySummary records={records} />

          <div>
            <h2 className="text-base font-semibold text-[var(--color-gray-900)] mb-3">
              Attendance History
            </h2>
            <AttendanceHistory records={records} isLoading={isLoading} />
          </div>
        </>
      )}

      {/* Admin View */}
      {isAdmin && (
        <>
          <TodayOverview employees={todayOverview} isLoading={isLoading} />

          <MonthlySummary records={records} />

          <div>
            <h2 className="text-base font-semibold text-[var(--color-gray-900)] mb-3">
              All Records This Month
            </h2>
            <AttendanceHistory records={records} isLoading={isLoading} />
          </div>
        </>
      )}
    </div>
  );
}
