"use client";

import { useEffect, useState } from "react";
import {
  Plug,
  Building2,
  Landmark,
  Mail,
  Phone,
  Calendar,
  CheckCircle,
  XCircle,
  RefreshCw,
  ExternalLink,
  Activity,
} from "lucide-react";
import Link from "next/link";
import {
  AppCard,
  AppButton,
  LoadingState,
  ErrorState,
  toast,
} from "@/components/design-system";
import {
  useIntegrationStatus,
  useConnectProvider,
  useDisconnectProvider,
  useTestConnection,
} from "@/hooks/api";
import type {
  ProviderStatus,
  ConnectionStatus,
} from "@/services/api/integrations";

/* ── Provider Catalog ────────────────────────────────────── */

interface ProviderConfig {
  id: string;
  name: string;
  description: string;
  category: string;
}

const PROVIDER_SECTIONS: {
  title: string;
  category: string;
  icon: typeof Building2;
  providers: ProviderConfig[];
}[] = [
  {
    title: "Accounting",
    category: "accounting",
    icon: Building2,
    providers: [
      {
        id: "xero",
        name: "Xero",
        description: "Cloud accounting for payroll journal entries",
        category: "accounting",
      },
      {
        id: "quickbooks",
        name: "QuickBooks Online",
        description: "Sync payroll data to QBO journals",
        category: "accounting",
      },
      {
        id: "zoho_books",
        name: "Zoho Books",
        description: "Payroll integration with Zoho accounting",
        category: "accounting",
      },
    ],
  },
  {
    title: "Banking",
    category: "banking",
    icon: Landmark,
    providers: [
      {
        id: "dbs_fast",
        name: "DBS FAST",
        description: "Bulk salary payment via DBS FAST transfer",
        category: "banking",
      },
      {
        id: "ocbc_velocity",
        name: "OCBC Velocity",
        description: "OCBC corporate banking integration",
        category: "banking",
      },
      {
        id: "paynow",
        name: "PayNow",
        description: "PayNow QR for individual payments and claims",
        category: "banking",
      },
    ],
  },
  {
    title: "Government",
    category: "government",
    icon: Landmark,
    providers: [
      {
        id: "corppass",
        name: "CorpPass",
        description:
          "Singapore government e-services authentication for CPF, IRAS filings",
        category: "government",
      },
    ],
  },
  {
    title: "Communications",
    category: "communications",
    icon: Mail,
    providers: [
      {
        id: "email_smtp",
        name: "Email (SMTP)",
        description: "Payslip delivery and notification emails",
        category: "communications",
      },
      {
        id: "whatsapp",
        name: "WhatsApp Business",
        description: "Employee notifications via WhatsApp",
        category: "communications",
      },
      {
        id: "telegram",
        name: "Telegram Bot",
        description: "Team notifications and alerts",
        category: "communications",
      },
      {
        id: "slack",
        name: "Slack",
        description: "Slack workspace integration for HR updates",
        category: "communications",
      },
      {
        id: "teams",
        name: "Microsoft Teams",
        description: "Teams notifications and HR bot",
        category: "communications",
      },
    ],
  },
  {
    title: "Calendar",
    category: "calendar",
    icon: Calendar,
    providers: [
      {
        id: "google_calendar",
        name: "Google Calendar",
        description: "Sync leave and shift schedules to Google Calendar",
        category: "calendar",
      },
      {
        id: "outlook_calendar",
        name: "Outlook Calendar",
        description: "Sync leave and shift schedules to Outlook",
        category: "calendar",
      },
    ],
  },
];

/* ── Status Badge ────────────────────────────────────────── */

function StatusBadge({ status }: { status: ConnectionStatus }) {
  if (status === "connected") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--color-success-bg)] text-[var(--color-success)]">
        <CheckCircle className="h-3 w-3" aria-hidden="true" />
        Connected
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--color-error-bg)] text-[var(--color-error)]">
        <XCircle className="h-3 w-3" aria-hidden="true" />
        Error
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-500)]">
      <XCircle className="h-3 w-3" aria-hidden="true" />
      Not Connected
    </span>
  );
}

/* ── Provider Row ────────────────────────────────────────── */

