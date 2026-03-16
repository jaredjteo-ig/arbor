"use client";

import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { AdvisoryPanelProvider } from "@/contexts/AdvisoryPanelContext";
import { AdvisoryPanel, AdvisoryFAB } from "@/components/advisory-panel";

/**
 * Dashboard layout — wraps all authenticated routes in AppShell (sidebar + topbar)
 * and ProtectedRoute (redirects to /login if not authenticated).
 *
 * AdvisoryPanelProvider sits inside AppShell so the floating advisory panel
 * persists across all dashboard page navigations.
 */
export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <AppShell>
        <AdvisoryPanelProvider>
          <div className="animate-fade-in">{children}</div>
          <AdvisoryPanel />
          <AdvisoryFAB />
        </AdvisoryPanelProvider>
      </AppShell>
    </ProtectedRoute>
  );
}
