"use client";

import { useState } from "react";
import {
  LayoutDashboard,
  FileText,
  Database,
  MessageSquareWarning,
  ShieldCheck,
  ClipboardCheck,
  BarChart3,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { OverviewTab } from "./elements/OverviewTab";
import { RegulatoryUpdatesTab } from "./elements/RegulatoryUpdatesTab";
import { KbManagementTab } from "./elements/KbManagementTab";
import { FeedbackReviewTab } from "./elements/FeedbackReviewTab";
import { AuditTab } from "./elements/AuditTab";
import { QASessionsTab } from "./elements/QASessionsTab";
import { QAMetricsDashboard } from "./elements/QAMetricsDashboard";

/* ── Tab definitions ──────────────────────────────────────── */

type TabId =
  | "overview"
  | "updates"
  | "kb"
  | "feedback"
  | "audit"
  | "qa"
  | "metrics";

interface TabDef {
  id: TabId;
  label: string;
  icon: typeof LayoutDashboard;
}

const TABS: TabDef[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "updates", label: "Regulatory Updates", icon: FileText },
  { id: "kb", label: "KB Management", icon: Database },
  { id: "feedback", label: "Feedback Review", icon: MessageSquareWarning },
  { id: "audit", label: "Audit", icon: ShieldCheck },
  { id: "qa", label: "QA Sessions", icon: ClipboardCheck },
  { id: "metrics", label: "QA Metrics", icon: BarChart3 },
];

/* ── Tab content mapping ──────────────────────────────────── */

const TAB_PANELS: Record<TabId, () => React.JSX.Element | null> = {
  overview: OverviewTab,
  updates: RegulatoryUpdatesTab,
  kb: KbManagementTab,
  feedback: FeedbackReviewTab,
  audit: AuditTab,
  qa: QASessionsTab,
  metrics: QAMetricsDashboard,
};

/* ── Page ─────────────────────────────────────────────────── */

export default function AdminPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const ActivePanel = TAB_PANELS[activeTab];

  if (user?.role !== "owner" && user?.role !== "hr_manager") {
    return (
      <div className="max-w-6xl mx-auto py-12 text-center">
        <p className="text-[var(--color-gray-500)]">
          Access Denied. You do not have permission to view this page.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
          Admin &amp; Operations
        </h1>
        <p className="text-sm text-[var(--color-gray-500)] mt-1">
          Manage regulatory updates, knowledge base, feedback, audit responses,
          QA review sessions, and quality metrics
        </p>
      </div>

      {/* Tab navigation */}
      <nav
        role="tablist"
        aria-label="Admin sections"
        className="flex gap-1 overflow-x-auto border-b border-[var(--color-gray-200)] -mb-px"
      >
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${tab.id}`}
              id={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] ${
                isActive
                  ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                  : "border-transparent text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] hover:border-[var(--color-gray-300)]"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Tab panel */}
      <div
        role="tabpanel"
        id={`panel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
      >
        <ActivePanel />
      </div>
    </div>
  );
}
