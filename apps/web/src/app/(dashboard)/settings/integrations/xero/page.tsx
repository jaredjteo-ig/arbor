"use client";

/**
 * Xero settings page — connection status + account mapping.
 *
 * Lives at /settings/integrations/xero. Reachable from the
 * Integrations card. Lets the user:
 *  - See which Xero org they're connected to and when.
 *  - Edit the six bucket → Xero account-code mappings without
 *    running a payroll export.
 *  - Refresh the chart of accounts when their accountant has
 *    archived/renamed accounts in Xero.
 *  - See a banner if the saved mapping references stale codes
 *    (M1-T06 mapping-health).
 *  - Disconnect (PDPA-compliant hard-delete + Xero-side revoke).
 *
 * The mapping form uses an account-code typeahead (M2-T09) so users
 * can search by code OR account name, preventing the
 * number-vs-code confusion when typing freely.
 */

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  CheckCircle2,
  ExternalLink,
  Loader2,
  RefreshCw,
  Search,
  TriangleAlert,
} from "lucide-react";
import {
  AppButton,
  AppCard,
  ErrorState,
  LoadingState,
  toast,
} from "@/components/design-system";
import {
  useSaveXeroMapping,
  useXeroChartOfAccounts,
  useXeroMapping,
  useXeroMappingHealth,
  useXeroPayrollStatus,
} from "@/hooks/api";
import {
  xeroPayrollApi,
  type XeroAccount,
  type XeroAccountMapping,
} from "@/services/api/payroll";
import { integrationsApi } from "@/services/api/integrations";

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
    hint: "Debit account for bonuses paid.",
    side: "debit",
  },
  {
    key: "employer_cpf_expense_code",
    label: "Employer CPF Expense",
    hint: "Debit — employer share of CPF.",
    side: "debit",
  },
  {
    key: "sdl_expense_code",
    label: "SDL + FWL Expense",
    hint: "Debit — SDL (and FWL if applicable).",
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

export default function XeroSettingsPage() {
  const status = useXeroPayrollStatus();
  const [forceRefresh, setForceRefresh] = useState(false);
  const chart = useXeroChartOfAccounts(true, forceRefresh);
  const mapping = useXeroMapping(true);
  const health = useXeroMappingHealth(true);
  const saveMapping = useSaveXeroMapping();

  const [overrides, setOverrides] = useState<Partial<XeroAccountMapping>>({});
  const [disconnecting, setDisconnecting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const accounts: XeroAccount[] = chart.data?.accounts ?? [];
  const draft: XeroAccountMapping = useMemo(
    () => ({
      ...EMPTY_MAPPING,
      ...(mapping.data?.mapping ?? {}),
      ...overrides,
    }),
    [mapping.data?.mapping, overrides],
  );

  const mappingChanged = useMemo(() => {
    if (!mapping.data) return Object.keys(overrides).length > 0;
    return BUCKETS.some((b) => mapping.data!.mapping[b.key] !== draft[b.key]);
  }, [mapping.data, draft, overrides]);

  // Bridge `?xero=connected` toast on first land
  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (url.searchParams.get("xero") === "connected") {
      toast.success("Xero connected.");
      url.searchParams.delete("xero");
      window.history.replaceState({}, "", url.toString());
    }
  }, []);

  const isConnected = status.data?.connected ?? false;

  async function handleSave() {
    try {
      await saveMapping.mutateAsync(draft);
      setOverrides({});
      toast.success("Xero account mapping saved.");
      health.refetch();
    } catch (err: unknown) {
      const m = err instanceof Error ? err.message : "Failed to save mapping.";
      toast.error(m);
    }
  }

  async function handleRefresh() {
    setForceRefresh(true);
    setRefreshing(true);
    try {
      await chart.refetch();
      await health.refetch();
      toast.success("Pulled the latest chart of accounts from Xero.");
    } catch (err: unknown) {
      const m =
        err instanceof Error
          ? err.message
          : "Failed to refresh accounts from Xero.";
      toast.error(m);
    } finally {
      setRefreshing(false);
      // Drop the force flag so subsequent reads use the cache.
      setTimeout(() => setForceRefresh(false), 0);
    }
  }

  async function handleConnect() {
    try {
      const r = await integrationsApi.xeroOauthStart();
      if (r.redirect_url) window.location.assign(r.redirect_url);
    } catch {
      toast.error("Could not start the Xero connection.");
    }
  }

  async function handleDisconnect() {
    if (
      !window.confirm(
        "Disconnect Xero? Central will stop posting journals and the OAuth token will be deleted. You can reconnect at any time.",
      )
    ) {
      return;
    }
    setDisconnecting(true);
    try {
      await integrationsApi.xeroDisconnect();
      toast.success("Xero disconnected.");
      window.location.reload();
    } catch {
      toast.error("Failed to disconnect Xero.");
    } finally {
      setDisconnecting(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      <Link
        href="/settings/integrations"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-gray-600)] hover:text-[var(--color-gray-900)]"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to integrations
      </Link>

      <AppCard className="p-6 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0">
              <Building2 className="w-5 h-5 text-blue-600" />
            </div>
            <div className="min-w-0">
              <h1 className="text-xl font-bold text-[var(--color-gray-900)]">
                Xero
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Post payroll journals to your Xero organisation as
                ManualJournals.
              </p>
            </div>
          </div>
          {isConnected ? (
            <AppButton
              variant="danger"
              size="sm"
              onClick={handleDisconnect}
              loading={disconnecting}
            >
              Disconnect
            </AppButton>
          ) : (
            <AppButton variant="primary" size="sm" onClick={handleConnect}>
              Connect Xero
              <ArrowRight className="w-3.5 h-3.5" />
            </AppButton>
          )}
        </div>

        {!isConnected && (
          <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900">
            Xero isn&apos;t connected. Click <strong>Connect Xero</strong> to
            authorise.
          </div>
        )}
      </AppCard>

      {isConnected && (
        <AppCard className="p-6 space-y-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-[var(--color-gray-900)]">
                Account mapping
              </h2>
              <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                Choose which Xero accounts each payroll bucket posts to. Saved
                across exports — re-edit any time.
              </p>
            </div>
            <AppButton
              variant="outlined"
              size="sm"
              onClick={handleRefresh}
              loading={refreshing}
              disabled={refreshing || chart.isFetching}
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh accounts
            </AppButton>
          </div>

          <MappingHealthBanner
            health={health.data}
            loading={health.isLoading}
            error={health.error}
          />

          {chart.isLoading || mapping.isLoading ? (
            <LoadingState variant="list" count={6} />
          ) : chart.error ? (
            <ErrorState
              variant="server"
              title="Could not load Xero accounts"
              description={chart.error.message}
            />
          ) : (
            <div className="space-y-3">
              {BUCKETS.map((bucket) => (
                <BucketRow
                  key={bucket.key}
                  bucket={bucket}
                  accounts={accounts}
                  value={draft[bucket.key]}
                  onChange={(next) =>
                    setOverrides((prev) => ({ ...prev, [bucket.key]: next }))
                  }
                />
              ))}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--color-gray-100)]">
            <span className="text-xs text-[var(--color-gray-500)] mr-auto">
              {mappingChanged
                ? "Unsaved changes"
                : `Last saved ${
                    mapping.data?.last_updated_at
                      ? new Date(
                          mapping.data.last_updated_at,
                        ).toLocaleDateString("en-SG", {
                          dateStyle: "medium",
                        })
                      : "—"
                  }`}
            </span>
            <AppButton
              variant="primary"
              size="sm"
              onClick={handleSave}
              loading={saveMapping.isPending}
              disabled={!mappingChanged || saveMapping.isPending}
            >
              Save mapping
            </AppButton>
          </div>
        </AppCard>
      )}

      <p className="text-xs text-[var(--color-gray-500)] text-center">
        <Link
          href="https://developer.xero.com/documentation/guides/oauth2/scopes/"
          className="underline hover:no-underline"
          target="_blank"
          rel="noreferrer"
        >
          Learn about Xero scopes
        </Link>{" "}
        ·{" "}
        <Link
          href="/help/xero-integration"
          className="underline hover:no-underline"
        >
          Xero integration help
        </Link>
      </p>
    </div>
  );
}

