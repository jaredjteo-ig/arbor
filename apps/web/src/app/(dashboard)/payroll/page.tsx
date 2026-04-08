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
  Upload,
  GitCompareArrows,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  payrollApi,
  type PayrollRun,
  type ParallelUploadResult,
  type ParallelCompareResult,
} from "@/services/api/payroll";

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

  /* -- Parallel run state -- */
  const [parallelOpen, setParallelOpen] = useState(false);
  const [parallelFile, setParallelFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<ParallelUploadResult | null>(
    null,
  );
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [compareResult, setCompareResult] =
    useState<ParallelCompareResult | null>(null);

  /* -- Past runs state -- */
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await payrollApi.listRuns();
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
      router.push(`/payroll/${result.id}`);
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

  /* -- Parallel run handlers -- */
  async function handleParallelUpload() {
    if (!parallelFile) return;
    setIsUploading(true);
    setCompareResult(null);
    try {
      const result = await payrollApi.uploadParallelRun(parallelFile);
      setUploadResult(result);
      toast.success(
        `Uploaded ${result.row_count} rows from ${result.filename}`,
      );
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to upload CSV.";
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleParallelCompare() {
    if (!uploadResult || selectedRunId === null) return;
    setIsComparing(true);
    try {
      const result = await payrollApi.compareParallelRun(
        uploadResult.parallel_run_id,
        selectedRunId,
      );
      setCompareResult(result);
      const { full_matches, mismatches } = result.summary;
      if (mismatches === 0) {
        toast.success(`All ${full_matches} employees match.`);
      } else {
        toast.error(
          `${mismatches} of ${full_matches + mismatches} employees have differences.`,
        );
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to compare payroll runs.";
      toast.error(message);
    } finally {
      setIsComparing(false);
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
    <AdminGuard>
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
                  Calculate payroll for a given month and review before
                  approving
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

        {/* Parallel Run — Compare with External HRIS */}
        {isAdmin && (
          <AppCard variant="standard">
            <button
              type="button"
              onClick={() => setParallelOpen(!parallelOpen)}
              className="flex items-center gap-2 w-full text-left"
            >
              {parallelOpen ? (
                <ChevronDown className="h-4 w-4 text-[var(--color-gray-400)]" />
              ) : (
                <ChevronRight className="h-4 w-4 text-[var(--color-gray-400)]" />
              )}
              <GitCompareArrows
                className="h-5 w-5 text-[var(--color-primary)]"
                aria-hidden="true"
              />
              <div>
                <span className="text-base font-semibold text-[var(--color-gray-900)]">
                  Parallel Run
                </span>
                <span className="text-sm text-[var(--color-gray-500)] ml-2">
                  Compare with external HRIS
                </span>
              </div>
            </button>

            {parallelOpen && (
              <div className="mt-4 space-y-4">
                {/* Step 1: Upload CSV */}
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-[var(--color-gray-700)]">
                    Step 1: Upload external payslip CSV
                  </h3>
                  <p className="text-xs text-[var(--color-gray-500)]">
                    CSV should contain: Employee Name or ID, Gross Salary, Net
                    Salary, Employee CPF, Employer CPF (and optionally SDL,
                    Period)
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    <input
                      type="file"
                      accept=".csv"
                      onChange={(e) => {
                        setParallelFile(e.target.files?.[0] ?? null);
                        setUploadResult(null);
                        setCompareResult(null);
                      }}
                      className="text-sm text-[var(--color-gray-600)] file:mr-3 file:py-1.5 file:px-3 file:rounded-[8px] file:border file:border-[var(--color-gray-200)] file:bg-[var(--color-surface-card)] file:text-sm file:font-medium file:text-[var(--color-gray-700)] hover:file:bg-[var(--color-gray-50)]"
                    />
                    <AppButton
                      variant="outlined"
                      size="sm"
                      onClick={handleParallelUpload}
                      loading={isUploading}
                      disabled={!parallelFile}
                    >
                      <Upload className="h-4 w-4 mr-1" />
                      Upload
                    </AppButton>
                  </div>
                  {uploadResult && (
                    <p className="text-sm text-emerald-600">
                      Uploaded {uploadResult.row_count} employee rows from{" "}
                      <span className="font-medium">
                        {uploadResult.filename}
                      </span>
                    </p>
                  )}
                </div>

                {/* Step 2: Select Arbor run and compare */}
                {uploadResult && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-[var(--color-gray-700)]">
                      Step 2: Select an Arbor payroll run to compare against
                    </h3>
                    <div className="flex flex-wrap items-center gap-3">
                      <select
                        value={selectedRunId ?? ""}
                        onChange={(e) =>
                          setSelectedRunId(
                            e.target.value ? Number(e.target.value) : null,
                          )
                        }
                        className="rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                      >
                        <option value="">Choose a payroll run...</option>
                        {runs.map((r) => (
                          <option key={r.id} value={r.id}>
                            {formatPeriod(r.period_start, r.period_end)} -{" "}
                            {r.status} ({r.employee_count} employees)
                          </option>
                        ))}
                      </select>
                      <AppButton
                        variant="primary"
                        size="sm"
                        onClick={handleParallelCompare}
                        loading={isComparing}
                        disabled={selectedRunId === null}
                      >
                        <GitCompareArrows className="h-4 w-4 mr-1" />
                        Compare
                      </AppButton>
                    </div>
                  </div>
                )}

                {/* Step 3: Results */}
                {compareResult && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-medium text-[var(--color-gray-700)]">
                      Comparison Results
                    </h3>

                    {/* Summary stats */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="rounded-[8px] border border-emerald-200 bg-emerald-50 p-3 text-center">
                        <p className="text-xs text-emerald-600 font-medium">
                          Matches
                        </p>
                        <p className="text-lg font-bold text-emerald-700">
                          {compareResult.summary.full_matches}
                        </p>
                      </div>
                      <div className="rounded-[8px] border border-red-200 bg-red-50 p-3 text-center">
                        <p className="text-xs text-red-600 font-medium">
                          Mismatches
                        </p>
                        <p className="text-lg font-bold text-red-700">
                          {compareResult.summary.mismatches}
                        </p>
                      </div>
                      <div className="rounded-[8px] border border-amber-200 bg-amber-50 p-3 text-center">
                        <p className="text-xs text-amber-600 font-medium">
                          Unmatched (ext)
                        </p>
                        <p className="text-lg font-bold text-amber-700">
                          {compareResult.summary.unmatched_external}
                        </p>
                      </div>
                      <div className="rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-gray-50)] p-3 text-center">
                        <p className="text-xs text-[var(--color-gray-500)] font-medium">
                          Largest diff
                        </p>
                        <p className="text-lg font-bold text-[var(--color-gray-900)]">
                          ${compareResult.summary.largest_deviation.toFixed(2)}
                        </p>
                        {compareResult.summary.largest_deviation_employee && (
                          <p className="text-xs text-[var(--color-gray-400)] truncate">
                            {compareResult.summary.largest_deviation_employee} (
                            {compareResult.summary.largest_deviation_field.replace(
                              /_/g,
                              " ",
                            )}
                            )
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Per-employee comparison table */}
                    {compareResult.comparisons.length > 0 && (
                      <div className="overflow-x-auto rounded-[8px] border border-[var(--color-gray-200)]">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="bg-[var(--color-gray-50)] border-b border-[var(--color-gray-200)]">
                              <th className="text-left py-2.5 px-3 font-medium text-[var(--color-gray-500)]">
                                Employee
                              </th>
                              <th className="text-right py-2.5 px-3 font-medium text-[var(--color-gray-500)]">
                                Gross
                              </th>
                              <th className="text-right py-2.5 px-3 font-medium text-[var(--color-gray-500)]">
                                Net
                              </th>
                              <th className="text-right py-2.5 px-3 font-medium text-[var(--color-gray-500)]">
                                Emp CPF
                              </th>
                              <th className="text-right py-2.5 px-3 font-medium text-[var(--color-gray-500)]">
                                Er CPF
                              </th>
                              <th className="text-center py-2.5 px-3 font-medium text-[var(--color-gray-500)]">
                                Status
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {compareResult.comparisons.map((comp, idx) => {
                              const gross = comp.fields.find(
                                (f) => f.field === "gross_salary",
                              );
                              const net = comp.fields.find(
                                (f) => f.field === "net_salary",
                              );
                              const empCpf = comp.fields.find(
                                (f) => f.field === "employee_cpf",
                              );
                              const erCpf = comp.fields.find(
                                (f) => f.field === "employer_cpf",
                              );
                              return (
                                <tr
                                  key={idx}
                                  className="border-b border-[var(--color-gray-100)] last:border-0"
                                >
                                  <td className="py-2 px-3 font-medium text-[var(--color-gray-900)]">
                                    {comp.employee_name || comp.employee_id}
                                  </td>
                                  {[gross, net, empCpf, erCpf].map((f, fi) => (
                                    <td
                                      key={fi}
                                      className={`py-2 px-3 text-right ${f && !f.match ? "text-red-600 font-medium" : "text-[var(--color-gray-600)]"}`}
                                    >
                                      {f ? (
                                        f.match ? (
                                          <span>${f.external.toFixed(2)}</span>
                                        ) : (
                                          <span
                                            title={`External: $${f.external.toFixed(2)} | Arbor: $${f.arbor.toFixed(2)}`}
                                          >
                                            {f.difference > 0 ? "+" : ""}$
                                            {f.difference.toFixed(2)}
                                          </span>
                                        )
                                      ) : (
                                        "-"
                                      )}
                                    </td>
                                  ))}
                                  <td className="py-2 px-3 text-center">
                                    {comp.overall_match ? (
                                      <CheckCircle2 className="h-4 w-4 text-emerald-500 inline" />
                                    ) : (
                                      <XCircle className="h-4 w-4 text-red-500 inline" />
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Unmatched employees */}
                    {(compareResult.unmatched_external.length > 0 ||
                      compareResult.unmatched_arbor.length > 0) && (
                      <div className="space-y-2">
                        {compareResult.unmatched_external.length > 0 && (
                          <div className="text-sm">
                            <div className="flex items-center gap-1 text-amber-600 font-medium mb-1">
                              <AlertTriangle className="h-3.5 w-3.5" />
                              Employees in external CSV but not in Arbor:
                            </div>
                            <ul className="list-disc list-inside text-[var(--color-gray-600)] text-xs ml-1">
                              {compareResult.unmatched_external.map((u, i) => (
                                <li key={i}>
                                  {u.employee_name || u.employee_id}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {compareResult.unmatched_arbor.length > 0 && (
                          <div className="text-sm">
                            <div className="flex items-center gap-1 text-[var(--color-gray-500)] font-medium mb-1">
                              <AlertTriangle className="h-3.5 w-3.5" />
                              Employees in Arbor but not in external CSV:
                            </div>
                            <ul className="list-disc list-inside text-[var(--color-gray-600)] text-xs ml-1">
                              {compareResult.unmatched_arbor.map((u, i) => (
                                <li key={i}>
                                  {u.employee_name ||
                                    u.employee_id_internal ||
                                    "Unknown"}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
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
    </AdminGuard>
  );
}
