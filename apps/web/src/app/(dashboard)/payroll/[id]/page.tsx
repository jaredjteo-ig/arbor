"use client";

import { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import {
  AppCard,
  AppButton,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  ArrowLeft,
  DollarSign,
  Users,
  Shield,
  CheckCircle2,
  XCircle,
  CreditCard,
  ChevronDown,
  ChevronUp,
  Download,
  FileText,
  ExternalLink,
  AlertCircle,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  payrollApi,
  type PayrollRunDetail,
  type PayslipSummary,
  type PayslipDetail,
} from "@/services/api/payroll";
import { XeroExportModal } from "@/components/payroll/XeroExportModal";
import { useXeroExportStatus } from "@/hooks/api";

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
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[s] || STATUS_STYLES.draft}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

/* ── Skeletons ────────────────────────────────────────────── */

function SummaryCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
      {Array.from({ length: 7 }, (_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-4"
        >
          <div className="h-3 w-16 bg-[var(--color-gray-200)] rounded mb-2" />
          <div className="h-5 w-20 bg-[var(--color-gray-200)] rounded" />
        </div>
      ))}
    </div>
  );
}

function PayslipTableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 5 }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-5 border-b border-[var(--color-gray-100)] last:border-0"
        >
          <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* ── Expandable Payslip Row ───────────────────────────────── */

