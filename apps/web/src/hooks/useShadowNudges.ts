/* ── Shadow Nudge Polling Hook ────────────────────────────── */
/* Polls /shadow/nudges every 60s and tracks which nudge IDs   */
/* the user has already seen, exposing an unseen count for the */
/* ShadowWidget badge.                                         */

import { useState, useEffect, useCallback, useRef } from "react";
import { usePathname } from "next/navigation";
import { shadowApi, type Nudge } from "@/services/api/shadow";

const POLL_INTERVAL_MS = 60_000;

export interface UseShadowNudgesResult {
  /** Nudges returned from the latest poll. */
  nudges: Nudge[];
  /** Number of nudges the user has not yet acknowledged. */
  nudgeCount: number;
  /** Mark all current nudges as seen (resets the badge count). */
  markNudgesSeen: () => void;
}

export function useShadowNudges(): UseShadowNudgesResult {
  const pathname = usePathname();
  const [nudges, setNudges] = useState<Nudge[]>([]);
  const seenIdsRef = useRef<Set<string>>(new Set());

  const fetchNudges = useCallback(async () => {
    try {
      const res = await shadowApi.nudges(pathname);
      setNudges(res.nudges ?? []);
    } catch {
      /* Nudge polling is non-critical — fail silently */
    }
  }, [pathname]);

  /* Poll on mount, on pathname change, and every 60s */
  useEffect(() => {
    fetchNudges();
    const interval = setInterval(fetchNudges, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchNudges]);

  const nudgeCount = nudges.filter((n) => !seenIdsRef.current.has(n.id)).length;

  const markNudgesSeen = useCallback(() => {
    for (const n of nudges) {
      seenIdsRef.current.add(n.id);
    }
    /* Force a re-render so nudgeCount recalculates to 0 */
    setNudges((prev) => [...prev]);
  }, [nudges]);

  return { nudges, nudgeCount, markNudgesSeen };
}
