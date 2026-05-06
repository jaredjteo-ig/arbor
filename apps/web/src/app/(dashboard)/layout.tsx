"use client";

import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useState, useEffect } from "react";
import { getLocale } from "@/lib/i18n";
import { useAuth } from "@/contexts/AuthContext";
import {
  ShadowAgentProvider,
  ShadowWidget,
  ShadowMargin,
  CommandSurface,
  ArborHistory,
  useShadowAgent,
  useShadowContext,
  useObservation,
} from "@/components/shadow-agent";

/**
 * Dashboard layout — wraps all authenticated routes in AppShell (sidebar + topbar)
 * and ProtectedRoute (redirects to /login if not authenticated).
 *
 * The ShadowAgent replaces the old AdvisoryPanel + AdvisoryFAB.
 * - ShadowWidget: 36px breathing circle at bottom-right (replaces FAB)
 * - CommandSurface: command palette overlay (replaces chat drawer)
 * - ShadowMargin: persistent right-edge insight strip (desktop only, T126)
 */
export default function DashboardLayout({ children }: { children: ReactNode }) {
  /* ── Restore text size accessibility preference on mount ── */
  useEffect(() => {
    const storedTextSize = localStorage.getItem("textSize");
    if (storedTextSize) {
      document.documentElement.setAttribute("data-text-size", storedTextSize);
    }
    // Mirror the active locale onto <html lang> so screen readers and
    // CSS :lang() selectors pick up the user's choice.
    document.documentElement.lang = getLocale();
  }, []);

  return (
    <ProtectedRoute>
      <AppShell>
        <ShadowAgentProvider>
          <div className="animate-fade-in">{children}</div>
          <ShadowAgentUI />
          <RoleGatedShadowMargin />
        </ShadowAgentProvider>
      </AppShell>
    </ProtectedRoute>
  );
}

/**
 * The shadow margin surfaces compliance gaps, regulatory updates, and KB
 * deadlines — all of which are HR-admin actionable. Render only for
 * owner / hr_manager. Employees see the rest of the shell without the
 * compliance-warning rail.
 */
function RoleGatedShadowMargin() {
  const { user } = useAuth();
  const role = user?.role;
  if (role !== "owner" && role !== "hr_manager") return null;
  return <ShadowMarginWrapper />;
}

/** Inner component that uses the shadow agent context */
function ShadowAgentUI() {
  const {
    isCommandOpen,
    hasAttention,
    isAdvisoryPage,
    isProcessing,
    recentCommands,
    nudgeCount,
    toggleCommand,
    closeCommand,
    submitCommand,
    markNudgesSeen,
  } = useShadowAgent();

  return (
    <>
      <ShadowWidget
        isCommandOpen={isCommandOpen}
        hasAttention={hasAttention}
        isAdvisoryPage={isAdvisoryPage}
        nudgeCount={nudgeCount}
        onToggle={toggleCommand}
        onNudgesSeen={markNudgesSeen}
      />
      <CommandSurface
        isOpen={isCommandOpen}
        onClose={closeCommand}
        onSubmit={submitCommand}
        recentCommands={recentCommands}
        isProcessing={isProcessing}
      />
    </>
  );
}

/**
 * T126 + T127: Wrapper that feeds shadow context insights into the margin.
 * The ShadowMargin component handles:
 * - Desktop-only rendering (returns null on <1024px)
 * - Graceful empty/error states
 * - Compliance gaps, regulatory updates, and deadline reminders from the API
 */
function ShadowMarginWrapper() {
  const { insights, isLoading } = useShadowContext();
  const { insights: observationInsights } = useObservation();
  const [historyOpen, setHistoryOpen] = useState(false);

  return (
    <>
      <ShadowMargin
        insights={insights}
        isLoading={isLoading}
        observationInsights={observationInsights}
        onOpenHistory={() => setHistoryOpen(true)}
      />
      <ArborHistory
        isOpen={historyOpen}
        onClose={() => setHistoryOpen(false)}
      />
    </>
  );
}
