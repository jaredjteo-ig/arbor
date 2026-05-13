/* ── Team Hooks ───────────────────────────────────────────── */

"use client";

import { useQuery } from "@tanstack/react-query";
import {
  teamApi,
  type TeamDashboard,
  type TeamSizeResponse,
} from "@/services/api/team";
import {
  engagementApi,
  type TeamEngagementAggregate,
} from "@/services/api/engagement";

/** Query keys for the team domain. */
export const teamKeys = {
  all: ["team"] as const,
  size: ["team", "size"] as const,
  dashboard: ["team", "dashboard"] as const,
  engagement: (surveyId?: number) =>
    ["team", "engagement", surveyId ?? "latest"] as const,
  members: (activeOnly: boolean) =>
    ["team", "members", { activeOnly }] as const,
};

/**
 * Fetch the caller's direct-report count. Cheap; used by the
 * sidebar to decide whether to render the Team nav entry.
 *
 * `staleTime` is 5 minutes — org-chart changes don't propagate
 * second-by-second, so a stale count is fine for nav visibility.
 */
export function useTeamSize() {
  return useQuery<TeamSizeResponse, Error>({
    queryKey: teamKeys.size,
    queryFn: () => teamApi.size(),
    staleTime: 5 * 60 * 1000,
  });
}

/** Fetch the bundled /team page payload. */
export function useTeamDashboard() {
  return useQuery<TeamDashboard, Error>({
    queryKey: teamKeys.dashboard,
    queryFn: () => teamApi.dashboard(),
  });
}

/**
 * Fetch the team's engagement aggregate for the latest closed survey
 * (or a specific survey if `surveyId` is provided). Returns a
 * discriminated union — callers must check `is_visible` before
 * reading score/trend fields. The BE enforces n ≥ 5 + Z26
 * self-exclusion + tier-aware pseudonym resolution; the FE just
 * branches on the visibility flag (P4-MG-5).
 */
export function useTeamEngagement(surveyId?: number) {
  return useQuery<TeamEngagementAggregate, Error>({
    queryKey: teamKeys.engagement(surveyId),
    queryFn: () => engagementApi.teamAggregate(surveyId),
  });
}
