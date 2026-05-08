/* ── Integrations API Service ─────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export type ConnectionStatus = "connected" | "disconnected" | "error";

export interface ProviderStatus {
  provider: string;
  category: string;
  status: ConnectionStatus;
  last_sync: string | null;
  error_message: string | null;
}

export interface IntegrationStatusResponse {
  providers: ProviderStatus[];
}

export interface TestConnectionResponse {
  provider: string;
  success: boolean;
  message: string;
  latency_ms: number;
}

export type ConnectorHealthStatus = "healthy" | "degraded" | "down" | "unknown";

export type CircuitBreakerState = "closed" | "open" | "half-open";

export interface ConnectorHealth {
  connector_id: string;
  name: string;
  category: string;
  status: ConnectorHealthStatus;
  error_rate: number;
  last_success: string | null;
  last_failure: string | null;
  circuit_breaker: CircuitBreakerState;
  uptime_pct: number;
  avg_latency_ms: number;
}

export interface ConnectorHealthResponse {
  connectors: ConnectorHealth[];
  updated_at: string;
}

export type FilingStatus = "pending" | "submitted" | "confirmed" | "failed";

export interface GovernmentFiling {
  id: string;
  submission_type: string;
  period: string;
  status: FilingStatus;
  submitted_at: string | null;
  reference_id: string | null;
  error_message: string | null;
}

export interface FilingListResponse {
  filings: GovernmentFiling[];
  total: number;
}

export type SagaStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped";

export interface SagaStep {
  step_name: string;
  status: SagaStepStatus;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface SagaDetail {
  saga_id: string;
  filing_id: string;
  steps: SagaStep[];
  status: string;
  started_at: string;
  completed_at: string | null;
}

export type SyncStatus = "synced" | "pending" | "failed" | "not_synced";

export interface AccountingSyncRecord {
  run_id: number;
  period: string;
  provider: string;
  sync_status: SyncStatus;
  journal_reference: string | null;
  journal_url: string | null;
  synced_at: string | null;
  payroll_amount: number;
  accounting_amount: number | null;
  bank_amount: number | null;
  variance: number | null;
}

export interface AccountingSyncResponse {
  records: AccountingSyncRecord[];
  total: number;
}

export type NotificationChannel =
  | "email"
  | "whatsapp"
  | "telegram"
  | "slack"
  | "teams"
  | "sms";

export interface NotificationPreference {
  type: string;
  label: string;
  description: string;
  channels: NotificationChannel[];
}

export interface NotificationPreferencesResponse {
  preferences: NotificationPreference[];
  phone_number: string | null;
}

export interface UpdateNotificationPreferencesRequest {
  preferences: NotificationPreference[];
  phone_number: string | null;
}

export interface SkillsFutureCourse {
  id: string;
  title: string;
  provider: string;
  duration: string;
  fee: number;
  grant_eligible: boolean;
  grant_amount: number | null;
  sfc_eligible: boolean;
  topics: string[];
  description: string;
  schedule: string | null;
  url: string | null;
}

export interface SkillsFutureCourseListResponse {
  courses: SkillsFutureCourse[];
  total: number;
  /**
   * Where the catalogue came from. "live" = MCP-served from the
   * SkillsFuture directory. "curated-fallback" = fixed seed list returned
   * because the MCP tool was unavailable. The UI surfaces a banner so
   * buyers see we're transparent about live-vs-cache state.
   */
  source?: "live" | "curated-fallback";
}

export interface SkillsFutureGrantCheckResponse {
  eligible: boolean;
  grant_amount: number;
  sfc_balance: number;
  message: string;
}

export type ImportSource = "talenox" | "hreasily" | "csv";

export interface FieldMapping {
  source_field: string;
  target_field: string;
  sample_value: string | null;
  is_mapped: boolean;
}

export interface ImportValidationError {
  row: number;
  field: string;
  message: string;
}

export interface ImportPreviewResponse {
  source: ImportSource;
  total_records: number;
  valid_records: number;
  duplicate_count: number;
  field_mappings: FieldMapping[];
  validation_errors: ImportValidationError[];
  preview_rows: Record<string, string>[];
}

export interface ImportConfirmResponse {
  imported: number;
  skipped: number;
  errors: number;
  message: string;
}

export interface PayNowQRResponse {
  qr_data: string;
  amount: number;
  reference: string;
  expires_at: string;
}

/* ── API Methods ─────────────────────────────────────────── */

export interface GoogleCalendarStatus {
  connected: boolean;
  expires_at: string | null;
  last_synced_at: string | null;
  scope: string | null;
  channel_id?: string | null;
}