function ProviderRow({
  config,
  providerStatus,
}: {
  config: ProviderConfig;
  providerStatus: ProviderStatus | undefined;
}) {
  const [testing, setTesting] = useState(false);
  const connect = useConnectProvider();
  const disconnect = useDisconnectProvider();
  const testConn = useTestConnection();

  const status: ConnectionStatus = providerStatus?.status ?? "disconnected";
  const isConnected = status === "connected";
  const lastSync = providerStatus?.last_sync;

  const handleConnect = async () => {
    // Xero has a real OAuth round-trip (M1-T02) — start endpoint
    // returns a Xero-hosted consent URL we redirect the whole page
    // to. Other providers still go through the legacy stub for now.
    if (config.id === "xero") {
      try {
        const { integrationsApi } = await import("@/services/api/integrations");
        const result = await integrationsApi.xeroOauthStart();
        if (result.redirect_url) {
          window.location.assign(result.redirect_url);
          return;
        }
        toast.error("Could not start the Xero connection — please retry.");
      } catch {
        toast.error("Could not start the Xero connection — please retry.");
      }
      return;
    }
    try {
      const result = await connect.mutateAsync(config.id);
      if (result.redirect_url) {
        window.open(result.redirect_url, "_blank");
      }
      toast.success(`Connecting to ${config.name}...`);
    } catch {
      toast.error(`Failed to connect to ${config.name}. Please try again.`);
    }
  };

  const handleDisconnect = async () => {
    // Xero uses the PDPA-compliant hard-delete + Xero-side revoke
    // path (M1-T07). Other providers stay on the legacy stub.
    if (config.id === "xero") {
      try {
        const { integrationsApi } = await import("@/services/api/integrations");
        await integrationsApi.xeroDisconnect();
        toast.success("Xero disconnected.");
        // Force a status refresh — the integration card should flip
        // back to "Disconnected" immediately.
        window.location.reload();
      } catch {
        toast.error("Could not disconnect Xero — please retry.");
      }
      return;
    }
    try {
      await disconnect.mutateAsync(config.id);
      toast.success(`${config.name} disconnected.`);
    } catch {
      toast.error(`Failed to disconnect ${config.name}. Please try again.`);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await testConn.mutateAsync(config.id);
      if (result.success) {
        toast.success(
          `${config.name} is working. Response time: ${result.latency_ms}ms`,
        );
      } else {
        toast.error(`${config.name}: ${result.message}`);
      }
    } catch {
      toast.error(`Connection test failed for ${config.name}.`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 py-4 border-b border-[var(--color-gray-100)] last:border-b-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <p className="text-sm font-medium text-[var(--color-gray-900)]">
            {config.name}
          </p>
          <StatusBadge status={status} />
        </div>
        <p className="text-xs text-[var(--color-gray-500)]">
          {config.description}
        </p>
        {lastSync && (
          <p className="text-xs text-[var(--color-gray-400)] mt-1">
            Last sync:{" "}
            {new Date(lastSync).toLocaleString("en-SG", {
              dateStyle: "medium",
              timeStyle: "short",
            })}
          </p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {isConnected && (
          <AppButton
            variant="outlined"
            size="sm"
            onClick={handleTest}
            loading={testing}
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Test
          </AppButton>
        )}
        {isConnected ? (
          <AppButton
            variant="danger"
            size="sm"
            onClick={handleDisconnect}
            loading={disconnect.isPending}
          >
            Disconnect
          </AppButton>
        ) : (
          <AppButton
            variant="primary"
            size="sm"
            onClick={handleConnect}
            loading={connect.isPending}
          >
            Connect
          </AppButton>
        )}
      </div>
    </div>
  );
}

/* ── Integration Section ─────────────────────────────────── */

function IntegrationSection({
  section,
  statusMap,
}: {
  section: (typeof PROVIDER_SECTIONS)[number];
  statusMap: Map<string, ProviderStatus>;
}) {
  const Icon = section.icon;
  const connectedCount = section.providers.filter(
    (p) => statusMap.get(p.id)?.status === "connected",
  ).length;

  return (
    <AppCard
      variant="standard"
      header={
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon
              className="h-4 w-4 text-[var(--color-gray-500)]"
              aria-hidden="true"
            />
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              {section.title}
            </h2>
          </div>
          <span className="text-xs text-[var(--color-gray-400)]">
            {connectedCount}/{section.providers.length} connected
          </span>
        </div>
      }
    >
      {section.providers.map((provider) => (
        <ProviderRow
          key={provider.id}
          config={provider}
          providerStatus={statusMap.get(provider.id)}
        />
      ))}
    </AppCard>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

const _XERO_ERROR_MESSAGES: Record<string, string> = {
  token_exchange_failed:
    "Xero rejected the authorization code. Please try connecting again.",
  list_connections_failed:
    "Connected to Xero, but couldn't list your organisations. Try again.",
  no_orgs_authorized:
    "No Xero organisations were authorised. Pick at least one org during the consent step.",
  access_denied: "You declined to authorise Xero. No connection was made.",
};

export default function IntegrationSettingsPage() {
  const { data, isPending, error, refetch } = useIntegrationStatus();

  // Handle the round-trip return from Xero OAuth (M1-T02). Read the
  // query params once on mount, surface a toast, then clear them so
  // a refresh doesn't re-fire the toast. Stripped early-render keeps
  // the URL clean for share/back behaviour.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    const xero = url.searchParams.get("xero");
    const xeroError = url.searchParams.get("xero_error");

    if (xero === "connected") {
      toast.success(
        "Xero connected. You can now export payroll runs as ManualJournals.",
      );
      refetch();
    } else if (xeroError) {
      const friendly =
        _XERO_ERROR_MESSAGES[xeroError] ??
        `Xero connection error: ${xeroError}`;
      toast.error(friendly);
    }

    if (xero || xeroError) {
      url.searchParams.delete("xero");
      url.searchParams.delete("xero_error");
      window.history.replaceState({}, "", url.toString());
    }
  }, [refetch]);

  const statusMap = new Map<string, ProviderStatus>();
  if (data?.providers) {
    for (const p of data.providers) {
      statusMap.set(p.provider, p);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Plug
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Integrations
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Connect your accounting, banking, government, and communication
              tools.
            </p>
          </div>
        </div>
        <Link href="/settings/integrations/health">
          <AppButton variant="outlined" size="sm">
            <Activity className="h-3.5 w-3.5" aria-hidden="true" />
            Health Dashboard
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </AppButton>
        </Link>
      </div>

      {/* Content */}
      {isPending && <LoadingState variant="card" count={5} />}

      {error && (
        <ErrorState
          variant="server"
          title="Could not load integration status"
          description="We had trouble reaching the server. Please try again."
          onRetry={() => refetch()}
        />
      )}

      {data &&
        PROVIDER_SECTIONS.map((section) => (
          <IntegrationSection
            key={section.category}
            section={section}
            statusMap={statusMap}
          />
        ))}
    </div>
  );
}
