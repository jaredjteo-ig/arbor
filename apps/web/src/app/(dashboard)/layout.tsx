"use client";

import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import {
  ShadowAgentProvider,
  ShadowWidget,
  CommandSurface,
  useShadowAgent,
} from "@/components/shadow-agent";

/**
 * Dashboard layout — wraps all authenticated routes in AppShell (sidebar + topbar)
 * and ProtectedRoute (redirects to /login if not authenticated).
 *
 * The ShadowAgent replaces the old AdvisoryPanel + AdvisoryFAB.
 * - ShadowWidget: 36px breathing circle at bottom-right (replaces FAB)
 * - CommandSurface: command palette overlay (replaces chat drawer)
 */
export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <AppShell>
        <ShadowAgentProvider>
          <div className="animate-fade-in">{children}</div>
          <ShadowAgentUI />
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
    toggleCommand,
    closeCommand,
    submitCommand,
  } = useShadowAgent();

  return (
    <>
      <ShadowWidget
        isCommandOpen={isCommandOpen}
        hasAttention={hasAttention}
        isAdvisoryPage={isAdvisoryPage}
        onToggle={toggleCommand}
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
