/* ── Shadow Nudge Polling Hook ────────────────────────────── */
/* Periodically checks for contextual nudges from the shadow   */
/* agent and tracks which nudges have been seen by the user.   */

"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import {
  shadowApi,
  type Nudge,
  type NudgesResponse,
} from "@/services/api/shadow";

/* ── Query Keys ──────────────────────────────────────────── */

export const nudgeKeys = {
  all: ["shadow-nudges"] as const,
  byPage: (page: string) => [...nudgeKeys.all, page] as const,
};

/* ── Constants ───────────────────────────────────────────── */

const POLL_INTERVAL_MS = 60_000;

/* ── Hook ────────────────────────────────────────────────── */

interface UseShadowNudgesReturn {
  /** Current nudge items from the API. */
  nudges: Nudge[];
  /** Count of unseen nudges (total minus dismissed). */
  unseenCount: number;
  /** Whether nudges are currently loading. */
  isLoading: boolean;
  /** Mark all current nudges as seen (stops the pulse animation). */
  markAllSeen: () => void;
  /** Dismiss a specific nudge by ID. */
  dismiss: (nudgeId: string) => void;
  /** Force an immediate refetch. */
  refresh: () => void;
}

function pageNameFromPath(pathname: string): string {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return "dashboard";
  return segments[0];
}

export function useShadowNudges(): UseShadowNudgesReturn {
  const pathname = usePathname();
  const page = pageNameFromPath(pathname);
  const queryClient = useQueryClient();

  // Track IDs of nudges the user has seen or dismissed this session
  const [seenIds, setSeenIds] = useState<Set<string>>(new Set());

  const { data, isLoading } = useQuery<NudgesResponse, Error>({
    queryKey: nudgeKeys.byPage(page),
    queryFn: () => shadowApi.nudges(page),
    refetchInterval: POLL_INTERVAL_MS,
    // Prevent refetch on window focus to avoid spamming the endpoint
    refetchOnWindowFocus: false,
    // Treat nudge data as stale after the polling interval
    staleTime: POLL_INTERVAL_MS,
    // Keep previous page data while new page data loads
    placeholderData: (previousData) => previousData,
  });

  const nudges = data?.nudges ?? [];
  const unseenCount = nudges.filter((n) => !seenIds.has(n.id)).length;

  const markAllSeen = () => {
    setSeenIds((prev) => {
      const next = new Set(prev);
      for (const nudge of nudges) {
        next.add(nudge.id);
      }
      return next;
    });
  };

  const dismiss = (nudgeId: string) => {
    setSeenIds((prev) => {
      const next = new Set(prev);
      next.add(nudgeId);
      return next;
    });
  };

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: nudgeKeys.all });
  };

  return {
    nudges,
    unseenCount,
    isLoading,
    markAllSeen,
    dismiss,
    refresh,
  };
}
