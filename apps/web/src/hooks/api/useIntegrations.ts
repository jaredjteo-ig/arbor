/* ── Integration Hooks ────────────────────────────────────── */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  integrationsApi,
  type IntegrationStatusResponse,
  type ConnectorHealthResponse,
  type FilingListResponse,
  type SagaDetail,
  type AccountingSyncResponse,
  type NotificationPreferencesResponse,
  type UpdateNotificationPreferencesRequest,
  type NotificationChannel,
  type SkillsFutureCourseListResponse,
  type SkillsFutureGrantCheckResponse,
  type ImportPreviewResponse,
  type ImportConfirmResponse,
  type ImportSource,
  type FieldMapping,
  type PayNowQRResponse,
  type TestConnectionResponse,
} from "@/services/api/integrations";

/** Query keys for the integrations domain. */
export const integrationKeys = {
  all: ["integrations"] as const,
  status: () => [...integrationKeys.all, "status"] as const,
  connectorHealth: () => [...integrationKeys.all, "connectorHealth"] as const,
  filings: () => [...integrationKeys.all, "filings"] as const,
  saga: (filingId: string) =>
    [...integrationKeys.all, "saga", filingId] as const,
  accountingSync: () => [...integrationKeys.all, "accountingSync"] as const,
  notificationPrefs: () =>
    [...integrationKeys.all, "notificationPrefs"] as const,
  skillsfutureCourses: (params?: Record<string, string>) =>
    [...integrationKeys.all, "skillsfuture", params ?? {}] as const,
  grantCheck: (courseId: string) =>
    [...integrationKeys.all, "grantCheck", courseId] as const,
  importPreview: () => [...integrationKeys.all, "importPreview"] as const,
  payNowQR: (reference: string) =>
    [...integrationKeys.all, "payNowQR", reference] as const,
};

/* ── Queries ─────────────────────────────────────────────── */

/** Fetch integration connection statuses for all providers. */
export function useIntegrationStatus() {
  return useQuery<IntegrationStatusResponse, Error>({
    queryKey: integrationKeys.status(),
    queryFn: () => integrationsApi.status(),
  });
}

/** Fetch connector health dashboard data. Auto-refreshes every 30s. */
export function useConnectorHealth() {
  return useQuery<ConnectorHealthResponse, Error>({
    queryKey: integrationKeys.connectorHealth(),
    queryFn: () => integrationsApi.connectorHealth(),
    refetchInterval: 30_000,
  });
}

/** Fetch government filing submissions. */
export function useFilings() {
  return useQuery<FilingListResponse, Error>({
    queryKey: integrationKeys.filings(),
    queryFn: () => integrationsApi.filingsList(),
  });
}

/** Fetch saga detail for a specific filing. */
export function useSagaDetail(filingId: string | null) {
  return useQuery<SagaDetail, Error>({
    queryKey: integrationKeys.saga(filingId ?? ""),
    queryFn: () => integrationsApi.sagaDetail(filingId!),
    enabled: !!filingId,
  });
}

/** Fetch accounting sync status for payroll runs. */
export function useAccountingSync() {
  return useQuery<AccountingSyncResponse, Error>({
    queryKey: integrationKeys.accountingSync(),
    queryFn: () => integrationsApi.accountingSyncStatus(),
  });
}

/** Fetch notification preferences. */
export function useNotificationPreferences() {
  return useQuery<NotificationPreferencesResponse, Error>({
    queryKey: integrationKeys.notificationPrefs(),
    queryFn: () => integrationsApi.notificationPreferences(),
  });
}

/** Search SkillsFuture courses. */
export function useSkillsFutureCourses(params?: {
  query?: string;
  topic?: string;
  duration?: string;
  funding?: string;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.query) queryParams.query = params.query;
  if (params?.topic) queryParams.topic = params.topic;
  if (params?.duration) queryParams.duration = params.duration;
  if (params?.funding) queryParams.funding = params.funding;

  return useQuery<SkillsFutureCourseListResponse, Error>({
    queryKey: integrationKeys.skillsfutureCourses(queryParams),
    queryFn: () => integrationsApi.skillsFutureCourses(params),
  });
}

/** Check grant eligibility for a course. */
export function useGrantCheck(courseId: string | null) {
  return useQuery<SkillsFutureGrantCheckResponse, Error>({
    queryKey: integrationKeys.grantCheck(courseId ?? ""),
    queryFn: () => integrationsApi.checkGrant(courseId!),
    enabled: !!courseId,
  });
}

/* ── Mutations ───────────────────────────────────────────── */

/** Connect a provider. */
export function useConnectProvider() {
  const queryClient = useQueryClient();
  return useMutation<{ redirect_url: string }, Error, string>({
    mutationFn: (provider) => integrationsApi.connect(provider),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.status(),
      });
    },
  });
}

/** Disconnect a provider. */
export function useDisconnectProvider() {
  const queryClient = useQueryClient();
  return useMutation<{ message: string }, Error, string>({
    mutationFn: (provider) => integrationsApi.disconnect(provider),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.status(),
      });
    },
  });
}

/** Test a provider connection. */
export function useTestConnection() {
  return useMutation<TestConnectionResponse, Error, string>({
    mutationFn: (provider) => integrationsApi.testConnection(provider),
  });
}

/** Retry a failed government filing. */
export function useRetryFiling() {
  const queryClient = useQueryClient();
  return useMutation<{ message: string }, Error, string>({
    mutationFn: (filingId) => integrationsApi.retryFiling(filingId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.filings(),
      });
    },
  });
}

/** Trigger accounting sync for a payroll run. */
export function useSyncPayrollRun() {
  const queryClient = useQueryClient();
  return useMutation<{ message: string }, Error, number>({
    mutationFn: (runId) => integrationsApi.syncPayrollRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.accountingSync(),
      });
    },
  });
}

/** Update notification preferences. */
export function useUpdateNotificationPreferences() {
  const queryClient = useQueryClient();
  return useMutation<
    NotificationPreferencesResponse,
    Error,
    UpdateNotificationPreferencesRequest
  >({
    mutationFn: (data) => integrationsApi.updateNotificationPreferences(data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.notificationPrefs(),
      });
    },
  });
}

/** Test a notification channel. */
export function useTestNotification() {
  return useMutation<
    { success: boolean; message: string },
    Error,
    NotificationChannel
  >({
    mutationFn: (channel) => integrationsApi.testNotification(channel),
  });
}

/** Preview import data. */
export function useImportPreview() {
  return useMutation<
    ImportPreviewResponse,
    Error,
    { source: ImportSource; data?: FormData }
  >({
    mutationFn: ({ source, data }) =>
      integrationsApi.importPreview(source, data),
  });
}

/** Confirm and execute import. */
export function useImportConfirm() {
  return useMutation<
    ImportConfirmResponse,
    Error,
    { source: ImportSource; field_mappings: FieldMapping[] }
  >({
    mutationFn: ({ source, field_mappings }) =>
      integrationsApi.importConfirm(source, field_mappings),
  });
}

/** Generate PayNow QR code. */
export function usePayNowQR() {
  return useMutation<
    PayNowQRResponse,
    Error,
    { amount: number; reference: string }
  >({
    mutationFn: ({ amount, reference }) =>
      integrationsApi.payNowQR(amount, reference),
  });
}
