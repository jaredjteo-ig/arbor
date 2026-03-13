/* ── Emergency API Service ────────────────────────────────── */

import { apiClient } from "./client";
import type {
  EmergencyScenario,
  EmergencyScenarioListResponse,
  EscalationRequest,
  EscalationResponse,
} from "@/types/api";

export type { EmergencyScenario, EmergencyScenarioListResponse };

export const emergencyApi = {
  /** List all emergency scenarios with full response content. */
  listScenarios(): Promise<EmergencyScenarioListResponse> {
    return apiClient.get<EmergencyScenarioListResponse>("/emergency/scenarios");
  },

  /** Get a specific emergency scenario by topic ID. */
  getScenario(topicId: string): Promise<EmergencyScenario> {
    return apiClient.get<EmergencyScenario>(`/emergency/scenarios/${topicId}`);
  },

  /** Submit an emergency escalation request. */
  escalate(data: EscalationRequest): Promise<EscalationResponse> {
    return apiClient.post<EscalationResponse>("/emergency/escalate", data);
  },
} as const;
