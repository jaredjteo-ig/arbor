"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Bell,
  ChevronDown,
  ChevronUp,
  Calendar,
  List,
  Eye,
  EyeOff,
  Calculator,
  MessageSquare,
  FileText,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { AppCard, AppButton } from "@/components/design-system";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  useAlerts,
  useMarkAlertRead,
  useDismissAlert,
} from "@/hooks/api/useAlerts";
import type { Alert, AlertSeverity, AlertStatus } from "@/types/api";

/* ── Constants ───────────────────────────────────────────── */

type TabFilter = "all" | "affecting" | "upcoming";
type ViewMode = "list" | "calendar";

const SEVERITY_ORDER: AlertSeverity[] = ["critical", "high", "medium", "low"];

const SEVERITY_STYLES: Record<
  AlertSeverity,
  { bg: string; text: string; dot: string; label: string }
> = {
  critical: {
    bg: "bg-red-50",
    text: "text-red-700",
    dot: "bg-red-500",
    label: "Critical",
  },
  high: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    dot: "bg-amber-500",
    label: "High",
  },
  medium: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    dot: "bg-blue-500",
    label: "Medium",
  },
  low: {
    bg: "bg-gray-50",
    text: "text-gray-600",
    dot: "bg-gray-400",
    label: "Low",
  },
};

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/* ── Helper functions ────────────────────────────────────── */

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function isThisMonth(iso: string): boolean {
  const d = new Date(iso);
  const now = new Date();
  return (
    d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
  );
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay();
}

/* ── Loading skeleton ────────────────────────────────────── */

function AlertsSkeleton() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-7 w-7 rounded bg-[var(--color-gray-200)] animate-pulse" />
        <div className="space-y-2">
          <div className="h-6 w-48 rounded bg-[var(--color-gray-200)] animate-pulse" />
          <div className="h-4 w-72 rounded bg-[var(--color-gray-200)] animate-pulse" />
        </div>
      </div>
      <div className="flex gap-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-8 w-24 rounded-full bg-[var(--color-gray-200)] animate-pulse"
          />
        ))}
      </div>
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="h-24 rounded-xl bg-[var(--color-gray-200)] animate-pulse"
        />
      ))}
    </div>
  );
}

/* ── Page component ──────────────────────────────────────── */

