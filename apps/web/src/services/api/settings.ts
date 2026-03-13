/* ── Settings API Service ─────────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface NotificationSettings {
  emailAlerts: boolean;
  pushNotifications: boolean;
  inAppNotifications: boolean;
  alertFrequency: "immediately" | "daily" | "weekly";
}

export interface DisplaySettings {
  textSize: "normal" | "large" | "extra-large";
}

export interface UserSettings {
  notifications: NotificationSettings;
  display: DisplaySettings;
  language: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ChangePasswordResponse {
  message: string;
}

/* ── API Methods ─────────────────────────────────────────── */

export const settingsApi = {
  /** Get current user's settings. */
  get(): Promise<UserSettings> {
    return apiClient.get<UserSettings>("/settings");
  },

  /** Update user settings (partial merge). */
  update(data: Partial<UserSettings>): Promise<UserSettings> {
    return apiClient.put<UserSettings>("/settings", data);
  },

  /** Change the current user's password. */
  changePassword(data: ChangePasswordRequest): Promise<ChangePasswordResponse> {
    return apiClient.post<ChangePasswordResponse>(
      "/settings/change-password",
      data,
    );
  },
};
