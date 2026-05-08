"use client";

/**
 * Xero multi-org picker.
 *
 * After OAuth, if the user authorised the app for multiple Xero
 * orgs (common for bookkeepers and accounting firms), the backend
 * redirects here with a signed `?token=` referencing the pending
 * pick. We render a list of orgs and POST the chosen `tenantId`
 * back to /integrations/xero/pick-org.
 *
 * Server-side validates: HMAC of the token, presence of the chosen
 * id in the original authorised list, and 10-minute TTL — so this
 * page can't be exploited to bind the wrong org to the wrong Arbor
 * company.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import {
  AppButton,
  AppCard,
  ErrorState,
  LoadingState,
  toast,
} from "@/components/design-system";
import { apiClient } from "@/services/api/client";

interface PendingConnection {
  tenantId: string;
  tenantName: string;
  tenantType: string;
}

interface PendingOrgsResponse {
  connections: PendingConnection[];
}

export default function XeroPickOrgPage() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") ?? "";

  const [connections, setConnections] = useState<PendingConnection[] | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [chosenId, setChosenId] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) {
      setError(
        "Missing pick token. Restart the Xero connection from Settings → Integrations.",
      );
      setLoading(false);
      return;
    }
    setLoading(true);
    apiClient
      .get<PendingOrgsResponse>(
        `/integrations/xero/pending-orgs?token=${encodeURIComponent(token)}`,
      )
      .then((data) => {
        setConnections(data.connections);
        if (data.connections.length > 0) {
          setChosenId(data.connections[0].tenantId);
        }
      })
      .catch((err: unknown) => {
        const message =
          err instanceof Error
            ? err.message
            : "Could not load Xero organisations.";
        setError(message);
      })
      .finally(() => setLoading(false));
  }, [token]);

  async function handleSubmit() {
    if (!chosenId) return;
    setSubmitting(true);
    try {
      const resp = await apiClient.post<{ redirect_url: string }>(
        "/integrations/xero/pick-org",
        { token, xero_tenant_id: chosenId },
      );
      toast.success("Connected to Xero.");
      router.push(resp.redirect_url || "/settings/integrations?xero=connected");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Could not save your choice.";
      toast.error(message);
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-10 px-4 sm:px-6">
      <Link
        href="/settings/integrations"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-gray-600)] hover:text-[var(--color-gray-900)] mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to integrations
      </Link>

      <AppCard className="p-6 md:p-8 space-y-6">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0">
            <Building2 className="w-5 h-5 text-blue-600" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-[var(--color-gray-900)]">
              Choose your Xero organisation
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-1">
              You authorised Arbor for more than one Xero organisation. Pick the
              one to use for this company. You can switch later from Settings →
              Integrations.
            </p>
          </div>
        </div>

        {loading && (
          <div className="space-y-3">
            <LoadingState variant="list" count={3} />
            <p className="text-sm text-[var(--color-gray-500)] text-center">
              Loading your Xero organisations…
            </p>
          </div>
        )}

        {error && !loading && (
          <div className="space-y-4">
            <ErrorState
              variant="server"
              title="Could not load organisations"
              description={error}
            />
            <div className="text-center">
              <Link
                href="/settings/integrations"
                className="text-sm font-semibold text-blue-600 hover:text-blue-700"
              >
                Restart Xero connection
              </Link>
            </div>
          </div>
        )}

        {!loading && !error && connections && connections.length > 0 && (
          <div className="space-y-2">
            {connections.map((c) => {
              const selected = c.tenantId === chosenId;
              return (
                <button
                  key={c.tenantId}
                  type="button"
                  onClick={() => setChosenId(c.tenantId)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-left transition-colors ${
                    selected
                      ? "border-blue-500 bg-blue-50"
                      : "border-[var(--color-gray-200)] hover:border-[var(--color-gray-300)] bg-white"
                  }`}
                  aria-pressed={selected}
                >
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                      selected
                        ? "bg-blue-600 text-white"
                        : "bg-[var(--color-gray-100)] text-[var(--color-gray-500)]"
                    }`}
                  >
                    <Building2 className="w-4 h-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-[var(--color-gray-900)] truncate">
                      {c.tenantName || c.tenantId}
                    </p>
                    <p className="text-xs text-[var(--color-gray-500)] uppercase tracking-wider">
                      {c.tenantType || "ORGANISATION"}
                    </p>
                  </div>
                  {selected && (
                    <CheckCircle2 className="w-5 h-5 text-blue-600 shrink-0" />
                  )}
                </button>
              );
            })}
          </div>
        )}

        {!loading && !error && connections && (
          <div className="flex justify-end pt-2">
            <AppButton
              variant="primary"
              onClick={handleSubmit}
              disabled={!chosenId || submitting}
            >
              {submitting ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Connecting…
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  Connect this organisation
                  <ArrowRight className="w-4 h-4" />
                </span>
              )}
            </AppButton>
          </div>
        )}
      </AppCard>
    </div>
  );
}