export default function AlertsPage() {
  const { data, isPending, error } = useAlerts();
  const markReadMutation = useMarkAlertRead();
  const dismissMutation = useDismissAlert();

  const [activeTab, setActiveTab] = useState<TabFilter>("all");
  const [severityFilter, setSeverityFilter] = useState<AlertSeverity | "all">(
    "all",
  );
  const [statusFilter, setStatusFilter] = useState<AlertStatus | "all">("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [calendarMonth, setCalendarMonth] = useState(2); // March (0-indexed)
  const [calendarYear, setCalendarYear] = useState(2026);

  const alerts = data?.alerts ?? [];

  /* ── Derived state ─────────────────────────────────────── */

  const filtered = useMemo(() => {
    let results = [...alerts];

    // Tab filter
    if (activeTab === "affecting") {
      results = results.filter(
        (a) => a.severity === "critical" || a.severity === "high",
      );
    } else if (activeTab === "upcoming") {
      const now = new Date();
      results = results.filter((a) => new Date(a.effective_date) >= now);
    }

    // Severity filter
    if (severityFilter !== "all") {
      results = results.filter((a) => a.severity === severityFilter);
    }

    // Status filter
    if (statusFilter !== "all") {
      results = results.filter((a) => a.status === statusFilter);
    }

    // Sort by date, most recent first
    results.sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );

    return results;
  }, [alerts, activeTab, severityFilter, statusFilter]);

  const unreadCount = alerts.filter((a) => a.status === "unread").length;
  const criticalCount = alerts.filter((a) => a.severity === "critical").length;
  const thisMonthCount = alerts.filter((a) => isThisMonth(a.created_at)).length;

  /* ── Actions ───────────────────────────────────────────── */

  function markAsRead(id: string) {
    markReadMutation.mutate(id);
  }

  function dismissAlert(id: string) {
    dismissMutation.mutate(id);
  }

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
    const alert = alerts.find((a) => a.id === id);
    if (alert && alert.status === "unread") {
      markAsRead(id);
    }
  }

  /* ── Calendar helpers ──────────────────────────────────── */

  const calendarAlerts = useMemo(() => {
    const map = new Map<number, Alert[]>();
    for (const a of alerts) {
      const d = new Date(a.effective_date);
      if (d.getMonth() === calendarMonth && d.getFullYear() === calendarYear) {
        const day = d.getDate();
        if (!map.has(day)) map.set(day, []);
        map.get(day)!.push(a);
      }
    }
    return map;
  }, [alerts, calendarMonth, calendarYear]);

  function prevMonth() {
    if (calendarMonth === 0) {
      setCalendarMonth(11);
      setCalendarYear((y) => y - 1);
    } else {
      setCalendarMonth((m) => m - 1);
    }
  }

  function nextMonth() {
    if (calendarMonth === 11) {
      setCalendarMonth(0);
      setCalendarYear((y) => y + 1);
    } else {
      setCalendarMonth((m) => m + 1);
    }
  }

  /* ── Loading / Error states ────────────────────────────── */

  if (isPending)
    return (
      <AdminGuard>
        <AlertsSkeleton />
      </AdminGuard>
    );

  if (error) {
    return (
      <AdminGuard>
        <div className="max-w-4xl mx-auto">
          <AppCard variant="standard">
            <div className="text-center py-8">
              <AlertCircle className="h-10 w-10 text-red-400 mx-auto mb-3" />
              <p className="text-[var(--color-gray-700)] font-medium">
                Unable to load alerts
              </p>
              <p className="text-sm text-[var(--color-gray-500)] mt-1">
                {error.message}
              </p>
            </div>
          </AppCard>
        </div>
      </AdminGuard>
    );
  }

  /* ── Render ────────────────────────────────────────────── */

  return (
    <AdminGuard>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Bell
                className="h-7 w-7 text-[var(--color-primary)]"
                aria-hidden="true"
              />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Regulatory Alerts
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Stay updated on regulatory changes affecting your company.
              </p>
            </div>
          </div>

          {/* View toggle */}
          <div className="flex items-center gap-1 bg-[var(--color-gray-100)] rounded-lg p-1">
            <button
              onClick={() => setViewMode("list")}
              className={`p-2 rounded-md transition-colors ${
                viewMode === "list"
                  ? "bg-white text-[var(--color-gray-900)] shadow-sm"
                  : "text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"
              }`}
              aria-label="List view"
            >
              <List className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode("calendar")}
              className={`p-2 rounded-md transition-colors ${
                viewMode === "calendar"
                  ? "bg-white text-[var(--color-gray-900)] shadow-sm"
                  : "text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"
              }`}
              aria-label="Calendar view"
            >
              <Calendar className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Summary pills */}
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <span className="h-2 w-2 rounded-full bg-blue-500" />
            {unreadCount} unread
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-red-50 text-red-700 border border-red-200">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            {criticalCount} critical
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-700)] border border-[var(--color-gray-200)]">
            <Calendar className="h-3.5 w-3.5" />
            {thisMonthCount} this month
          </span>
        </div>

        {/* Filter bar */}
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Tabs */}
          <div className="flex gap-2 overflow-x-auto pb-1">
            {(
              [
                { key: "all", label: "All" },
                { key: "affecting", label: "Affecting Your Company" },
                { key: "upcoming", label: "Upcoming Changes" },
              ] as const
            ).map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.key
                    ? "bg-[var(--color-primary)] text-white"
                    : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:bg-[var(--color-gray-200)]"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Severity + status filters */}
          <div className="flex gap-2 sm:ml-auto">
            <select
              value={severityFilter}
              onChange={(e) =>
                setSeverityFilter(e.target.value as AlertSeverity | "all")
              }
              className="px-3 py-1.5 text-sm rounded-lg border border-[var(--color-gray-200)] bg-white text-[var(--color-gray-700)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            >
              <option value="all">All Severity</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as AlertStatus | "all")
              }
              className="px-3 py-1.5 text-sm rounded-lg border border-[var(--color-gray-200)] bg-white text-[var(--color-gray-700)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            >
              <option value="all">All Status</option>
              <option value="unread">Unread</option>
              <option value="read">Read</option>
            </select>
          </div>
        </div>

        {/* List view */}
        {viewMode === "list" && (
          <>
            {filtered.length === 0 ? (
              <AppCard variant="standard">
                <div className="text-center py-8">
                  <Bell className="h-10 w-10 text-[var(--color-gray-300)] mx-auto mb-3" />
                  <p className="text-[var(--color-gray-500)]">
                    No alerts match your current filters. Try adjusting your
                    selection.
                  </p>
                </div>
              </AppCard>
            ) : (
              <div className="space-y-3">
                {filtered.map((alert) => (
                  <AlertListItem
                    key={alert.id}
                    alert={alert}
                    isExpanded={expandedId === alert.id}
                    onToggle={() => toggleExpand(alert.id)}
                    onMarkRead={() => markAsRead(alert.id)}
                    onDismiss={() => dismissAlert(alert.id)}
                  />
                ))}
              </div>
            )}

            <p className="text-xs text-[var(--color-gray-400)] text-center">
              Showing {filtered.length} of {alerts.length} alerts
            </p>
          </>
        )}

        {/* Calendar view */}
        {viewMode === "calendar" && (
          <CalendarView
            year={calendarYear}
            month={calendarMonth}
            alertsByDay={calendarAlerts}
            onPrevMonth={prevMonth}
            onNextMonth={nextMonth}
            onSelectAlert={(id) => {
              setViewMode("list");
              setExpandedId(id);
              const alert = alerts.find((a) => a.id === id);
              if (alert && alert.status === "unread") {
                markAsRead(id);
              }
            }}
          />
        )}
      </div>
    </AdminGuard>
  );
}

