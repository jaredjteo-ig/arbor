/* ── Alerts API Service ───────────────────────────────────── */

import { apiClient } from "./client";
import type {
  Alert,
  AlertSeverity,
  AlertStatus,
  AlertListResponse,
  AlertUnreadCountResponse,
} from "@/types/api";

export type { Alert, AlertSeverity, AlertStatus, AlertListResponse };

export const alertsApi = {
  /** List regulatory alerts, optionally filtered by severity and status. */
  list(params?: {
    severity?: AlertSeverity;
    status?: AlertStatus;
  }): Promise<AlertListResponse> {
    const queryParams: Record<string, string> = {};
    if (params?.severity) queryParams.severity = params.severity;
    if (params?.status) queryParams.status = params.status;
    return apiClient.get<AlertListResponse>("/alerts", queryParams);
  },

  /** Mark a specific alert as read. */
  markAsRead(alertId: string): Promise<{ alert_id: string; status: string }> {
    return apiClient.post<{ alert_id: string; status: string }>(
      `/alerts/${alertId}/read`,
    );
  },

  /** Dismiss a specific alert. */
  dismiss(alertId: string): Promise<{ alert_id: string; status: string }> {
    return apiClient.post<{ alert_id: string; status: string }>(
      `/alerts/${alertId}/dismiss`,
    );
  },

  /** Get the count of unread alerts. */
  unreadCount(): Promise<AlertUnreadCountResponse> {
    return apiClient.get<AlertUnreadCountResponse>("/alerts/unread-count");
  },
} as const;