function MappingHealthBanner({
  health,
  loading,
  error,
}: {
  health:
    | {
        archived: string[];
        missing: string[];
        system_managed: string[];
        ok: boolean;
      }
    | undefined;
  loading: boolean;
  error: Error | null;
}) {
  if (loading || error || !health || health.ok) return null;
  const lines: string[] = [];
  if (health.missing.length > 0) {
    lines.push(
      `Missing in Xero: ${health.missing.join(", ")} — these codes no longer exist.`,
    );
  }
  if (health.archived.length > 0) {
    lines.push(
      `Archived in Xero: ${health.archived.join(", ")} — these have been deactivated.`,
    );
  }
  if (health.system_managed.length > 0) {
    lines.push(
      `System-managed: ${health.system_managed.join(
        ", ",
      )} — Xero won't accept ManualJournal posts to these accounts.`,
    );
  }
  return (
    <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900 flex items-start gap-2">
      <TriangleAlert className="w-4 h-4 mt-0.5 shrink-0" />
      <div>
        <p className="font-semibold mb-1">
          Some mapped accounts need updating before your next export.
        </p>
        <ul className="list-disc list-inside space-y-0.5">
          {lines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
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
  onChange: (next: string) => void;
}

function BucketRow({ bucket, accounts, value, onChange }: BucketRowProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_minmax(280px,1fr)] gap-3 items-start py-3 border-b border-[var(--color-gray-100)] last:border-b-0">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[var(--color-gray-900)]">
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
        <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
          {bucket.hint}
        </p>
      </div>
      <AccountTypeahead accounts={accounts} value={value} onChange={onChange} />
    </div>
  );
}