/* ── Alert list item ─────────────────────────────────────── */

function AlertListItem({
  alert,
  isExpanded,
  onToggle,
  onMarkRead,
  onDismiss,
}: {
  alert: Alert;
  isExpanded: boolean;
  onToggle: () => void;
  onMarkRead: () => void;
  onDismiss: () => void;
}) {
  const router = useRouter();
  const style = SEVERITY_STYLES[alert.severity];

  return (
    <AppCard
      variant={isExpanded ? "elevated" : "standard"}
      className="transition-shadow"
    >
      {/* Collapsed header */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] rounded-lg"
        aria-expanded={isExpanded}
      >
        <div className="flex items-start gap-3">
          {/* Unread dot */}
          <div className="pt-1.5 shrink-0">
            {alert.status === "unread" ? (
              <span
                className="block h-2.5 w-2.5 rounded-full bg-[var(--color-primary)]"
                title="Unread"
              />
            ) : (
              <span className="block h-2.5 w-2.5" />
            )}
          </div>

          {/* Severity badge */}
          <span
            className={`shrink-0 px-2 py-0.5 rounded text-xs font-semibold uppercase ${style.bg} ${style.text}`}
          >
            {style.label}
          </span>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <h3
              className={`text-sm leading-snug ${
                alert.status === "unread"
                  ? "font-semibold text-[var(--color-gray-900)]"
                  : "font-medium text-[var(--color-gray-700)]"
              }`}
            >
              {alert.title}
            </h3>
            {!isExpanded && (
              <p className="text-xs text-[var(--color-gray-500)] mt-1 line-clamp-1">
                {alert.description}
              </p>
            )}
            <div className="flex items-center gap-3 mt-1.5">
              <span className="text-xs text-[var(--color-gray-400)]">
                {formatDate(alert.created_at)}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-gray-100)] text-[var(--color-gray-500)]">
                {alert.domain}
              </span>
            </div>
          </div>

          {/* Expand chevron */}
          <div className="shrink-0 pt-0.5">
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-[var(--color-gray-400)]" />
            ) : (
              <ChevronDown className="h-4 w-4 text-[var(--color-gray-400)]" />
            )}
          </div>
        </div>
      </button>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-[var(--color-gray-200)]">
          {/* Full description */}
          <p className="text-sm text-[var(--color-gray-700)] leading-relaxed">
            {alert.description}
          </p>

          {/* Impact summary */}
          {alert.impact_summary && (
            <div className="mt-4 p-3 rounded-lg bg-amber-50 border border-amber-200">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-700 mb-1">
                How this affects your company
              </h4>
              <p className="text-sm text-amber-900 leading-relaxed">
                {alert.impact_summary}
              </p>
            </div>
          )}

          {/* Action items */}
          {alert.actions && alert.actions.length > 0 && (
            <div className="mt-4">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-gray-500)] mb-2">
                What you need to do
              </h4>
              <ol className="space-y-2">
                {alert.actions.map((action, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className="shrink-0 h-5 w-5 rounded-full bg-[var(--color-primary-bg)] text-[var(--color-primary)] text-xs font-semibold flex items-center justify-center mt-0.5">
                      {i + 1}
                    </span>
                    <span className="text-sm text-[var(--color-gray-700)]">
                      {action}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Effective date */}
          {alert.effective_date && (
            <div className="mt-4 flex items-center gap-2">
              <Calendar className="h-4 w-4 text-[var(--color-gray-400)]" />
              <span className="text-sm text-[var(--color-gray-600)]">
                Effective: {formatDate(alert.effective_date)}
              </span>
            </div>
          )}

          {/* CTAs */}
          <div className="mt-4 flex flex-wrap gap-2">
            <AppButton
              size="sm"
              variant="outlined"
              onClick={(e) => {
                e.stopPropagation();
                const calcPath = alert.domain.toLowerCase().includes("cpf")
                  ? "/calculators/cpf"
                  : "/calculators";
                router.push(calcPath);
              }}
            >
              <Calculator className="h-4 w-4" />
              Update Calculator
            </AppButton>
            <AppButton
              size="sm"
              variant="outlined"
              onClick={(e) => {
                e.stopPropagation();
                const query = encodeURIComponent(alert.title);
                router.push(`/advisory?query=${query}`);
              }}
            >
              <MessageSquare className="h-4 w-4" />
              Ask About This
            </AppButton>
            <AppButton
              size="sm"
              variant="outlined"
              onClick={(e) => {
                e.stopPropagation();
                router.push("/documents");
              }}
            >
              <FileText className="h-4 w-4" />
              Generate Updated Policy
            </AppButton>
          </div>

          {/* Status actions */}
          <div className="mt-4 pt-3 border-t border-[var(--color-gray-100)] flex items-center gap-2">
            {alert.status !== "read" && (
              <AppButton
                size="sm"
                variant="text"
                onClick={(e) => {
                  e.stopPropagation();
                  onMarkRead();
                }}
              >
                <Eye className="h-4 w-4" />
                Mark as read
              </AppButton>
            )}
            {alert.status !== "dismissed" && (
              <AppButton
                size="sm"
                variant="text"
                onClick={(e) => {
                  e.stopPropagation();
                  onDismiss();
                }}
              >
                <EyeOff className="h-4 w-4" />
                Dismiss
              </AppButton>
            )}
            {alert.status === "dismissed" && (
              <span className="text-xs text-[var(--color-gray-400)] italic">
                This alert has been dismissed.
              </span>
            )}
          </div>
        </div>
      )}
    </AppCard>
  );
}

