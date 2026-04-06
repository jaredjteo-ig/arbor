"use client";

import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useState } from "react";
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
  return (
    <ProtectedRoute>
      <AppShell>
        <ShadowAgentProvider>
          <div className="animate-fade-in">{children}</div>
          <ShadowAgentUI />
          <ShadowMarginWrapper />
        </ShadowAgentProvider>
      </AppShell>
    </ProtectedRoute>
  );
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
        onToggle={() => {
          toggleCommand();
          if (nudgeCount > 0) markNudgesSeen();
        }}
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