function PayslipRow({
  payslip,
  runId,
}: {
  payslip: PayslipSummary;
  runId: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<PayslipDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  async function handleToggle() {
    if (expanded) {
      setExpanded(false);
      return;
    }

    setExpanded(true);

    if (!detail) {
      setLoadingDetail(true);
      try {
        const data = await payrollApi.getPayslipDetail(
          runId,
          payslip.payslip_id,
        );
        setDetail(data);
      } catch {
        /* Silently fail — the row just shows no items */
      } finally {
        setLoadingDetail(false);
      }
    }
  }

  const deductions = payslip.employee_cpf;
  const displayName = payslip.employee_name || payslip.name;

  return (
    <>
      <tr
        onClick={handleToggle}
        className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors cursor-pointer"
      >
        <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronUp className="h-4 w-4 text-[var(--color-gray-400)] shrink-0" />
            ) : (
              <ChevronDown className="h-4 w-4 text-[var(--color-gray-400)] shrink-0" />
            )}
            {displayName}
          </div>
        </td>
        <td className="py-3 px-3 text-right text-[var(--color-gray-600)]">
          {formatCurrency(payslip.basic_salary)}
        </td>
        <td className="py-3 px-3 text-right text-[var(--color-gray-900)] font-medium">
          {formatCurrency(payslip.gross_salary)}
        </td>
        <td className="py-3 px-3 text-right text-[var(--color-gray-600)]">
          {formatCurrency(deductions)}
        </td>
        <td className="py-3 px-3 text-right text-[var(--color-gray-600)]">
          {formatCurrency(payslip.employer_cpf)}
        </td>
        <td className="py-3 px-5 text-right text-[var(--color-gray-900)] font-semibold">
          {formatCurrency(payslip.net_salary)}
        </td>
      </tr>

      {/* Expanded detail */}
      {expanded && (
        <tr>
          <td colSpan={6} className="bg-[var(--color-gray-50)] px-5 py-4">
            {loadingDetail ? (
              <div className="animate-pulse space-y-2">
                {Array.from({ length: 3 }, (_, i) => (
                  <div
                    key={i}
                    className="h-4 w-48 bg-[var(--color-gray-200)] rounded"
                  />
                ))}
              </div>
            ) : detail?.items && detail.items.length > 0 ? (
              <div className="space-y-4">
                {/* Group by item_type */}
                {["earning", "deduction", "employer_contribution"].map(
                  (type) => {
                    const items = detail.items.filter(
                      (item) => item.item_type === type,
                    );
                    if (items.length === 0) return null;

                    const typeLabels: Record<string, string> = {
                      earning: "Earnings",
                      deduction: "Deductions",
                      employer_contribution: "Employer Contributions",
                    };

                    return (
                      <div key={type}>
                        <h4 className="text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wide mb-2">
                          {typeLabels[type] || type}
                        </h4>
                        <div className="space-y-1">
                          {items.map((item) => (
                            <div
                              key={item.id}
                              className="flex items-center justify-between text-sm"
                            >
                              <span className="text-[var(--color-gray-700)]">
                                {item.name}
                                {item.is_cpf_applicable && (
                                  <span className="ml-1.5 text-[10px] text-[var(--color-gray-400)]">
                                    CPF
                                  </span>
                                )}
                              </span>
                              <span
                                className={
                                  type === "deduction"
                                    ? "text-red-600 font-medium"
                                    : "text-[var(--color-gray-900)] font-medium"
                                }
                              >
                                {type === "deduction" ? "-" : ""}
                                {formatCurrency(item.amount)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  },
                )}

                {/* Statutory detail */}
                {(detail.sdl > 0 ||
                  detail.fwl > 0 ||
                  detail.shg_amount > 0) && (
                  <div>
                    <h4 className="text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wide mb-2">
                      Statutory Contributions
                    </h4>
                    <div className="space-y-1 text-sm">
                      {detail.sdl > 0 && (
                        <div className="flex justify-between">
                          <span className="text-[var(--color-gray-700)]">
                            SDL
                          </span>
                          <span className="text-[var(--color-gray-900)] font-medium">
                            {formatCurrency(detail.sdl)}
                          </span>
                        </div>
                      )}
                      {detail.fwl > 0 && (
                        <div className="flex justify-between">
                          <span className="text-[var(--color-gray-700)]">
                            FWL
                          </span>
                          <span className="text-[var(--color-gray-900)] font-medium">
                            {formatCurrency(detail.fwl)}
                          </span>
                        </div>
                      )}
                      {detail.shg_amount > 0 && (
                        <div className="flex justify-between">
                          <span className="text-[var(--color-gray-700)]">
                            SHG ({detail.shg_fund})
                          </span>
                          <span className="text-[var(--color-gray-900)] font-medium">
                            {formatCurrency(detail.shg_amount)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-[var(--color-gray-500)]">
                No payslip items available.
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

/* ── Page ──────────────────────────────────────────────────── */

interface PayrollRunDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function PayrollRunDetailPage({
  params,
}: PayrollRunDetailPageProps) {
  const { id } = use(params);
  const runId = Number(id);
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "hr_manager";

  const [run, setRun] = useState<PayrollRunDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [xeroOpen, setXeroOpen] = useState<boolean>(false);

  const fetchRun = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await payrollApi.getRun(runId);
      setRun(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load payroll run details.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchRun();
  }, [fetchRun]);

  /* -- Action handlers -- */

  async function handleApprove() {
    setActionLoading("approve");
    try {
      await payrollApi.approveRun(runId);
      toast.success("Payroll run approved");
      fetchRun();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to approve payroll run.";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleMarkPaid() {
    setActionLoading("paid");
    try {
      await payrollApi.markPaid(runId);
      toast.success("Payroll run marked as paid");
      fetchRun();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to mark as paid.";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleCancel() {
    setActionLoading("cancel");
    try {
      await payrollApi.cancelRun(runId);
      toast.success("Payroll run cancelled");
      fetchRun();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to cancel payroll run.";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleVoidXero() {
    if (!run?.xero_journal_id) return;
    const confirmMsg =
      `Void the Xero journal ${run.xero_journal_id}? It stays in your` +
      ` Xero with status VOIDED on the original date — your accountant` +
      ` can still see it for audit. The run will be marked as not-yet-` +
      `exported here so you can re-export if needed.`;
    if (!window.confirm(confirmMsg)) return;
    setActionLoading("void-xero");
    try {
      const { xeroPayrollApi } = await import("@/services/api/payroll");
      await xeroPayrollApi.voidExport(runId);
      toast.success("Xero journal voided.");
      fetchRun();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to void Xero journal.";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  async function downloadFile(type: "cpf" | "giro") {
    setActionLoading(type);
    try {
      const endpoint =
        type === "cpf"
          ? `/payroll/runs/${runId}/cpf-file`
          : `/payroll/runs/${runId}/bank-file`;
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${endpoint}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
            "Content-Type": "application/json",
          },
        },
      );
      if (!res.ok) throw new Error("Failed to generate file");
      const text = await res.text();
      const blob = new Blob([text], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download =
        type === "cpf"
          ? `cpf-esubmit-${run?.period_start || "run"}.csv`
          : `bank-giro-${run?.period_start || "run"}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(
        `${type === "cpf" ? "CPF e-Submit" : "Bank GIRO"} file downloaded`,
      );
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to download file.";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  /* -- Render -- */

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-8">
      {/* Back link */}
      <Link
        href="/payroll"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-primary)] hover:text-[var(--color-primary-dark)] transition-colors"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to Payroll
      </Link>

      {isLoading ? (
        <>
          {/* Header skeleton */}
          <div className="animate-pulse">
            <div className="h-7 w-64 bg-[var(--color-gray-200)] rounded mb-2" />
            <div className="h-4 w-40 bg-[var(--color-gray-200)] rounded" />
          </div>
          <SummaryCardsSkeleton />
          <AppCard variant="standard">
            <div className="-mx-5 -my-4">
              <PayslipTableSkeleton />
            </div>
          </AppCard>
        </>
      ) : error ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={fetchRun}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      ) : run ? (
        <>
          {/* Header */}
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                  {formatPeriod(run.period_start, run.period_end)} Payroll
                </h1>
                <StatusBadge status={run.status} />
              </div>
              <p className="text-sm text-[var(--color-gray-500)] mt-1">
                Pay date: {formatDate(run.pay_date)} &middot;{" "}
                {run.employee_count} employee
                {run.employee_count !== 1 ? "s" : ""}
              </p>
            </div>
          </div>

          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {[
              {
                label: "Gross",
                value: run.total_gross,
                icon: DollarSign,
              },
              { label: "Net", value: run.total_net, icon: CreditCard },
              {
                label: "ER CPF",
                value: run.total_employer_cpf,
                icon: Shield,
              },
              {
                label: "EE CPF",
                value: run.total_employee_cpf,
                icon: Shield,
              },
              { label: "SDL", value: run.total_sdl, icon: Shield },
              { label: "FWL", value: run.total_fwl, icon: Shield },
              { label: "SHG", value: run.total_shg, icon: Shield },
            ].map((card) => (
              <div
                key={card.label}
                className="rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-4"
              >
                <div className="flex items-center gap-1.5 mb-1.5">
                  <card.icon
                    className="h-3.5 w-3.5 text-[var(--color-gray-400)]"
                    aria-hidden="true"
                  />
                  <span className="text-[10px] font-medium text-[var(--color-gray-500)] uppercase tracking-wide">
                    {card.label}
                  </span>
                </div>
                <p className="text-sm font-bold text-[var(--color-gray-900)]">
                  {formatCurrency(card.value)}
                </p>
              </div>
            ))}
          </div>

          {/* Actions bar */}
          {isAdmin && run.status !== "paid" && run.status !== "cancelled" && (
            <div className="flex flex-wrap gap-3">
              {run.status === "draft" && (
                <AppButton
                  variant="primary"
                  size="md"
                  onClick={handleApprove}
                  loading={actionLoading === "approve"}
                  disabled={actionLoading !== null}
                >
                  <CheckCircle2 className="h-4 w-4 mr-1" />
                  Approve
                </AppButton>
              )}
              {run.status === "approved" && (
                <AppButton
                  variant="primary"
                  size="md"
                  onClick={handleMarkPaid}
                  loading={actionLoading === "paid"}
                  disabled={actionLoading !== null}
                >
                  <CreditCard className="h-4 w-4 mr-1" />
                  Mark as Paid
                </AppButton>
              )}
              <AppButton
                variant="danger"
                size="md"
                onClick={handleCancel}
                loading={actionLoading === "cancel"}
                disabled={actionLoading !== null}
              >
                <XCircle className="h-4 w-4 mr-1" />
                Cancel Run
              </AppButton>
            </div>
          )}

          {/* File downloads + accounting export */}
          {run.status !== "cancelled" && (
            <div className="flex flex-wrap gap-3">
              <AppButton
                variant="outlined"
                size="sm"
                onClick={() => downloadFile("cpf")}
                loading={actionLoading === "cpf"}
                disabled={actionLoading !== null}
              >
                <Download className="h-4 w-4 mr-1.5" />
                CPF e-Submit File
              </AppButton>
              <AppButton
                variant="outlined"
                size="sm"
                onClick={() => downloadFile("giro")}
                loading={actionLoading === "giro"}
                disabled={actionLoading !== null}
              >
                <FileText className="h-4 w-4 mr-1.5" />
                Bank GIRO File
              </AppButton>
              {/* Xero export — only available once the run is approved or paid;
                  draft and cancelled runs hide the button entirely. */}
              {isAdmin &&
                (run.status === "approved" || run.status === "paid") && (
                  <AppButton
                    variant="outlined"
                    size="sm"
                    onClick={() => setXeroOpen(true)}
                  >
                    <ExternalLink className="h-4 w-4 mr-1.5" />
                    {run.xero_journal_id
                      ? "Re-export to Xero"
                      : "Export to Xero"}
                  </AppButton>
                )}
              {/* Void — only when there's a posted journal to void. */}
              {isAdmin && run.xero_journal_id && (
                <AppButton
                  variant="outlined"
                  size="sm"
                  onClick={handleVoidXero}
                  loading={actionLoading === "void-xero"}
                  disabled={actionLoading !== null}
                >
                  <XCircle className="h-4 w-4 mr-1.5" />
                  Void Xero export
                </AppButton>
              )}
            </div>
          )}

          {/* Xero export status badge — current journal */}
          <XeroStatusBadge runId={runId} run={run} />
          {run.xero_journal_id && (
            <div className="inline-flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Exported to Xero · journal{" "}
              <span className="font-mono">{run.xero_journal_id}</span>
              {run.xero_exported_at
                ? ` · ${formatDate(run.xero_exported_at)}`
                : ""}
            </div>
          )}

          {/* Conditional render so closing unmounts the modal and resets
              its transient state (overrides, bonus, force, result). */}
          {xeroOpen && (
            <XeroExportModal
              isOpen
              onClose={() => setXeroOpen(false)}
              runId={runId}
              existingJournalId={run.xero_journal_id || undefined}
              onExported={fetchRun}
            />
          )}

          {/* Payslip table */}
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)] mb-3">
              Payslips
            </h2>

            {run.payslips && run.payslips.length > 0 ? (
              <AppCard variant="standard">
                <div className="overflow-x-auto -mx-5 -my-4">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[var(--color-gray-200)]">
                        <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                          Employee
                        </th>
                        <th className="text-right py-3 px-3 font-medium text-[var(--color-gray-500)]">
                          Basic
                        </th>
                        <th className="text-right py-3 px-3 font-medium text-[var(--color-gray-500)]">
                          Gross
                        </th>
                        <th className="text-right py-3 px-3 font-medium text-[var(--color-gray-500)]">
                          EE CPF
                        </th>
                        <th className="text-right py-3 px-3 font-medium text-[var(--color-gray-500)]">
                          ER CPF
                        </th>
                        <th className="text-right py-3 px-5 font-medium text-[var(--color-gray-500)]">
                          Net
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {run.payslips.map((payslip, idx) => (
                        <PayslipRow
                          key={payslip.payslip_id || idx}
                          payslip={payslip}
                          runId={runId}
                        />
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t-2 border-[var(--color-gray-200)] bg-[var(--color-gray-50)]">
                        <td className="py-3 px-5 font-semibold text-[var(--color-gray-900)]">
                          Total
                        </td>
                        <td className="py-3 px-3 text-right font-semibold text-[var(--color-gray-900)]">
                          -
                        </td>
                        <td className="py-3 px-3 text-right font-semibold text-[var(--color-gray-900)]">
                          {formatCurrency(run.total_gross)}
                        </td>
                        <td className="py-3 px-3 text-right font-semibold text-[var(--color-gray-900)]">
                          {formatCurrency(run.total_employee_cpf)}
                        </td>
                        <td className="py-3 px-3 text-right font-semibold text-[var(--color-gray-900)]">
                          {formatCurrency(run.total_employer_cpf)}
                        </td>
                        <td className="py-3 px-5 text-right font-bold text-[var(--color-gray-900)]">
                          {formatCurrency(run.total_net)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </AppCard>
            ) : (
              <EmptyState
                icon={<Users className="h-12 w-12" aria-hidden="true" />}
                message="No payslips"
                description="This payroll run has no payslips."
              />
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}

/* ── Xero status badge ─────────────────────────────────────── */

function XeroStatusBadge({
  runId,
  run,
}: {
  runId: number;
  run: PayrollRunDetail;
}) {
  const status = useXeroExportStatus(runId, true);
  const last = status.data?.last_attempt;
  // No attempts ever → no badge.
  if (!last) return null;
  // The "current journal" badge below the button already covers
  // POSTED+xero_journal_id; only render here for the failure / void
  // states the simple boolean badge can't represent.
  if (last.status === "POSTED" && run.xero_journal_id) return null;

  if (last.status === "FAILED") {
    return (
      <div className="inline-flex items-start gap-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 px-3 py-2 rounded-md max-w-2xl">
        <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
        <div>
          <p className="font-semibold">Last Xero export attempt failed</p>
          <p className="text-amber-700">
            {last.error_message || "Unknown error"} — review and retry.
          </p>
        </div>
      </div>
    );
  }
  if (last.status === "VOIDED") {
    return (
      <div className="inline-flex items-center gap-2 text-xs text-[var(--color-gray-700)] bg-[var(--color-gray-100)] border border-[var(--color-gray-200)] px-3 py-1.5 rounded-full">
        <XCircle className="h-3.5 w-3.5" />
        Last Xero journal voided
        {last.posted_at ? ` · ${formatDate(last.posted_at)}` : ""}
      </div>
    );
  }
  return null;
}
