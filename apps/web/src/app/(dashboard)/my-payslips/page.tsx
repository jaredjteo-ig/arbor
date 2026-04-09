"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  Receipt,
  ChevronDown,
  ChevronUp,
  Download,
  RefreshCw,
} from "lucide-react";
import {
  payrollApi,
  type Payslip,
  type PayslipDetail,
} from "@/services/api/payroll";

/* ── Helpers ──────────────────────────────────────────────── */

function formatCurrency(amount: number): string {
  return `$${(amount ?? 0).toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPeriod(start: string, end: string): string {
  if (!start) return "-";
  const s = new Date(start);
  return s.toLocaleDateString("en-SG", { month: "long", year: "numeric" });
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

/* ── Skeletons ────────────────────────────────────────────── */

function PayslipListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-5"
        >
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="h-4 w-36 bg-[var(--color-gray-200)] rounded" />
              <div className="h-3.5 w-24 bg-[var(--color-gray-200)] rounded" />
            </div>
            <div className="h-6 w-24 bg-[var(--color-gray-200)] rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Expandable Payslip Card ──────────────────────────────── */

function PayslipCard({ payslip }: { payslip: Payslip }) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<PayslipDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  async function handleToggle() {
    if (expanded) {
      setExpanded(false);
      return;
    }

    setExpanded(true);

    if (!detail) {
      setLoadingDetail(true);
      try {
        const data = await payrollApi.myPayslipDetail(payslip.payslip_id);
        setDetail(data);
      } catch {
        /* Silently fail — detail just won't render */
      } finally {
        setLoadingDetail(false);
      }
    }
  }

  return (
    <AppCard variant="standard" className="overflow-visible">
      {/* Summary row */}
      <button
        type="button"
        onClick={handleToggle}
        className="w-full text-left flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-4 min-h-[44px]"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-base font-semibold text-[var(--color-gray-900)]">
              {formatPeriod(payslip.period_start, payslip.period_end)}
            </span>
            <StatusBadge status={payslip.status} />
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5 mt-1 text-sm text-[var(--color-gray-500)]">
            <span>Gross: {formatCurrency(payslip.gross_salary)}</span>
            <span>Net: {formatCurrency(payslip.net_salary)}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-lg font-bold text-[var(--color-gray-900)]">
            {formatCurrency(payslip.net_salary)}
          </span>
          {expanded ? (
            <ChevronUp className="h-5 w-5 text-[var(--color-gray-400)]" />
          ) : (
            <ChevronDown className="h-5 w-5 text-[var(--color-gray-400)]" />
          )}
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-[var(--color-gray-200)]">
          {loadingDetail ? (
            <div className="animate-pulse space-y-3">
              {Array.from({ length: 4 }, (_, i) => (
                <div
                  key={i}
                  className="h-4 w-48 bg-[var(--color-gray-200)] rounded"
                />
              ))}
            </div>
          ) : detail?.items && detail.items.length > 0 ? (
            <div className="space-y-5">
              {/* Group by item_type */}
              {[
                {
                  type: "earning",
                  label: "Earnings",
                  color: "text-[var(--color-gray-900)]",
                },
                {
                  type: "deduction",
                  label: "Deductions",
                  color: "text-red-600",
                },
                {
                  type: "employer_contribution",
                  label: "Employer Contributions",
                  color: "text-[var(--color-gray-600)]",
                },
              ].map(({ type, label, color }) => {
                const items = detail.items.filter(
                  (item) => item.item_type === type,
                );
                if (items.length === 0) return null;

                return (
                  <div key={type}>
                    <h4 className="text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wide mb-2">
                      {label}
                    </h4>
                    <div className="space-y-1.5">
                      {items.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between text-sm"
                        >
                          <span className="text-[var(--color-gray-700)]">
                            {item.name}
                            {item.is_cpf_applicable && (
                              <span className="ml-1.5 text-[10px] px-1 py-0.5 rounded bg-[var(--color-gray-100)] text-[var(--color-gray-500)]">
                                CPF
                              </span>
                            )}
                            {item.is_taxable && (
                              <span className="ml-1 text-[10px] px-1 py-0.5 rounded bg-amber-50 text-amber-600">
                                Tax
                              </span>
                            )}
                          </span>
                          <span className={`font-medium ${color}`}>
                            {type === "deduction" ? "-" : ""}
                            {formatCurrency(item.amount)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}

              {/* Statutory section */}
              {(detail.sdl > 0 || detail.fwl > 0 || detail.shg_amount > 0) && (
                <div>
                  <h4 className="text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wide mb-2">
                    Statutory Contributions
                  </h4>
                  <div className="space-y-1.5 text-sm">
                    {detail.employer_cpf > 0 && (
                      <div className="flex justify-between">
                        <span className="text-[var(--color-gray-700)]">
                          Employer CPF
                        </span>
                        <span className="text-[var(--color-gray-600)] font-medium">
                          {formatCurrency(detail.employer_cpf)}
                        </span>
                      </div>
                    )}
                    {detail.employee_cpf > 0 && (
                      <div className="flex justify-between">
                        <span className="text-[var(--color-gray-700)]">
                          Employee CPF
                        </span>
                        <span className="text-red-600 font-medium">
                          -{formatCurrency(detail.employee_cpf)}
                        </span>
                      </div>
                    )}
                    {detail.sdl > 0 && (
                      <div className="flex justify-between">
                        <span className="text-[var(--color-gray-700)]">
                          SDL
                        </span>
                        <span className="text-[var(--color-gray-600)] font-medium">
                          {formatCurrency(detail.sdl)}
                        </span>
                      </div>
                    )}
                    {detail.fwl > 0 && (
                      <div className="flex justify-between">
                        <span className="text-[var(--color-gray-700)]">
                          FWL
                        </span>
                        <span className="text-[var(--color-gray-600)] font-medium">
                          {formatCurrency(detail.fwl)}
                        </span>
                      </div>
                    )}
                    {detail.shg_amount > 0 && (
                      <div className="flex justify-between">
                        <span className="text-[var(--color-gray-700)]">
                          SHG ({detail.shg_fund})
                        </span>
                        <span className="text-[var(--color-gray-600)] font-medium">
                          {formatCurrency(detail.shg_amount)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Net summary */}
              <div className="pt-3 border-t border-[var(--color-gray-200)] flex justify-between">
                <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                  Net Pay
                </span>
                <span className="text-base font-bold text-[var(--color-gray-900)]">
                  {formatCurrency(detail.net_salary)}
                </span>
              </div>

              {/* Download PDF */}
              <div className="pt-2">
                <AppButton
                  variant="outlined"
                  size="sm"
                  onClick={async (e) => {
                    e.stopPropagation();
                    setDownloadingPdf(true);
                    try {
                      await payrollApi.downloadMyPayslipPdf(payslip.payslip_id);
                    } catch {
                      toast.error(
                        "Failed to download payslip. Please try again.",
                      );
                    } finally {
                      setDownloadingPdf(false);
                    }
                  }}
                  disabled={downloadingPdf}
                >
                  <Download className="h-4 w-4 mr-1" />
                  {downloadingPdf ? "Downloading..." : "Download PDF"}
                </AppButton>
              </div>
            </div>
          ) : (
            /* Fallback: show basic summary when no items */
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--color-gray-700)]">
                  Gross Salary
                </span>
                <span className="font-medium text-[var(--color-gray-900)]">
                  {formatCurrency(payslip.gross_salary)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-gray-700)]">
                  Employee CPF
                </span>
                <span className="font-medium text-red-600">
                  -{formatCurrency(payslip.employee_cpf)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-gray-700)]">
                  Employer CPF
                </span>
                <span className="font-medium text-[var(--color-gray-600)]">
                  {formatCurrency(payslip.employer_cpf)}
                </span>
              </div>
              <div className="pt-2 border-t border-[var(--color-gray-200)] flex justify-between">
                <span className="font-semibold text-[var(--color-gray-900)]">
                  Net Pay
                </span>
                <span className="font-bold text-[var(--color-gray-900)]">
                  {formatCurrency(payslip.net_salary)}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </AppCard>
  );
}

/* ── Page ──────────────────────────────────────────────────── */

export default function MyPayslipsPage() {
  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPayslips = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await payrollApi.myPayslips();
      setPayslips(list);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load your payslips. Please try again.";
      setError(message);
      setPayslips([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPayslips();
  }, [fetchPayslips]);

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Receipt
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              My Payslips
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              View your salary history and payslip details
            </p>
          </div>
        </div>
        <AppButton
          variant="text"
          size="sm"
          onClick={fetchPayslips}
          disabled={isLoading}
        >
          <RefreshCw
            className={`h-4 w-4 mr-1 ${isLoading ? "animate-spin" : ""}`}
          />
          Refresh
        </AppButton>
      </div>

      {/* Content */}
      {isLoading ? (
        <PayslipListSkeleton />
      ) : error ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={fetchPayslips}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      ) : payslips.length === 0 ? (
        <EmptyState
          icon={<Receipt className="h-12 w-12" aria-hidden="true" />}
          message="No payslips yet"
          description="Your payslips will appear here after payroll is processed."
        />
      ) : (
        <div className="space-y-3">
          {payslips.map((payslip) => (
            <PayslipCard key={payslip.payslip_id} payslip={payslip} />
          ))}
        </div>
      )}
    </div>
  );
}
