"use client";

import { useState, useEffect, useCallback } from "react";
import { usePathname } from "next/navigation";
import {
  unwrapNexusResponse,
  getValidAccessToken,
} from "@/services/api/client";
import type { ShadowInsight } from "./ShadowMargin";
import type { AnnotationData } from "./InlineAnnotation";

/* ── Types ────────────────────────────────────────────────── */

interface ShadowContextResponse {
  insights: ShadowInsight[];
  alerts: Array<{
    id: string;
    type: string;
    title: string;
    description: string;
    days_remaining?: number;
  }>;
  annotations: Record<string, AnnotationData[]>;
}

interface UseShadowContextReturn {
  insights: ShadowInsight[];
  annotations: AnnotationData[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/* ── Page name extraction ─────────────────────────────────── */

function pageNameFromPath(pathname: string): string {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return "dashboard";
  return segments[0];
}

/* ── Hook ─────────────────────────────────────────────────── */

/**
 * Fetch shadow agent context data for the current page.
 *
 * Returns insights (for the margin) and annotations (for inline display).
 * Refreshes every 5 minutes and on page navigation.
 */
export function useShadowContext(): UseShadowContextReturn {
  const pathname = usePathname();
  const pageName = pageNameFromPath(pathname);

  const [insights, setInsights] = useState<ShadowInsight[]>([]);
  const [annotations, setAnnotations] = useState<AnnotationData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pollEnabled, setPollEnabled] = useState(true);

  const fetchContext = useCallback(async () => {
    const token = await getValidAccessToken();

    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const API_BASE =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(
        `${API_BASE}/shadow/context?page=${pageName}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) {
        // Shadow context is non-critical — fail silently.
        // Stop polling on 403/404 (endpoint not deployed or not authorized).
        if (response.status === 403 || response.status === 404) {
          setPollEnabled(false);
        }
        setIsLoading(false);
        return;
      }

      const raw = await response.json();
      const data = unwrapNexusResponse(raw) as ShadowContextResponse;

      // Merge insights and alerts into a single list
      const allInsights: ShadowInsight[] = [
        ...(data.insights || []),
        ...(data.alerts || []).map((alert) => ({
          id: alert.id,
          type: "deadline" as const,
          severity: (alert.days_remaining !== undefined &&
          alert.days_remaining <= 3
            ? "high"
            : alert.days_remaining !== undefined && alert.days_remaining <= 7
              ? "medium"
              : "low") as ShadowInsight["severity"],
          title: alert.title,
          description: alert.description,
          daysRemaining: alert.days_remaining,
        })),
      ];

      setInsights(allInsights);
      setAnnotations(data.annotations?.[pageName] || []);
      setError(null);
    } catch {
      // Shadow context is non-critical — fail silently
      setError("Unable to load insights");
    } finally {
      setIsLoading(false);
    }
  }, [pageName]);

  // Fetch on mount and page change
  useEffect(() => {
    setIsLoading(true);
    fetchContext();
  }, [fetchContext]);

  // Auto-refresh every 5 minutes (disabled after 403/404)
  useEffect(() => {
    if (!pollEnabled) return;
    const interval = setInterval(fetchContext, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchContext, pollEnabled]);

  return {
    insights,
    annotations,
    isLoading,
    error,
    refresh: fetchContext,
  };
}
