"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  AppCard,
  AppButton,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  Wallet,
  Plus,
  Calendar,
  TrendingUp,
  DollarSign,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { payrollApi, type PayrollRun } from "@/services/api/payroll";

/* ── Helpers ──────────────────────────────────────────────── */

function formatCurrency(amount: number): string {
  return `$${(amount ?? 0).toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-SG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatPeriod(start: string, end: string): string {
  const s = new Date(start);
  return s.toLocaleDateString("en-SG", { month: "short", year: "numeric" });
}

/** Get last day of month in YYYY-MM-DD format. */
function getLastDayOfMonth(year: number, month: number): string {
  const d = new Date(year, month, 0);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Get first day of month in YYYY-MM-DD format. */
function getFirstDayOfMonth(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}-01`;
}

/* ── Status badge ─────────────────────────────────────────── */

const STATUS_STYLES: Record<string, string> = {
  draft:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
  approved: "bg-blue-50 text-blue-700 border-blue-200",
  paid: "bg-emerald-50 text-emerald-700 border-emerald-200",
  cancelled: "bg-red-50 text-red-700 border-red-200",
};

function StatusBadge({ status }: { status: string }) {
  const s = status || "draft";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[s] || STATUS_STYLES.draft}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

/* ── Loading skeleton ─────────────────────────────────────── */

function TableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-5 border-b border-[var(--color-gray-100)] last:border-0"
        >
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-12 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full ml-auto" />
        </div>
      ))}
    </div>
  );
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {Array.from({ length: 3 }, (_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-5"
        >
          <div className="h-3.5 w-28 bg-[var(--color-gray-200)] rounded mb-3" />
          <div className="h-6 w-24 bg-[var(--color-gray-200)] rounded" />
        </div>
      ))}
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────── */