/* ── Calendar view ───────────────────────────────────────── */

function CalendarView({
  year,
  month,
  alertsByDay,
  onPrevMonth,
  onNextMonth,
  onSelectAlert,
}: {
  year: number;
  month: number;
  alertsByDay: Map<number, Alert[]>;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  onSelectAlert: (id: string) => void;
}) {
  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfMonth(year, month);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const selectedAlerts = selectedDay
    ? (alertsByDay.get(selectedDay) ?? [])
    : [];

  // Build grid cells: leading blanks + day numbers
  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  return (
    <div className="space-y-4">
      <AppCard variant="standard">
        {/* Month navigation */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={onPrevMonth}
            className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors text-[var(--color-gray-600)]"
            aria-label="Previous month"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <h3 className="text-lg font-semibold text-[var(--color-gray-900)]">
            {MONTHS[month]} {year}
          </h3>
          <button
            onClick={onNextMonth}
            className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors text-[var(--color-gray-600)]"
            aria-label="Next month"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>

        {/* Weekday headers */}
        <div className="grid grid-cols-7 gap-1 mb-1">
          {WEEKDAYS.map((day) => (
            <div
              key={day}
              className="text-center text-xs font-medium text-[var(--color-gray-400)] py-1"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Day cells */}
        <div className="grid grid-cols-7 gap-1">
          {cells.map((day, i) => {
            if (day === null) {
              return <div key={`blank-${i}`} className="aspect-square" />;
            }
            const dayAlerts = alertsByDay.get(day) ?? [];
            const hasAlerts = dayAlerts.length > 0;
            const isSelected = selectedDay === day;

            return (
              <button
                key={day}
                type="button"
                onClick={() => setSelectedDay(isSelected ? null : day)}
                className={`aspect-square rounded-lg flex flex-col items-center justify-center gap-0.5 text-sm transition-colors relative ${
                  isSelected
                    ? "bg-[var(--color-primary)] text-white"
                    : hasAlerts
                      ? "bg-[var(--color-gray-50)] hover:bg-[var(--color-gray-100)] text-[var(--color-gray-900)] font-medium"
                      : "text-[var(--color-gray-600)] hover:bg-[var(--color-gray-50)]"
                }`}
                aria-label={`${day} ${MONTHS[month]} ${year}${hasAlerts ? `, ${dayAlerts.length} alert${dayAlerts.length > 1 ? "s" : ""}` : ""}`}
              >
                <span>{day}</span>
                {hasAlerts && (
                  <div className="flex gap-0.5">
                    {dayAlerts.map((a) => (
                      <span
                        key={a.id}
                        className={`h-1.5 w-1.5 rounded-full ${
                          isSelected
                            ? "bg-white/80"
                            : SEVERITY_STYLES[a.severity].dot
                        }`}
                      />
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {/* Legend */}
        <div className="mt-4 pt-3 border-t border-[var(--color-gray-100)] flex flex-wrap gap-4">
          {SEVERITY_ORDER.map((sev) => (
            <div key={sev} className="flex items-center gap-1.5">
              <span
                className={`h-2 w-2 rounded-full ${SEVERITY_STYLES[sev].dot}`}
              />
              <span className="text-xs text-[var(--color-gray-500)]">
                {SEVERITY_STYLES[sev].label}
              </span>
            </div>
          ))}
        </div>
      </AppCard>

      {/* Selected day detail */}
      {selectedDay !== null && selectedAlerts.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-[var(--color-gray-700)]">
            Alerts effective {selectedDay} {MONTHS[month]} {year}
          </h4>
          {selectedAlerts.map((alert) => {
            const style = SEVERITY_STYLES[alert.severity];
            return (
              <AppCard key={alert.id} variant="standard">
                <div className="flex items-start gap-3">
                  <span
                    className={`shrink-0 px-2 py-0.5 rounded text-xs font-semibold uppercase ${style.bg} ${style.text}`}
                  >
                    {style.label}
                  </span>
                  <div className="flex-1 min-w-0">
                    <h5 className="text-sm font-medium text-[var(--color-gray-900)]">
                      {alert.title}
                    </h5>
                    <p className="text-xs text-[var(--color-gray-500)] mt-1 line-clamp-2">
                      {alert.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-gray-100)] text-[var(--color-gray-500)]">
                        {alert.domain}
                      </span>
                      <AppButton
                        size="sm"
                        variant="text"
                        onClick={() => onSelectAlert(alert.id)}
                      >
                        View details
                      </AppButton>
                    </div>
                  </div>
                </div>
              </AppCard>
            );
          })}
        </div>
      )}

      {selectedDay !== null && selectedAlerts.length === 0 && (
        <p className="text-sm text-[var(--color-gray-500)] text-center py-4">
          No alerts effective on {selectedDay} {MONTHS[month]} {year}.
        </p>
      )}
    </div>
  );
}
