"use client";

import { useState, useEffect, useCallback } from "react";
import { usePathname } from "next/navigation";

/* -- Types --------------------------------------------------------- */

export interface PageVisit {
  page: string;
  timestamp: number;
}

export interface ObservationInsight {
  id: string;
  message: string;
  page: string;
  visitCount: number;
  actionPrompt?: string;
  actionPath?: string;
}

interface UseObservationReturn {
  /** All recorded page visits in the current session */
  visits: PageVisit[];
  /** Generated insights based on navigation patterns */
  insights: ObservationInsight[];
  /** Whether pattern learning is enabled */
  isEnabled: boolean;
  /** Toggle pattern learning on/off */
  setEnabled: (value: boolean) => void;
  /** Clear all recorded observations */
  clearAll: () => void;
}

/* -- Constants ----------------------------------------------------- */

const STORAGE_KEY_VISITS = "arbor_observation_visits";
const STORAGE_KEY_ENABLED = "arbor_observation_enabled";
const MIN_VISITS_FOR_INSIGHT = 3;

/* -- Page label mapping -------------------------------------------- */

const PAGE_LABELS: Record<string, string> = {
  "/": "Dashboard",
  "/my-dashboard": "My Dashboard",
  "/my-leave": "My Leave",
  "/policies": "Policies",
  "/compliance": "Compliance",
  "/calculators": "Calculators",
  "/advisory": "Advisory",
  "/documents": "Documents",
  "/settings": "Settings",
  "/employees": "Employees",
  "/analytics": "Analytics",
  "/emergency": "Emergency Guides",
};

function getPageLabel(path: string): string {
  return PAGE_LABELS[path] || path.replace(/^\//, "").replace(/-/g, " ");
}

/* -- Session storage helpers --------------------------------------- */

function getStoredVisits(): PageVisit[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY_VISITS);
    return raw ? (JSON.parse(raw) as PageVisit[]) : [];
  } catch {
    return [];
  }
}

function storeVisits(visits: PageVisit[]): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(STORAGE_KEY_VISITS, JSON.stringify(visits));
  } catch {
    // Session storage full or unavailable
  }
}

function getEnabledState(): boolean {
  if (typeof window === "undefined") return true;
  const stored = localStorage.getItem(STORAGE_KEY_ENABLED);
  return stored !== "false"; // Enabled by default
}

/* -- Insight generation -------------------------------------------- */

function generateInsights(visits: PageVisit[]): ObservationInsight[] {
  const insights: ObservationInsight[] = [];

  // Count visits per page
  const pageCounts = new Map<string, number>();
  for (const visit of visits) {
    const count = pageCounts.get(visit.page) || 0;
    pageCounts.set(visit.page, count + 1);
  }

  // Generate insights for pages visited 3+ times
  for (const [page, count] of pageCounts) {
    if (count < MIN_VISITS_FOR_INSIGHT) continue;

    const label = getPageLabel(page);

    // Compliance-specific insight
    if (page === "/compliance" || page.startsWith("/compliance")) {
      insights.push({
        id: `obs-compliance-${count}`,
        message: `You've viewed ${label} ${count} times today. Want to run a full compliance check?`,
        page,
        visitCount: count,
        actionPrompt: "Run compliance check",
        actionPath: "/compliance",
      });
    }
    // Calculator-specific insight
    else if (page === "/calculators" || page.startsWith("/calculators")) {
      insights.push({
        id: `obs-calculators-${count}`,
        message: `You've used the ${label} ${count} times this session. Pin your most-used calculation?`,
        page,
        visitCount: count,
      });
    }
    // Leave page insight
    else if (page === "/my-leave") {
      insights.push({
        id: `obs-leave-${count}`,
        message: `You've checked your leave balance ${count} times. Need help planning time off?`,
        page,
        visitCount: count,
      });
    }
    // Policies insight
    else if (page === "/policies") {
      insights.push({
        id: `obs-policies-${count}`,
        message: `You've reviewed policies ${count} times. Looking for something specific? Ask Central.`,
        page,
        visitCount: count,
      });
    }
    // Generic insight for any page
    else {
      insights.push({
        id: `obs-${page}-${count}`,
        message: `You've visited ${label} ${count} times this session.`,
        page,
        visitCount: count,
      });
    }
  }

  // Sort by visit count descending
  insights.sort((a, b) => b.visitCount - a.visitCount);

  return insights;
}

/* -- Backend reporting --------------------------------------------- */

import { getValidAccessToken } from "@/services/api/client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Report a page observation to the backend (fire-and-forget).
 * Uses the shadow/observe endpoint to persist navigation data.
 */
async function reportObservation(page: string): Promise<void> {
  try {
    const token = await getValidAccessToken();
    if (!token) return;

    fetch(`${API_BASE}/shadow/observe`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        page,
        action_type: "page_visit",
        details: { label: getPageLabel(page) },
        timestamp: new Date().toISOString(),
      }),
    }).catch(() => {
      // Silently ignore — observation is best-effort
    });
  } catch {
    // No token or network error — ignore
  }
}

/* -- Hook ---------------------------------------------------------- */

/**
 * Observation Layer (Substrate - Layer A)
 *
 * Tracks page navigation patterns within a session and generates
 * insights when patterns are detected (e.g., visiting the same page
 * repeatedly).
 *
 * Persists observations to backend via /shadow/observe for cross-session
 * learning and shadow agent memory distillation.
 */
export function useObservation(): UseObservationReturn {
  const pathname = usePathname();
  const [visits, setVisits] = useState<PageVisit[]>([]);
  const [isEnabled, setIsEnabledState] = useState(true);
  const [insights, setInsights] = useState<ObservationInsight[]>([]);

  // Load initial state
  useEffect(() => {
    setVisits(getStoredVisits());
    setIsEnabledState(getEnabledState());
  }, []);

  // Record page visit on navigation and report to backend
  useEffect(() => {
    if (!isEnabled) return;

    const newVisit: PageVisit = {
      page: pathname,
      timestamp: Date.now(),
    };

    setVisits((prev) => {
      const updated = [...prev, newVisit];
      storeVisits(updated);

      // Only generate insights after 5+ total page views
      if (updated.length >= 5) {
        setInsights(generateInsights(updated));
      }

      return updated;
    });

    // Report observation to backend (fire-and-forget)
    reportObservation(pathname);
  }, [pathname, isEnabled]);

  const setEnabled = useCallback((value: boolean) => {
    setIsEnabledState(value);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY_ENABLED, String(value));
    }
    if (!value) {
      setInsights([]);
    }
  }, []);

  const clearAll = useCallback(() => {
    setVisits([]);
    setInsights([]);
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(STORAGE_KEY_VISITS);
    }
  }, []);

  return {
    visits,
    insights,
    isEnabled,
    setEnabled,
    clearAll,
  };
}
