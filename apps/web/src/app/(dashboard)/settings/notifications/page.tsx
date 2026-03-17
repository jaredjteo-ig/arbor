"use client";

import { useState, useCallback, useEffect } from "react";
import { Bell, Send, Phone } from "lucide-react";
import {
  AppCard,
  AppButton,
  LoadingState,
  ErrorState,
  toast,
} from "@/components/design-system";
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
  useTestNotification,
} from "@/hooks/api";
import type {
  NotificationChannel,
  NotificationPreference,
} from "@/services/api/integrations";

/* ── Channel Labels ──────────────────────────────────────── */

const CHANNEL_CONFIG: Record<
  NotificationChannel,
  { label: string; needsPhone: boolean }
> = {
  email: { label: "Email", needsPhone: false },
  whatsapp: { label: "WhatsApp", needsPhone: true },
  telegram: { label: "Telegram", needsPhone: true },
  slack: { label: "Slack", needsPhone: false },
  teams: { label: "Teams", needsPhone: false },
  sms: { label: "SMS", needsPhone: true },
};

const ALL_CHANNELS: NotificationChannel[] = [
  "email",
  "whatsapp",
  "telegram",
  "slack",
  "teams",
  "sms",
];

/* ── Channel Checkbox ────────────────────────────────────── */

function ChannelCheckbox({
  channel,
  checked,
  onChange,
}: {
  channel: NotificationChannel;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  const config = CHANNEL_CONFIG[channel];
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-[var(--color-gray-300)]
          text-[var(--color-primary)] focus:ring-[var(--color-primary)] focus:ring-offset-0"
      />
      <span className="text-sm text-[var(--color-gray-700)]">
        {config.label}
      </span>
    </label>
  );
}

/* ── Notification Type Row ───────────────────────────────── */

function NotificationTypeRow({
  pref,
  onToggleChannel,
}: {
  pref: NotificationPreference;
  onToggleChannel: (channel: NotificationChannel, enabled: boolean) => void;
}) {
  return (
    <div className="py-4 border-b border-[var(--color-gray-100)] last:border-b-0">
      <div className="mb-3">
        <p className="text-sm font-medium text-[var(--color-gray-900)]">
          {pref.label}
        </p>
        <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
          {pref.description}
        </p>
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-2">
        {ALL_CHANNELS.map((channel) => (
          <ChannelCheckbox
            key={channel}
            channel={channel}
            checked={pref.channels.includes(channel)}
            onChange={(enabled) => onToggleChannel(channel, enabled)}
          />
        ))}
      </div>
    </div>
  );
}

/* ── Test Notification Button ────────────────────────────── */

function TestNotificationButton({ channel }: { channel: NotificationChannel }) {
  const testNotif = useTestNotification();
  const config = CHANNEL_CONFIG[channel];

  const handleTest = async () => {
    try {
      const result = await testNotif.mutateAsync(channel);
      if (result.success) {
        toast.success(`Test ${config.label} notification sent.`);
      } else {
        toast.error(`${config.label} test failed: ${result.message}`);
      }
    } catch {
      toast.error(`Could not send test to ${config.label}.`);
    }
  };

  return (
    <AppButton
      variant="outlined"
      size="sm"
      onClick={handleTest}
      loading={testNotif.isPending}
    >
      <Send className="h-3 w-3" aria-hidden="true" />
      Test {config.label}
    </AppButton>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function NotificationPreferencesPage() {
  const { data, isPending, error, refetch } = useNotificationPreferences();
  const updatePrefs = useUpdateNotificationPreferences();

  const [preferences, setPreferences] = useState<NotificationPreference[]>([]);
  const [phoneNumber, setPhoneNumber] = useState<string>("");
  const [saving, setSaving] = useState(false);

  // Sync server state to local state when data loads
  useEffect(() => {
    if (data) {
      setPreferences(data.preferences);
      setPhoneNumber(data.phone_number ?? "");
    }
  }, [data]);

  const handleToggleChannel = useCallback(
    (prefType: string, channel: NotificationChannel, enabled: boolean) => {
      setPreferences((prev) =>
        prev.map((p) => {
          if (p.type !== prefType) return p;
          const channels = enabled
            ? [...p.channels, channel]
            : p.channels.filter((c) => c !== channel);
          return { ...p, channels };
        }),
      );
    },
    [],
  );

  const handleSave = async () => {
    setSaving(true);
    try {
      await updatePrefs.mutateAsync({
        preferences,
        phone_number: phoneNumber || null,
      });
      toast.success("Notification preferences saved.");
    } catch {
      toast.error("Could not save preferences. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  // Check if any channel needs a phone number
  const phoneRequired = preferences.some((p) =>
    p.channels.some((c) => CHANNEL_CONFIG[c]?.needsPhone),
  );

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Bell
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Notification Preferences
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Choose how and where you receive notifications for each event type.
          </p>
        </div>
      </div>

      {/* Content */}
      {isPending && <LoadingState variant="card" count={4} />}

      {error && (
        <ErrorState
          variant="server"
          title="Could not load notification preferences"
          description="Please try again."
          onRetry={() => refetch()}
        />
      )}

      {data && (
        <>
          {/* Phone number input (for WhatsApp / Telegram / SMS) */}
          {phoneRequired && (
            <AppCard
              variant="standard"
              header={
                <div className="flex items-center gap-2">
                  <Phone
                    className="h-4 w-4 text-[var(--color-gray-500)]"
                    aria-hidden="true"
                  />
                  <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
                    Contact Number
                  </h2>
                </div>
              }
            >
              <p className="text-sm text-[var(--color-gray-600)] mb-3">
                Required for WhatsApp, Telegram, and SMS notifications. Include
                country code (e.g. +65).
              </p>
              <div className="flex flex-col gap-1.5 max-w-sm">
                <label
                  htmlFor="phone-number"
                  className="text-sm font-medium text-[var(--color-gray-700)]"
                >
                  Phone Number
                </label>
                <input
                  id="phone-number"
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+65 8123 4567"
                  className="w-full rounded-[8px] border px-3 py-2 text-base min-h-[44px]
                    bg-[var(--color-surface-input)] text-[var(--foreground)]
                    border-[var(--color-surface-input-border)]
                    placeholder:text-[var(--color-gray-400)]
                    transition-colors
                    focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                    focus:border-[var(--color-surface-input-focus)]"
                />
              </div>
            </AppCard>
          )}

          {/* Notification types */}
          <AppCard
            variant="standard"
            header={
              <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
                Notification Types
              </h2>
            }
          >
            {preferences.map((pref) => (
              <NotificationTypeRow
                key={pref.type}
                pref={pref}
                onToggleChannel={(channel, enabled) =>
                  handleToggleChannel(pref.type, channel, enabled)
                }
              />
            ))}
          </AppCard>

          {/* Save button */}
          <div className="flex items-center justify-between">
            <AppButton
              variant="primary"
              size="md"
              onClick={handleSave}
              loading={saving}
            >
              Save Preferences
            </AppButton>

            {/* Test buttons */}
            <div className="flex flex-wrap gap-2">
              {ALL_CHANNELS.map((channel) => {
                const isUsed = preferences.some((p) =>
                  p.channels.includes(channel),
                );
                if (!isUsed) return null;
                return (
                  <TestNotificationButton key={channel} channel={channel} />
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