export default function PayrollPage() {
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "hr_manager";

  /* -- Run payroll form state -- */
  const now = new Date();
  const [selectedYear, setSelectedYear] = useState(now.getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1);
  const [payDate, setPayDate] = useState(
    getLastDayOfMonth(now.getFullYear(), now.getMonth() + 1),
  );
  const [isCalculating, setIsCalculating] = useState(false);

  /* -- Past runs state -- */
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await payrollApi.listRuns();
      /* The API may return an array directly or wrapped in { runs: [...] }. */
      const list = Array.isArray(data)
        ? data
        : ((data as unknown as { runs: PayrollRun[] }).runs ?? []);
      setRuns(list);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load payroll runs. Please try again.";
      setError(message);
      setRuns([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  /* -- Derived quick stats -- */
  const paidRuns = runs.filter((r) => r.status === "paid");
  const lastPaid = paidRuns.length > 0 ? paidRuns[0] : null;

  const upcomingDraft = runs.find(
    (r) => r.status === "draft" || r.status === "approved",
  );
  const nextPayDate = upcomingDraft ? upcomingDraft.pay_date : null;

  /* CPF submission is typically due on the 14th of the following month */
  const cpfDueDate = lastPaid
    ? (() => {
        const d = new Date(lastPaid.period_end);
        d.setMonth(d.getMonth() + 1);
        d.setDate(14);
        return d.toISOString().split("T")[0];
      })()
    : null;

  /* -- Calculate payroll handler -- */
  async function handleCalculate() {
    setIsCalculating(true);
    try {
      const periodStart = getFirstDayOfMonth(selectedYear, selectedMonth);
      const periodEnd = getLastDayOfMonth(selectedYear, selectedMonth);
      const result = await payrollApi.calculatePayroll({
        period_start: periodStart,
        period_end: periodEnd,
        pay_date: payDate,
        payroll_type: "monthly",
      });
      toast.success("Payroll calculated successfully");
      // Backend returns { payroll_run: {...}, payslips: [...] }
      const runId = result.id || (result as any).payroll_run?.id;
      router.push(`/payroll/${runId}`);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "detail" in err
            ? String((err as Record<string, unknown>).detail)
            : "Failed to calculate payroll. Please try again.";
      toast.error(message);
    } finally {
      setIsCalculating(false);
    }
  }

  /* -- Month options -- */
  const months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  const yearOptions = Array.from(
    { length: 5 },
    (_, i) => now.getFullYear() - 2 + i,
  );

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Wallet
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Payroll
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Run payroll, review past runs, and manage payments
            </p>
          </div>
        </div>
      </div>

      {/* Run Payroll Action Card */}
      {isAdmin && (
        <AppCard variant="elevated">
          <div className="flex items-start gap-3 mb-4">
            <Plus
              className="h-5 w-5 text-[var(--color-primary)] mt-0.5"
              aria-hidden="true"
            />
            <div>
              <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
                Run Payroll
              </h2>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Calculate payroll for a given month and review before approving
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-3">
            {/* Month selector */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="payroll-month"
                className="text-sm font-medium text-[var(--color-gray-700)]"
              >
                Month
              </label>
              <select
                id="payroll-month"
                value={selectedMonth}
                onChange={(e) => {
                  const m = Number(e.target.value);
                  setSelectedMonth(m);
                  setPayDate(getLastDayOfMonth(selectedYear, m));
                }}
                className="
                  rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
                  bg-[var(--color-surface-input)] text-[var(--foreground)]
                  border-[var(--color-surface-input-border)]
                  transition-colors
                  focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                  focus:border-[var(--color-surface-input-focus)]
                "
              >
                {months.map((m, i) => (
                  <option key={i + 1} value={i + 1}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            {/* Year selector */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="payroll-year"
                className="text-sm font-medium text-[var(--color-gray-700)]"
              >
                Year
              </label>
              <select
                id="payroll-year"
                value={selectedYear}
                onChange={(e) => {
                  const y = Number(e.target.value);
                  setSelectedYear(y);
                  setPayDate(getLastDayOfMonth(y, selectedMonth));
                }}
                className="
                  rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
                  bg-[var(--color-surface-input)] text-[var(--foreground)]
                  border-[var(--color-surface-input-border)]
                  transition-colors
                  focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                  focus:border-[var(--color-surface-input-focus)]
                "
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>

            {/* Pay date */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="pay-date"
                className="text-sm font-medium text-[var(--color-gray-700)]"
              >
                Pay Date
              </label>
              <input
                id="pay-date"
                type="date"
                value={payDate}
                onChange={(e) => setPayDate(e.target.value)}
                className="
                  rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
                  bg-[var(--color-surface-input)] text-[var(--foreground)]
                  border-[var(--color-surface-input-border)]
                  transition-colors
                  focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                  focus:border-[var(--color-surface-input-focus)]
                "
              />
            </div>

            {/* Calculate button */}
            <AppButton
              variant="primary"
              size="md"
              onClick={handleCalculate}
              loading={isCalculating}
            >
              <Calendar className="h-4 w-4 mr-1" />
              Calculate Payroll
            </AppButton>
          </div>
        </AppCard>
      )}

      {/* Quick Stats Cards */}
      {isLoading ? (
        <StatsSkeleton />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Last payroll total */}
          <AppCard variant="flat">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign
                className="h-4 w-4 text-[var(--color-gray-400)]"
                aria-hidden="true"
              />
              <span className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wide">
                Last Payroll
              </span>
            </div>
            <p className="text-xl font-bold text-[var(--color-gray-900)]">
              {lastPaid ? formatCurrency(lastPaid.total_net) : "-"}
            </p>
            {lastPaid && (
              <p className="text-xs text-[var(--color-gray-400)] mt-1">
                {formatPeriod(lastPaid.period_start, lastPaid.period_end)}
              </p>
            )}
          </AppCard>

          {/* Next pay date */}
          <AppCard variant="flat">
            <div className="flex items-center gap-2 mb-2">
              <Calendar
                className="h-4 w-4 text-[var(--color-gray-400)]"
                aria-hidden="true"
              />
              <span className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wide">
                Next Pay Date
              </span>
            </div>
            <p className="text-xl font-bold text-[var(--color-gray-900)]">
              {nextPayDate ? formatDate(nextPayDate) : "-"}
            </p>
            {upcomingDraft && (
              <p className="text-xs text-[var(--color-gray-400)] mt-1">
                <StatusBadge status={upcomingDraft.status} />
              </p>
            )}
          </AppCard>

          {/* CPF due */}
          <AppCard variant="flat">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp
                className="h-4 w-4 text-[var(--color-gray-400)]"
                aria-hidden="true"
              />
              <span className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wide">
                CPF Due
              </span>
            </div>
            <p className="text-xl font-bold text-[var(--color-gray-900)]">
              {cpfDueDate ? formatDate(cpfDueDate) : "-"}
            </p>
            {lastPaid && (
              <p className="text-xs text-[var(--color-gray-400)] mt-1">
                {formatCurrency(
                  lastPaid.total_employer_cpf + lastPaid.total_employee_cpf,
                )}{" "}
                total CPF
              </p>
            )}
          </AppCard>
        </div>
      )}

      {/* Past Runs */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
          Payroll Runs
        </h2>
        <AppButton
          variant="text"
          size="sm"
          onClick={fetchRuns}
          disabled={isLoading}
        >
          <RefreshCw
            className={`h-4 w-4 mr-1 ${isLoading ? "animate-spin" : ""}`}
          />
          Refresh
        </AppButton>
      </div>

      {isLoading ? (
        <AppCard variant="standard">
          <div className="-mx-5 -my-4">
            <TableSkeleton />
          </div>
        </AppCard>
      ) : error ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={fetchRuns}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      ) : runs.length === 0 ? (
        <EmptyState
          icon={<Wallet className="h-12 w-12" aria-hidden="true" />}
          message="No payroll runs yet"
          description="Calculate your first payroll to get started."
        />
      ) : (
        <AppCard variant="standard">
          <div className="overflow-x-auto -mx-5 -my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)]">
                  <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                    Period
                  </th>
                  <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Pay Date
                  </th>
                  <th className="text-right py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Employees
                  </th>
                  <th className="text-right py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Gross Total
                  </th>
                  <th className="text-right py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Net Total
                  </th>
                  <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    onClick={() => router.push(`/payroll/${run.id}`)}
                    className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors cursor-pointer"
                  >
                    <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                      {formatPeriod(run.period_start, run.period_end)}
                    </td>
                    <td className="py-3 px-3 text-[var(--color-gray-600)]">
                      {formatDate(run.pay_date)}
                    </td>
                    <td className="py-3 px-3 text-right text-[var(--color-gray-600)]">
                      {run.employee_count}
                    </td>
                    <td className="py-3 px-3 text-right text-[var(--color-gray-900)] font-medium">
                      {formatCurrency(run.total_gross)}
                    </td>
                    <td className="py-3 px-3 text-right text-[var(--color-gray-900)] font-medium">
                      {formatCurrency(run.total_net)}
                    </td>
                    <td className="py-3 px-5 text-center">
                      <StatusBadge status={run.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AppCard>
      )}
    </div>
  );
}
