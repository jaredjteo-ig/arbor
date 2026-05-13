/* ── Team Hooks ───────────────────────────────────────────── */

"use client";

import { useQuery } from "@tanstack/react-query";
import {
  teamApi,
  type TeamDashboard,
  type TeamSizeResponse,
} from "@/services/api/team";

/** Query keys for the team domain. */
export const teamKeys = {
  all: ["team"] as const,
  size: ["team", "size"] as const,
  dashboard: ["team", "dashboard"] as const,
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
