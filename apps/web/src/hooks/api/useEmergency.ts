/* ── Emergency Hooks ──────────────────────────────────────── */

"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { emergencyApi } from "@/services/api/emergency";
import type {
  EmergencyScenarioListResponse,
  EscalationRequest,
  EscalationResponse,
} from "@/types/api";

/** Query keys for emergency domain. */
export const emergencyKeys = {
  all: ["emergency"] as const,
  scenarios: [...(["emergency", "scenarios"] as const)] as const,
};

/**
 * Fetch all emergency scenarios with full response content.
 */
export function useEmergencyScenarios() {
  return useQuery<EmergencyScenarioListResponse, Error>({
    queryKey: emergencyKeys.scenarios,
    queryFn: () => emergencyApi.listScenarios(),
    staleTime: 5 * 60 * 1000, // Emergency content rarely changes
  });
}

/**
 * Submit an emergency escalation request.
 */
export function useEmergencyEscalate() {
  return useMutation<EscalationResponse, Error, EscalationRequest>({
    mutationFn: (data) => emergencyApi.escalate(data),
  });
}