/**
 * Filterable account picker — searches by code OR name (M2-T09). Skips
 * inactive and system-managed accounts since Xero rejects manual
 * journals against those.
 */
function AccountTypeahead({
  accounts,
  value,
  onChange,
}: {
  accounts: XeroAccount[];
  value: string;
  onChange: (next: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const usable = useMemo(
    () =>
      accounts
        .filter(
          (a) => a.code && (a.status || "ACTIVE").toUpperCase() === "ACTIVE",
        )
        .sort((a, b) => a.code.localeCompare(b.code)),
    [accounts],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return usable;
    return usable.filter(
      (a) =>
        a.code.toLowerCase().includes(q) || a.name.toLowerCase().includes(q),
    );
  }, [usable, query]);

  const current = accounts.find((a) => a.code === value);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          setOpen((v) => !v);
          if (!open) setQuery("");
        }}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg border border-[var(--color-gray-300)] bg-white text-sm text-left hover:border-[var(--color-gray-400)] focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none"
      >
        <span className="min-w-0 truncate">
          {value ? (
            <>
              <span className="font-mono">{value}</span>
              {current && (
                <span className="text-[var(--color-gray-500)] ml-1.5">
                  · {current.name}
                </span>
              )}
            </>
          ) : (
            <span className="text-[var(--color-gray-400)]">
              Pick a Xero account
            </span>
          )}
        </span>
        <Search className="w-3.5 h-3.5 text-[var(--color-gray-400)]" />
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-full bg-white border border-[var(--color-gray-200)] rounded-lg shadow-lg max-h-72 overflow-hidden flex flex-col">
          <input
            autoFocus
            type="text"
            placeholder="Search code or name…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="px-3 py-2 text-sm border-b border-[var(--color-gray-100)] focus:outline-none"
          />
          <div className="overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="px-3 py-3 text-xs text-[var(--color-gray-500)]">
                No matching accounts.
              </p>
            ) : (
              filtered.slice(0, 50).map((a) => (
                <button
                  key={a.code}
                  type="button"
                  onClick={() => {
                    onChange(a.code);
                    setOpen(false);
                    setQuery("");
                  }}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-blue-50 flex items-center gap-2 ${
                    a.code === value ? "bg-blue-50" : ""
                  }`}
                >
                  <span className="font-mono text-xs text-[var(--color-gray-700)] w-12 shrink-0">
                    {a.code}
                  </span>
                  <span className="min-w-0 truncate">{a.name}</span>
                  <span className="ml-auto text-[10px] uppercase tracking-wider text-[var(--color-gray-400)]">
                    {a.type}
                  </span>
                  {a.code === value && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                  )}
                </button>
              ))
            )}
            {filtered.length > 50 && (
              <p className="px-3 py-2 text-xs text-[var(--color-gray-400)]">
                Showing first 50 — keep typing to narrow.
              </p>
            )}
          </div>
        </div>
      )}
      <div className="text-xs mt-1">
        <Link
          href={`https://go.xero.com/`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-[var(--color-gray-400)] hover:text-[var(--color-gray-600)]"
        >
          Open Xero <ExternalLink className="w-3 h-3" />
        </Link>
      </div>
    </div>
  );
}
