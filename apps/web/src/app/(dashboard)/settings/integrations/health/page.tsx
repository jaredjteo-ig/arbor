"use client";

import {
  Activity,
  CheckCircle,
  AlertTriangle,
  XCircle,
  HelpCircle,
  RefreshCw,
  Clock,
  Zap,
} from "lucide-react";
import { AppCard, LoadingState, ErrorState } from "@/components/design-system";
import { useConnectorHealth } from "@/hooks/api";
import type {
  ConnectorHealth,
  ConnectorHealthStatus,
  CircuitBreakerState,
} from "@/services/api/integrations";

/* ── Status Helpers ──────────────────────────────────────── */

const STATUS_CONFIG: Record<
  ConnectorHealthStatus,
  {
    icon: typeof CheckCircle;
    color: string;
    bg: string;
    border: string;
    label: string;
  }
> = {
  healthy: {
    icon: CheckCircle,
    color: "text-[var(--color-success)]",
    bg: "bg-[var(--color-success-bg)]",
    border: "border-[var(--color-risk-green-border)]",
    label: "Healthy",
  },
  degraded: {
    icon: AlertTriangle,
    color: "text-[var(--color-warning)]",
    bg: "bg-[var(--color-warning-bg)]",
    border: "border-[var(--color-risk-amber-border)]",
    label: "Degraded",
  },
  down: {
    icon: XCircle,
    color: "text-[var(--color-error)]",
    bg: "bg-[var(--color-error-bg)]",
    border: "border-[var(--color-risk-red-border)]",
    label: "Down",
  },
  unknown: {
    icon: HelpCircle,
    color: "text-[var(--color-gray-400)]",
    bg: "bg-[var(--color-gray-50)]",
    border: "border-[var(--color-gray-200)]",
    label: "Unknown",
  },
};

const CIRCUIT_BREAKER_LABELS: Record<CircuitBreakerState, string> = {
  closed: "Closed (normal)",
  open: "Open (blocking)",
  "half-open": "Half-open (testing)",
};

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

/* ── Health Card ─────────────────────────────────────────── */

function HealthCard({ connector }: { connector: ConnectorHealth }) {
  const config = STATUS_CONFIG[connector.status];
  const Icon = config.icon;

  return (
    <div
      className={`
        rounded-[12px] border p-5 transition-colors
        bg-[var(--color-surface-card)]
        ${config.border}
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-[var(--color-gray-900)] truncate">
            {connector.name}
          </p>
          <p className="text-xs text-[var(--color-gray-400)] mt-0.5">
            {connector.category}
          </p>
        </div>
        <div className={`flex items-center gap-1.5 ${config.color}`}>
          <Icon className="h-4 w-4" aria-hidden="true" />
          <span className="text-xs font-medium">{config.label}</span>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="rounded-lg bg-[var(--color-gray-50)] p-3">
          <p className="text-xs text-[var(--color-gray-500)] mb-1">
            Error Rate
          </p>
          <p
            className={`text-lg font-semibold ${
              (connector.error_rate ?? 0) > 10
                ? "text-[var(--color-error)]"
                : (connector.error_rate ?? 0) > 5
                  ? "text-[var(--color-warning)]"
                  : "text-[var(--color-gray-900)]"
            }`}
          >
            {(connector.error_rate ?? 0).toFixed(1)}%
          </p>
        </div>
        <div className="rounded-lg bg-[var(--color-gray-50)] p-3">
          <p className="text-xs text-[var(--color-gray-500)] mb-1">
            Avg Latency
          </p>
          <p className="text-lg font-semibold text-[var(--color-gray-900)]">
            {connector.avg_latency_ms ?? 0}ms
          </p>
        </div>
        <div className="rounded-lg bg-[var(--color-gray-50)] p-3">
          <p className="text-xs text-[var(--color-gray-500)] mb-1">Uptime</p>
          <p className="text-lg font-semibold text-[var(--color-gray-900)]">
            {(connector.uptime_pct ?? 0).toFixed(1)}%
          </p>
        </div>
        <div className="rounded-lg bg-[var(--color-gray-50)] p-3">
          <p className="text-xs text-[var(--color-gray-500)] mb-1">
            Circuit Breaker
          </p>
          <p
            className={`text-xs font-medium ${
              connector.circuit_breaker === "open"
                ? "text-[var(--color-error)]"
                : connector.circuit_breaker === "half-open"
                  ? "text-[var(--color-warning)]"
                  : "text-[var(--color-success)]"
            }`}
          >
            {CIRCUIT_BREAKER_LABELS[connector.circuit_breaker]}
          </p>
        </div>
      </div>

      {/* Timestamps */}
      <div className="flex items-center justify-between text-xs text-[var(--color-gray-400)]">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" aria-hidden="true" />
          <span>Last OK: {formatTimeAgo(connector.last_success)}</span>
        </div>
        {connector.last_failure && (
          <div className="flex items-center gap-1 text-[var(--color-error)]">
            <Zap className="h-3 w-3" aria-hidden="true" />
            <span>Last fail: {formatTimeAgo(connector.last_failure)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Summary Bar ─────────────────────────────────────────── */

function SummaryBar({ connectors }: { connectors: ConnectorHealth[] }) {
  const counts = { healthy: 0, degraded: 0, down: 0, unknown: 0 };
  for (const c of connectors) {
    counts[c.status]++;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {(Object.entries(counts) as [ConnectorHealthStatus, number][]).map(
        ([status, count]) => {
          const config = STATUS_CONFIG[status];
          const Icon = config.icon;
          return (
            <div
              key={status}
              className={`flex items-center gap-3 rounded-[12px] border p-4 ${config.bg} ${config.border}`}
            >
              <Icon className={`h-5 w-5 ${config.color}`} aria-hidden="true" />
              <div>
                <p className="text-2xl font-bold text-[var(--color-gray-900)]">
                  {count}
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">
                  {config.label}
                </p>
              </div>
            </div>
          );
        },
      )}
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function ConnectorHealthDashboard() {
  const { data, isPending, error, refetch, dataUpdatedAt } =
    useConnectorHealth();

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Activity
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Connector Health
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Real-time health status for all external connectors.
              Auto-refreshes every 30 seconds.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {dataUpdatedAt > 0 && (
            <span className="text-xs text-[var(--color-gray-400)] hidden sm:inline">
              Updated{" "}
              {new Date(dataUpdatedAt).toLocaleTimeString("en-SG", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>
          )}
          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center justify-center rounded-[8px] p-2 min-h-[36px] min-w-[36px]
              text-[var(--color-gray-500)] hover:bg-[var(--color-gray-100)] transition-colors
              focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            aria-label="Refresh health data"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Content */}
      {isPending && <LoadingState variant="card" count={6} />}

      {error && (
        <ErrorState
          variant="server"
          title="Could not load connector health"
          description="We had trouble reaching the health monitoring service."
          onRetry={() => refetch()}
        />
      )}

      {data && (
        <>
          <SummaryBar connectors={data.connectors} />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.connectors.map((connector) => (
              <HealthCard key={connector.connector_id} connector={connector} />
            ))}
          </div>

          {data.connectors.length === 0 && (
            <AppCard variant="flat">
              <div className="text-center py-8">
                <Activity
                  className="h-12 w-12 text-[var(--color-gray-300)] mx-auto mb-3"
                  aria-hidden="true"
                />
                <p className="text-sm text-[var(--color-gray-500)]">
                  No connectors configured yet. Connect your first integration
                  to see health data here.
                </p>
              </div>
            </AppCard>
          )}
        </>
      )}
    </div>
  );
}
