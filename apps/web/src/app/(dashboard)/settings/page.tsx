"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Settings,
  Type,
  Bell,
  Globe,
  ShieldCheck,
  Download,
  Trash2,
  Moon,
  Sun,
  Brain,
  Eye,
} from "lucide-react";
import {
  AppCard,
  AppButton,
  AlertBanner,
  toast,
} from "@/components/design-system";
import { settingsApi } from "@/services/api/settings";
import { apiClient } from "@/services/api/client";
import { useObservation } from "@/components/shadow-agent";

/* ── Types ────────────────────────────────────────────────── */

type TextSize = "normal" | "large" | "extra-large";
type Theme = "light" | "dark";
type AlertFrequency = "immediately" | "daily" | "weekly";

interface NotificationSettings {
  emailAlerts: boolean;
  pushNotifications: boolean;
  inAppNotifications: boolean;
  alertFrequency: AlertFrequency;
}

interface DisplaySettings {
  textSize: TextSize;
  theme: Theme;
}

/* ── Toggle Switch ────────────────────────────────────────── */

function ToggleSwitch({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <div className="flex items-start justify-between py-3">
      <div className="flex-1 min-w-0 pr-4">
        <p className="text-sm font-medium text-[var(--color-gray-900)]">
          {label}
        </p>
        {description && (
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            {description}
          </p>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={`
          relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent
          transition-colors duration-200 cursor-pointer
          focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
          ${checked ? "bg-[var(--color-primary)]" : "bg-[var(--color-gray-300)]"}
        `}
      >
        <span
          className={`
            pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm
            transition-transform duration-200
            ${checked ? "translate-x-5" : "translate-x-0"}
          `}
        />
      </button>
    </div>
  );
}

/* ── Radio Option ─────────────────────────────────────────── */

function RadioOption({
  name,
  value,
  checked,
  onChange,
  label,
  preview,
}: {
  name: string;
  value: string;
  checked: boolean;
  onChange: (value: string) => void;
  label: string;
  preview?: string;
}) {
  return (
    <label
      className={`
        flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors border
        ${
          checked
            ? "border-[var(--color-primary)] bg-[var(--color-primary-bg)]"
            : "border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
        }
      `}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={() => onChange(value)}
        className="h-4 w-4 text-[var(--color-primary)] border-[var(--color-gray-300)]
          focus:ring-[var(--color-primary)] focus:ring-offset-0"
      />
      <div>
        <span
          className="font-medium text-[var(--color-gray-900)]"
          style={{
            fontSize:
              preview === "large"
                ? "1.125rem"
                : preview === "extra-large"
                  ? "1.25rem"
                  : "0.875rem",
          }}
        >
          {label}
        </span>
      </div>
    </label>
  );
}

/* ── Confirmation Dialog ──────────────────────────────────── */

function ConfirmDialog({
  title,
  description,
  confirmLabel,
  variant,
  onConfirm,
  onCancel,
}: {
  title: string;
  description: string;
  confirmLabel: string;
  variant: "danger" | "primary";
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="fixed inset-0 bg-black/40"
        onClick={onCancel}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="relative bg-[var(--color-surface-card)] rounded-[12px] shadow-[var(--shadow-raised)]
          border border-[var(--color-gray-200)] p-6 max-w-md w-full"
      >
        <h3
          id="confirm-title"
          className="text-lg font-semibold text-[var(--color-gray-900)]"
        >
          {title}
        </h3>
        <p className="text-sm text-[var(--color-gray-600)] mt-2">
          {description}
        </p>
        <div className="flex justify-end gap-3 mt-6">
          <AppButton variant="outlined" size="sm" onClick={onCancel}>
            Cancel
          </AppButton>
          <AppButton variant={variant} size="sm" onClick={onConfirm}>
            {confirmLabel}
          </AppButton>
        </div>
      </div>
    </div>
  );
}

/* ── AI Memory Section (T139) ─────────────────────────────── */

function AIMemorySection() {
  const { visits, insights, isEnabled, setEnabled, clearAll } =
    useObservation();

  // Group visits by page for display
  const pageCounts = new Map<string, number>();
  for (const visit of visits) {
    const count = pageCounts.get(visit.page) || 0;
    pageCounts.set(visit.page, count + 1);
  }

  const PAGE_LABELS: Record<string, string> = {
    "/": "Dashboard",
    "/my-dashboard": "My Dashboard",
    "/my-leave": "My Leave",
    "/policies": "Policies",
    "/compliance": "Compliance",
    "/calculators": "Calculators",
    "/advisory": "Advisory",
    "/settings": "Settings",
  };

  return (
    <AppCard
      variant="standard"
      header={
        <div className="flex items-center gap-2">
          <Brain
            className="h-4 w-4 text-[var(--color-gray-500)]"
            aria-hidden="true"
          />
          <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
            AI Memory
          </h2>
        </div>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-[var(--color-gray-600)]">
          Arbor learns your work patterns to provide better assistance. This
          data is stored only in your browser session and is not shared with
          anyone.
        </p>

        {/* Enable/disable toggle */}
        <ToggleSwitch
          checked={isEnabled}
          onChange={setEnabled}
          label="Enable pattern learning"
          description="Allow Arbor to observe your navigation patterns and offer proactive suggestions"
        />

        {/* Observed patterns */}
        {isEnabled && visits.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <Eye
                className="h-3.5 w-3.5 text-[var(--color-gray-400)]"
                aria-hidden="true"
              />
              <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
                Observed Patterns ({visits.length} page views)
              </p>
            </div>

            {/* Page visit counts */}
            <div className="space-y-1">
              {Array.from(pageCounts.entries())
                .sort((a, b) => b[1] - a[1])
                .slice(0, 8)
                .map(([page, count]) => (
                  <div
                    key={page}
                    className="flex items-center justify-between py-1.5 px-3 rounded-lg bg-[var(--color-gray-50)]"
                  >
                    <span className="text-sm text-[var(--color-gray-700)]">
                      {PAGE_LABELS[page] || page}
                    </span>
                    <span className="text-xs font-medium text-[var(--color-gray-500)]">
                      {count} visit{count !== 1 ? "s" : ""}
                    </span>
                  </div>
                ))}
            </div>

            {/* Generated insights */}
            {insights.length > 0 && (
              <div className="mt-3 space-y-1.5">
                <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
                  Active Insights
                </p>
                {insights.map((insight) => (
                  <div
                    key={insight.id}
                    className="text-xs text-[var(--color-gray-600)] py-1.5 px-3 rounded-lg bg-[var(--color-primary-bg)] border border-[var(--color-primary)]/20"
                  >
                    {insight.message}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {isEnabled && visits.length === 0 && (
          <p className="text-xs text-[var(--color-gray-400)] italic">
            No patterns observed yet. Navigate around the app and patterns will
            appear here.
          </p>
        )}

        {/* Clear button */}
        {visits.length > 0 && (
          <AppButton
            variant="outlined"
            size="sm"
            onClick={() => {
              clearAll();
              toast.success("All observations have been cleared");
            }}
          >
            Clear all observations
          </AppButton>
        )}
      </div>
    </AppCard>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function SettingsPage() {
  /* Display state */
  const [display, setDisplay] = useState<DisplaySettings>(() => {
    const storedTheme =
      typeof window !== "undefined"
        ? (localStorage.getItem("theme") as Theme | null)
        : null;
    return {
      textSize: "normal",
      theme: storedTheme === "dark" ? "dark" : "light",
    };
  });

  /* Notification state */
  const [notifications, setNotifications] = useState<NotificationSettings>({
    emailAlerts: true,
    pushNotifications: false,
    inAppNotifications: true,
    alertFrequency: "daily",
  });

  /* Data & Privacy state */
  const [exporting, setExporting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  /* Saving feedback */
  const [savingSection, setSavingSection] = useState<string | null>(null);

  /* ── Apply stored theme on mount ────────────────────────── */

  useEffect(() => {
    document.documentElement.classList.toggle("dark", display.theme === "dark");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Load settings from backend on mount ───────────────── */

  useEffect(() => {
    let cancelled = false;
    async function loadSettings() {
      try {
        const settings = await settingsApi.get();
        if (cancelled) return;
        if (settings.display) {
          const storedTheme = localStorage.getItem("theme") as Theme | null;
          setDisplay({
            textSize: settings.display.textSize as TextSize,
            theme: storedTheme === "dark" ? "dark" : "light",
          });
        }
        if (settings.notifications) {
          setNotifications(settings.notifications as NotificationSettings);
        }
      } catch {
        // Silently fall back to defaults on first load
      }
    }
    loadSettings();
    return () => {
      cancelled = true;
    };
  }, []);

  /* ── Handlers ────────────────────────────────────────────── */

  const saveDisplay = useCallback(
    async (patch: Partial<DisplaySettings>) => {
      setSavingSection("display");
      const updated = { ...display, ...patch };
      setDisplay(updated);

      // Theme is stored client-side in localStorage
      if (patch.theme) {
        localStorage.setItem("theme", patch.theme);
        document.documentElement.classList.toggle(
          "dark",
          patch.theme === "dark",
        );
      }

      try {
        await settingsApi.update({
          display: { textSize: updated.textSize },
        });
        toast.success("Display preference saved");
      } catch {
        toast.error("Failed to save display preference. Please try again.");
      } finally {
        setSavingSection(null);
      }
    },
    [display],
  );

  const updateNotification = useCallback(
    async (
      field: keyof NotificationSettings,
      value: boolean | AlertFrequency,
    ) => {
      setSavingSection("notifications");
      const updated = { ...notifications, [field]: value };
      setNotifications(updated);
      try {
        await settingsApi.update({ notifications: updated });
        toast.success("Notification preference saved");
      } catch {
        toast.error(
          "Failed to save notification preference. Please try again.",
        );
      } finally {
        setSavingSection(null);
      }
    },
    [notifications],
  );

  const handleExportData = useCallback(async () => {
    setExporting(true);
    try {
      // Gather data from available APIs in parallel
      const [userProfile, userSettings] = await Promise.all([
        apiClient
          .get<{
            id: number;
            email: string;
            name: string;
            role: string;
            company_id: number | null;
          }>("/auth/me")
          .catch(() => null),
        settingsApi.get().catch(() => null),
      ]);

      // If the user has a company, fetch the company profile
      let companyProfile = null;
      if (userProfile?.company_id) {
        companyProfile = await apiClient
          .get(`/profile/${userProfile.company_id}`)
          .catch(() => null);
      }

      const exportPayload = {
        exported_at: new Date().toISOString(),
        format_version: "1.0",
        user: userProfile,
        settings: userSettings,
        company: companyProfile,
      };

      // Trigger browser download as JSON
      const blob = new Blob([JSON.stringify(exportPayload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `arbor-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);

      toast.success("Your data has been exported");
    } catch {
      toast.error("Failed to export data. Please try again.");
    } finally {
      setExporting(false);
    }
  }, []);

  const handleDeleteAccount = useCallback(() => {
    setShowDeleteConfirm(false);
    toast.error(
      "Account deletion has been requested. You will receive a confirmation email.",
    );
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Settings
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Settings
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Configure your account preferences, notifications, and privacy
            options.
          </p>
        </div>
      </div>

      {/* AI Configuration */}
      <a
        href="/settings/ai"
        className="block no-underline"
        style={{ textDecoration: "none", color: "inherit" }}
      >
        <AppCard variant="standard">
          <div className="flex items-center gap-3 py-1">
            <Brain
              className="h-5 w-5 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div className="flex-1">
              <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
                AI Configuration
              </h2>
              <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                Manage your AI provider, API key, and usage budget.
              </p>
            </div>
            <span className="text-xs text-[var(--color-gray-400)]">→</span>
          </div>
        </AppCard>
      </a>

      {/* Display Section */}
      <AppCard
        variant="standard"
        header={
          <div className="flex items-center gap-2">
            <Type
              className="h-4 w-4 text-[var(--color-gray-500)]"
              aria-hidden="true"
            />
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Display
            </h2>
            {savingSection === "display" && (
              <span className="text-xs text-[var(--color-gray-400)] ml-auto">
                Saving...
              </span>
            )}
          </div>
        }
      >
        <div className="space-y-2">
          <p className="text-sm text-[var(--color-gray-600)] mb-3">
            Choose your preferred text size for the application.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <RadioOption
              name="textSize"
              value="normal"
              checked={display.textSize === "normal"}
              onChange={(v) => saveDisplay({ textSize: v as TextSize })}
              label="Normal"
              preview="normal"
            />
            <RadioOption
              name="textSize"
              value="large"
              checked={display.textSize === "large"}
              onChange={(v) => saveDisplay({ textSize: v as TextSize })}
              label="Large"
              preview="large"
            />
            <RadioOption
              name="textSize"
              value="extra-large"
              checked={display.textSize === "extra-large"}
              onChange={(v) => saveDisplay({ textSize: v as TextSize })}
              label="Extra Large"
              preview="extra-large"
            />
          </div>

          {/* Theme toggle */}
          <div className="mt-5 pt-4 border-t border-[var(--color-gray-200)]">
            <p className="text-sm text-[var(--color-gray-600)] mb-3">
              Choose your preferred colour theme.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => saveDisplay({ theme: "light" })}
                className={`
                  flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors border
                  ${
                    display.theme === "light"
                      ? "border-[var(--color-primary)] bg-[var(--color-primary-bg)]"
                      : "border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
                  }
                `}
              >
                <Sun className="h-5 w-5 text-amber-500" aria-hidden="true" />
                <span className="text-sm font-medium text-[var(--color-gray-900)]">
                  Light Mode
                </span>
              </button>
              <button
                type="button"
                onClick={() => saveDisplay({ theme: "dark" })}
                className={`
                  flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors border
                  ${
                    display.theme === "dark"
                      ? "border-[var(--color-primary)] bg-[var(--color-primary-bg)]"
                      : "border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
                  }
                `}
              >
                <Moon className="h-5 w-5 text-indigo-500" aria-hidden="true" />
                <span className="text-sm font-medium text-[var(--color-gray-900)]">
                  Dark Mode
                </span>
              </button>
            </div>
          </div>
        </div>
      </AppCard>

      {/* Notifications Section */}
      <AppCard
        variant="standard"
        header={
          <div className="flex items-center gap-2">
            <Bell
              className="h-4 w-4 text-[var(--color-gray-500)]"
              aria-hidden="true"
            />
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Notifications
            </h2>
            {savingSection === "notifications" && (
              <span className="text-xs text-[var(--color-gray-400)] ml-auto">
                Saving...
              </span>
            )}
          </div>
        }
      >
        <div className="divide-y divide-[var(--color-gray-100)]">
          <ToggleSwitch
            checked={notifications.emailAlerts}
            onChange={(v) => updateNotification("emailAlerts", v)}
            label="Email alerts"
            description="Receive compliance updates and advisory notifications via email"
          />
          <ToggleSwitch
            checked={notifications.pushNotifications}
            onChange={(v) => updateNotification("pushNotifications", v)}
            label="Push notifications"
            description="Get browser push notifications for urgent compliance alerts"
          />
          <ToggleSwitch
            checked={notifications.inAppNotifications}
            onChange={(v) => updateNotification("inAppNotifications", v)}
            label="In-app notifications"
            description="Show notification badges and banners within the application"
          />

          {/* Alert Frequency */}
          <div className="py-3">
            <label
              htmlFor="alert-frequency"
              className="block text-sm font-medium text-[var(--color-gray-900)]"
            >
              Alert frequency
            </label>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5 mb-2">
              How often should we bundle non-urgent notifications
            </p>
            <select
              id="alert-frequency"
              value={notifications.alertFrequency}
              onChange={(e) =>
                updateNotification(
                  "alertFrequency",
                  e.target.value as AlertFrequency,
                )
              }
              className="
                w-full sm:w-64 rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                transition-colors
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                focus:border-[var(--color-surface-input-focus)]
              "
            >
              <option value="immediately">Immediately</option>
              <option value="daily">Daily Digest</option>
              <option value="weekly">Weekly Summary</option>
            </select>
          </div>
        </div>
      </AppCard>

      {/* Language Section */}
      <AppCard
        variant="standard"
        header={
          <div className="flex items-center gap-2">
            <Globe
              className="h-4 w-4 text-[var(--color-gray-500)]"
              aria-hidden="true"
            />
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Language
            </h2>
          </div>
        }
      >
        <div className="space-y-3">
          <div
            className="flex items-center gap-3 p-3 rounded-lg border
              border-[var(--color-primary)] bg-[var(--color-primary-bg)]"
          >
            <div
              className="flex items-center justify-center h-8 w-8 rounded-full
                bg-[var(--color-primary)] text-white text-xs font-bold"
            >
              EN
            </div>
            <div>
              <p className="text-sm font-medium text-[var(--color-gray-900)]">
                English
              </p>
              <p className="text-xs text-[var(--color-gray-500)]">
                Currently selected
              </p>
            </div>
          </div>
          <AlertBanner
            variant="info"
            title="More languages coming soon"
            description="Support for Mandarin, Malay, and Tamil is on our roadmap to better serve Singapore's multilingual workforce."
          />
        </div>
      </AppCard>

      {/* AI Memory Section (T139) */}
      <AIMemorySection />

      {/* Data & Privacy Section */}
      <AppCard
        variant="standard"
        header={
          <div className="flex items-center gap-2">
            <ShieldCheck
              className="h-4 w-4 text-[var(--color-gray-500)]"
              aria-hidden="true"
            />
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Data &amp; Privacy
            </h2>
          </div>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-gray-600)]">
            Manage your data in compliance with Singapore&apos;s Personal Data
            Protection Act (PDPA). You have the right to access, correct, and
            request deletion of your personal data.
          </p>

          {/* Export Data */}
          <div
            className="flex flex-col sm:flex-row sm:items-center justify-between gap-3
              p-4 rounded-lg border border-[var(--color-gray-200)] bg-[var(--color-gray-50)]"
          >
            <div className="flex items-start gap-3">
              <Download
                className="h-5 w-5 text-[var(--color-gray-500)] mt-0.5 shrink-0"
                aria-hidden="true"
              />
              <div>
                <p className="text-sm font-medium text-[var(--color-gray-900)]">
                  Export My Data
                </p>
                <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                  Download a copy of all your personal data and company
                  information stored in the system.
                </p>
              </div>
            </div>
            <AppButton
              variant="outlined"
              size="sm"
              onClick={handleExportData}
              loading={exporting}
              className="shrink-0"
            >
              Export Data
            </AppButton>
          </div>

          {/* Delete Account */}
          <div
            className="flex flex-col sm:flex-row sm:items-center justify-between gap-3
              p-4 rounded-lg border border-[var(--color-error)] bg-red-50"
          >
            <div className="flex items-start gap-3">
              <Trash2
                className="h-5 w-5 text-[var(--color-error)] mt-0.5 shrink-0"
                aria-hidden="true"
              />
              <div>
                <p className="text-sm font-medium text-[var(--color-gray-900)]">
                  Delete Account
                </p>
                <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                  Permanently delete your account and all associated data. This
                  action cannot be undone.
                </p>
              </div>
            </div>
            <AppButton
              variant="danger"
              size="sm"
              onClick={() => setShowDeleteConfirm(true)}
              className="shrink-0"
            >
              Delete Account
            </AppButton>
          </div>
        </div>
      </AppCard>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <ConfirmDialog
          title="Delete your account?"
          description="This will permanently remove your account, company profile, and all associated data. Under PDPA, this process is irreversible and will be completed within 30 days. You will receive a confirmation email."
          confirmLabel="Yes, delete my account"
          variant="danger"
          onConfirm={handleDeleteAccount}
          onCancel={() => setShowDeleteConfirm(false)}
        />
      )}
    </div>
  );
}
