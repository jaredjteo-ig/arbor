/* ── Alerts Hooks ─────────────────────────────────────────── */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { alertsApi } from "@/services/api/alerts";
import type {
  AlertListResponse,
  AlertSeverity,
  AlertStatus,
  AlertUnreadCountResponse,
} from "@/types/api";

/** Query keys for alerts domain. */
export const alertKeys = {
  all: ["alerts"] as const,
  list: (params?: { severity?: AlertSeverity; status?: AlertStatus }) =>
    [...alertKeys.all, "list", params] as const,
  unreadCount: [...(["alerts", "unread-count"] as const)] as const,
};

/**
 * Fetch all alerts, optionally filtered by severity and status.
 */
export function useAlerts(params?: {
  severity?: AlertSeverity;
  status?: AlertStatus;
}) {
  return useQuery<AlertListResponse, Error>({
    queryKey: alertKeys.list(params),
    queryFn: () => alertsApi.list(params),
  });
}

/**
 * Fetch the unread alert count.
 */
export function useUnreadAlertCount() {
  return useQuery<AlertUnreadCountResponse, Error>({
    queryKey: alertKeys.unreadCount,
    queryFn: () => alertsApi.unreadCount(),
  });
}

/**
 * Mark an alert as read. Invalidates alert list and unread count on success.
 */
export function useMarkAlertRead() {
  const queryClient = useQueryClient();

  return useMutation<{ alert_id: string; status: string }, Error, string>({
    mutationFn: (alertId) => alertsApi.markAsRead(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.all });
    },
  });
}

/**
 * Dismiss an alert. Invalidates alert list and unread count on success.
 */
export function useDismissAlert() {
  const queryClient = useQueryClient();

  return useMutation<{ alert_id: string; status: string }, Error, string>({
    mutationFn: (alertId) => alertsApi.dismiss(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.all });
    },
  });
}
