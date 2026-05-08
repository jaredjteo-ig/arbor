"use client";

/**
 * Modal that handles the Xero payroll-export flow:
 *
 * 1. Loads the company's Xero chart of accounts + saved/auto-matched mapping.
 * 2. Lets the user confirm/edit the six bucket → account-code mappings.
 * 3. Saves the mapping (PUT /payroll/xero/account-mapping).
 * 4. Posts the journal (POST /payroll/runs/{id}/export-xero) and shows a
 *    line-by-line preview on success.
 *
 * Opens from XeroExportButton on the payroll-run detail page. Re-opening
 * after a successful export shows the saved mapping pre-filled and a
 * "force re-export" toggle.
 */

import { useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  Loader2,
  Sparkles,
  X,
} from "lucide-react";
import { toast, AppButton } from "@/components/design-system";
import {
  useExportRunToXero,
  useSaveXeroMapping,
  useXeroChartOfAccounts,
  useXeroMapping,
  useXeroPayrollStatus,
} from "@/hooks/api";
import type {
  XeroAccount,
  XeroAccountMapping,
  XeroExportLine,
} from "@/services/api/payroll";

type BucketKey = keyof XeroAccountMapping;

const BUCKETS: ReadonlyArray<{
  key: BucketKey;
  label: string;
  hint: string;
  side: "debit" | "credit";
}> = [
  {
    key: "salary_expense_code",
    label: "Salary Expense",
    hint: "Debit account for basic wages.",
    side: "debit",
  },
  {
    key: "bonus_expense_code",
    label: "Bonus Expense",
    hint: "Debit account for bonuses paid this run.",
    side: "debit",
  },
  {
    key: "employer_cpf_expense_code",
    label: "Employer CPF Expense",
    hint: "Debit account for the employer share of CPF.",
    side: "debit",
  },
  {
    key: "sdl_expense_code",
    label: "SDL + FWL Expense",
    hint: "Debit account for SDL (and FWL if applicable).",
    side: "debit",
  },
  {
    key: "cpf_payable_code",
    label: "CPF & Statutory Payable",
    hint: "Liability — total owed to CPF Board (employer + employee CPF, SDL, FWL, SHG).",
    side: "credit",
  },
  {
    key: "net_pay_payable_code",
    label: "Net Pay Payable",
    hint: "Liability — net pay owed to employees.",
    side: "credit",
  },
];

const EMPTY_MAPPING: XeroAccountMapping = {
  salary_expense_code: "",
  bonus_expense_code: "",
  employer_cpf_expense_code: "",
  sdl_expense_code: "",
  cpf_payable_code: "",
  net_pay_payable_code: "",
};

interface XeroExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  runId: number;
  /** Pre-existing journal id, if this run was already exported. */
  existingJournalId?: string;
  /** Called after a successful export so the parent can refresh. */
  onExported?: () => void;
}