export const integrationsApi = {
  /** Get connection status for all configured providers. */
  status(): Promise<IntegrationStatusResponse> {
    return apiClient.get<IntegrationStatusResponse>("/integrations/status");
  },

  /** T-R055: Google Calendar — fetch the OAuth consent URL. */
  googleCalendarAuthUrl(): Promise<{ auth_url: string; state: string }> {
    return apiClient.get<{ auth_url: string; state: string }>(
      "/integrations/google-calendar/auth-url",
    );
  },

  /** T-R055: Google Calendar — connection status for the current company. */
  googleCalendarStatus(): Promise<GoogleCalendarStatus> {
    return apiClient.get<GoogleCalendarStatus>(
      "/integrations/google-calendar/status",
    );
  },

  /** T-R055: Google Calendar — revoke + delete the stored connection. */
  googleCalendarDisconnect(): Promise<{ disconnected: boolean }> {
    return apiClient.post<{ disconnected: boolean }>(
      "/integrations/google-calendar/disconnect",
    );
  },

  /** Connect a provider (initiates OAuth or API key setup). */
  connect(provider: string): Promise<{ redirect_url: string }> {
    return apiClient.post<{ redirect_url: string }>(
      `/integrations/${provider}/connect`,
    );
  },

  /** Disconnect a provider. */
  disconnect(provider: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      `/integrations/${provider}/disconnect`,
    );
  },

  /** Test the connection for a specific provider. */
  testConnection(provider: string): Promise<TestConnectionResponse> {
    return apiClient.post<TestConnectionResponse>(
      `/integrations/${provider}/test`,
    );
  },

  /** Get health status for all connectors. */
  connectorHealth(): Promise<ConnectorHealthResponse> {
    return apiClient.get<ConnectorHealthResponse>("/integrations/health");
  },

  /** Get government filing submissions. */
  filingsList(): Promise<FilingListResponse> {
    return apiClient.get<FilingListResponse>("/integrations/submissions");
  },

  /** Get saga detail for a filing. */
  sagaDetail(filingId: string): Promise<SagaDetail> {
    return apiClient.get<SagaDetail>(`/integrations/sagas/${filingId}`);
  },

  /** Retry a failed filing. */
  retryFiling(filingId: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      `/integrations/sagas/${filingId}/resume`,
    );
  },

  /** Get accounting sync status for payroll runs. */
  accountingSyncStatus(): Promise<AccountingSyncResponse> {
    return apiClient.get<AccountingSyncResponse>(
      "/integrations/accounting-sync",
    );
  },

  /** Trigger sync for a specific payroll run. */
  syncPayrollRun(runId: number): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      `/integrations/accounting-sync/${runId}`,
    );
  },

  /** Get notification preferences. */
  notificationPreferences(): Promise<NotificationPreferencesResponse> {
    return apiClient.get<NotificationPreferencesResponse>(
      "/settings/notification-preferences",
    );
  },

  /** Update notification preferences. */
  updateNotificationPreferences(
    data: UpdateNotificationPreferencesRequest,
  ): Promise<NotificationPreferencesResponse> {
    return apiClient.put<NotificationPreferencesResponse>(
      "/settings/notification-preferences",
      data,
    );
  },

  /** Test a notification channel. */
  testNotification(
    channel: NotificationChannel,
  ): Promise<{ success: boolean; message: string }> {
    return apiClient.post<{ success: boolean; message: string }>(
      `/settings/notification-preferences/test`,
      { channel },
    );
  },

  /** Search SkillsFuture courses. */
  skillsFutureCourses(params?: {
    query?: string;
    topic?: string;
    duration?: string;
    funding?: string;
  }): Promise<SkillsFutureCourseListResponse> {
    const queryParams: Record<string, string> = {};
    if (params?.query) queryParams.query = params.query;
    if (params?.topic) queryParams.topic = params.topic;
    if (params?.duration) queryParams.duration = params.duration;
    if (params?.funding) queryParams.funding = params.funding;
    return apiClient.get<SkillsFutureCourseListResponse>(
      "/integrations/skillsfuture/courses",
      queryParams,
    );
  },

  /** Check grant eligibility for a course. */
  checkGrant(courseId: string): Promise<SkillsFutureGrantCheckResponse> {
    return apiClient.get<SkillsFutureGrantCheckResponse>(
      `/integrations/skillsfuture/courses/${courseId}/grant-check`,
    );
  },

  /** Preview import data. */
  importPreview(
    source: ImportSource,
    data?: FormData,
  ): Promise<ImportPreviewResponse> {
    if (data) {
      return apiClient.postFormData<ImportPreviewResponse>(
        `/integrations/import/preview`,
        data,
      );
    }
    return apiClient.post<ImportPreviewResponse>(
      `/integrations/import/preview`,
      { source },
    );
  },

  /** Confirm and execute import. */
  importConfirm(
    source: ImportSource,
    field_mappings: FieldMapping[],
  ): Promise<ImportConfirmResponse> {
    return apiClient.post<ImportConfirmResponse>(
      `/integrations/import/confirm`,
      { source, field_mappings },
    );
  },

  /** Generate PayNow QR code. */
  payNowQR(amount: number, reference: string): Promise<PayNowQRResponse> {
    return apiClient.post<PayNowQRResponse>("/banking/paynow-qr", {
      amount,
      reference,
    });
  },

  /**
   * Begin the Xero OAuth round-trip. Returns a redirect URL the
   * frontend uses for full-page navigation (Xero's consent screen
   * blocks framing).
   */
  xeroOauthStart(): Promise<{ redirect_url: string }> {
    return apiClient.get<{ redirect_url: string }>(
      "/integrations/xero/oauth/start",
    );
  },

  /**
   * Hard-disconnect Xero — revokes Arbor's authorisation at Xero's
   * side and hard-deletes the IntegrationToken row (PDPA M1-T07).
   */
  xeroDisconnect(): Promise<{ disconnected: boolean }> {
    return apiClient.post<{ disconnected: boolean }>(
      "/integrations/xero/disconnect",
    );
  },

  /**
   * Live diagnostic — hits Xero /connections and reports
   * success/latency/tenant info. M3-T05.
   */
  xeroTestConnection(): Promise<{
    success: boolean;
    message: string;
    latency_ms: number;
    tenant_name: string;
    tenant_id?: string;
    tenant_type?: string;
    scopes: string[];
    connection_count?: number;
  }> {
    return apiClient.get("/integrations/xero/test");
  },
};