export function XeroExportModal({
  isOpen,
  onClose,
  runId,
  existingJournalId,
  onExported,
}: XeroExportModalProps) {
  const status = useXeroPayrollStatus();
  const chart = useXeroChartOfAccounts(isOpen);
  const mapping = useXeroMapping(isOpen);
  const saveMapping = useSaveXeroMapping();
  const exportRun = useExportRunToXero();

  // Pure-derived draft: server-loaded mapping + per-field overrides the
  // user has typed. Avoids mirroring server state into local state via
  // an effect (eslint-rule react-hooks/set-state-in-effect). The parent
  // mounts the modal conditionally (`{isOpen && ...}`) so reopening
  // starts with a fresh component and these states reset to defaults.
  const [overrides, setOverrides] = useState<Partial<XeroAccountMapping>>({});
  const [bonusTotal, setBonusTotal] = useState<string>("0");
  const [forceReexport, setForceReexport] = useState<boolean>(false);
  const [exportResult, setExportResult] = useState<{
    journalId: string;
    lines: XeroExportLine[];
    narration: string;
    date: string;
  } | null>(null);

  const draft: XeroAccountMapping = useMemo(
    () => ({
      ...EMPTY_MAPPING,
      ...(mapping.data?.mapping ?? {}),
      ...overrides,
    }),
    [mapping.data?.mapping, overrides],
  );

  const accounts: XeroAccount[] = chart.data?.accounts ?? [];

  const allBucketsSet = useMemo(
    () => BUCKETS.every((b) => draft[b.key].trim().length > 0),
    [draft],
  );

  const mappingChanged = useMemo(() => {
    if (!mapping.data) return Object.keys(overrides).length > 0;
    return BUCKETS.some((b) => mapping.data!.mapping[b.key] !== draft[b.key]);
  }, [mapping.data, draft, overrides]);

  if (!isOpen) return null;

  const isConnected = status.data?.connected ?? false;
  const fetchingPrereqs = chart.isLoading || mapping.isLoading;
  const blocked = !isConnected;

  async function handleSaveMapping() {
    try {
      await saveMapping.mutateAsync(draft);
      toast.success("Xero account mapping saved");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save mapping.";
      toast.error(message);
    }
  }

  async function handleExport() {
    // Save mapping first if it changed — the export endpoint only reads
    // the persisted row, so we must persist before posting the journal.
    if (mappingChanged) {
      try {
        await saveMapping.mutateAsync(draft);
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to save mapping.";
        toast.error(message);
        return;
      }
    }

    const parsedBonus = Number.parseFloat(bonusTotal || "0") || 0;
    try {
      const result = await exportRun.mutateAsync({
        runId,
        body: {
          bonus_total: parsedBonus,
          force: existingJournalId ? forceReexport : false,
        },
      });
      setExportResult({
        journalId: result.journal_id,
        lines: result.lines_preview,
        narration: result.narration,
        date: result.date,
      });
      toast.success("Posted to Xero");
      onExported?.();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to export to Xero.";
      toast.error(message);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-2xl mx-4 bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-full hover:bg-gray-100 transition-colors z-10"
          aria-label="Close"
        >
          <X className="w-5 h-5 text-gray-400" />
        </button>

        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0">
              <ExternalLink className="w-5 h-5 text-blue-600" />
            </div>
            <div className="min-w-0">
              <h2 className="text-lg font-bold text-gray-900">
                Export payroll to Xero
              </h2>
              <p className="text-sm text-gray-500">
                Posts a balanced ManualJournal in your Xero organisation.
              </p>
            </div>
          </div>
        </div>

        {/* Body — scrollable */}
        <div className="overflow-y-auto px-6 py-5 space-y-5">
          {!isConnected && (
            <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900">
              Xero is not connected. Connect it in{" "}
              <a
                href="/settings/integrations"
                className="font-semibold underline hover:no-underline"
              >
                Settings → Integrations
              </a>{" "}
              before exporting.
            </div>
          )}

          {existingJournalId && !exportResult && (
            <div className="rounded-xl bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-900">
              <p className="font-semibold mb-1">
                This run was already exported.
              </p>
              <p>
                Existing Xero journal ID:{" "}
                <span className="font-mono">{existingJournalId}</span>. Tick
                &ldquo;force re-export&rdquo; below to overwrite.
              </p>
            </div>
          )}

          {fetchingPrereqs && isConnected && (
            <div className="flex items-center gap-2 text-sm text-gray-500 py-4">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading Xero chart of accounts…
            </div>
          )}

          {!fetchingPrereqs &&
            isConnected &&
            mapping.data?.source === "auto_match" && (
              <div className="rounded-xl bg-violet-50 border border-violet-200 px-4 py-3 text-sm text-violet-900 flex items-start gap-2">
                <Sparkles className="w-4 h-4 mt-0.5 shrink-0" />
                <div>
                  <p className="font-semibold mb-1">Suggestions ready.</p>
                  <p>
                    We auto-matched your Xero chart to the six payroll buckets.
                    Confirm or change them below — your choice is saved for
                    future exports.
                  </p>
                </div>
              </div>
            )}

          {/* Mapping form */}
          {isConnected && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-900">
                Account mapping
              </h3>
              <div className="grid grid-cols-1 gap-3">
                {BUCKETS.map((bucket) => (
                  <BucketRow
                    key={bucket.key}
                    bucket={bucket}
                    accounts={accounts}
                    value={draft[bucket.key]}
                    disabled={blocked || fetchingPrereqs}
                    onChange={(next) =>
                      setOverrides((prev) => ({ ...prev, [bucket.key]: next }))
                    }
                  />
                ))}
              </div>
            </div>
          )}

          {/* Export options */}
          {isConnected && (
            <div className="space-y-3 pt-2 border-t border-gray-100">
              <h3 className="text-sm font-semibold text-gray-900">
                Export options
              </h3>
              <div>
                <label
                  htmlFor="bonus-total"
                  className="block text-sm font-medium text-gray-700 mb-1.5"
                >
                  Bonus portion of gross (optional)
                </label>
                <input
                  id="bonus-total"
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="0.01"
                  value={bonusTotal}
                  onChange={(e) => setBonusTotal(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 text-sm"
                  placeholder="0.00"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Splits the gross debit into Salary Expense and Bonus Expense.
                  Leave at 0 to put the whole gross under Salary.
                </p>
              </div>

              {existingJournalId && (
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={forceReexport}
                    onChange={(e) => setForceReexport(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  Force re-export — post a new journal even though one already
                  exists.
                </label>
              )}
            </div>
          )}

          {exportResult && (
            <ExportResult
              journalId={exportResult.journalId}
              lines={exportResult.lines}
              narration={exportResult.narration}
              date={exportResult.date}
            />
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between gap-3 bg-gray-50">
          <div className="text-xs text-gray-500">
            {mappingChanged && !exportResult ? (
              <span>Mapping has unsaved changes — saved on export.</span>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            {!exportResult ? (
              <>
                <AppButton
                  variant="text"
                  onClick={handleSaveMapping}
                  disabled={
                    !isConnected || !mappingChanged || saveMapping.isPending
                  }
                >
                  Save mapping only
                </AppButton>
                <AppButton
                  variant="primary"
                  onClick={handleExport}
                  disabled={
                    !isConnected ||
                    fetchingPrereqs ||
                    !allBucketsSet ||
                    exportRun.isPending ||
                    saveMapping.isPending ||
                    (Boolean(existingJournalId) && !forceReexport)
                  }
                >
                  {exportRun.isPending ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Posting…
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      Post to Xero
                      <ArrowRight className="w-4 h-4" />
                    </span>
                  )}
                </AppButton>
              </>
            ) : (
              <AppButton variant="primary" onClick={onClose}>
                Done
              </AppButton>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface BucketRowProps {
  bucket: {
    key: BucketKey;
    label: string;
    hint: string;
    side: "debit" | "credit";
  };
  accounts: XeroAccount[];
  value: string;
  disabled: boolean;
  onChange: (next: string) => void;
}

function BucketRow({
  bucket,
  accounts,
  value,
  disabled,
  onChange,
}: BucketRowProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-2 items-start">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900">
            {bucket.label}
          </span>
          <span
            className={`text-[10px] font-medium uppercase tracking-wider px-1.5 py-0.5 rounded ${
              bucket.side === "debit"
                ? "bg-blue-50 text-blue-700"
                : "bg-emerald-50 text-emerald-700"
            }`}
          >
            {bucket.side}
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-0.5">{bucket.hint}</p>
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full sm:w-72 px-3 py-2 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 text-sm bg-white disabled:bg-gray-50 disabled:text-gray-400"
      >
        <option value="">— select Xero account —</option>
        {accounts.map((acc) => (
          <option key={acc.Code} value={acc.Code}>
            {acc.Code} · {acc.Name}
          </option>
        ))}
      </select>
    </div>
  );
}

function ExportResult({
  journalId,
  lines,
  narration,
  date,
}: {
  journalId: string;
  lines: XeroExportLine[];
  narration: string;
  date: string;
}) {
  return (
    <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-4">
      <div className="flex items-start gap-2 mb-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-emerald-900">
            Posted to Xero.
          </p>
          <p className="text-xs text-emerald-800 mt-0.5">
            Journal ID: <span className="font-mono">{journalId}</span> · Date{" "}
            {date}
          </p>
          <p className="text-xs text-emerald-800">Narration: {narration}</p>
        </div>
      </div>
      <div className="bg-white rounded-lg border border-emerald-100 overflow-hidden">
        <table className="min-w-full text-xs">
          <thead className="bg-gray-50 text-gray-500 uppercase tracking-wider">
            <tr>
              <th className="px-3 py-2 text-left">Account</th>
              <th className="px-3 py-2 text-left">Description</th>
              <th className="px-3 py-2 text-right">Debit</th>
              <th className="px-3 py-2 text-right">Credit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {lines.map((line, i) => {
              const debit = line.amount > 0 ? line.amount : 0;
              const credit = line.amount < 0 ? -line.amount : 0;
              return (
                <tr key={`${line.account_code}-${i}`}>
                  <td className="px-3 py-2 font-mono">{line.account_code}</td>
                  <td className="px-3 py-2 text-gray-700">
                    {line.description}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-900">
                    {debit > 0 ? debit.toFixed(2) : ""}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-900">
                    {credit > 0 ? credit.toFixed(2) : ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
