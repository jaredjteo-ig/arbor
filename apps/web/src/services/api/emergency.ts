/* ── Emergency API Service ────────────────────────────────── */

import { apiClient } from "./client";
import type {
  EmergencyScenario,
  EmergencyScenarioListResponse,
  EscalationRequest,
  EscalationResponse,
  AdvisoryEscalationRequest,
  AdvisoryEscalationResponse,
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

  /** Submit an emergency escalation request (from emergency scenarios page). */
  escalate(data: EscalationRequest): Promise<EscalationResponse> {
    return apiClient.post<EscalationResponse>("/emergency/escalate", data);
  },

  /** Submit an advisory escalation request (from chat context). */
  submitAdvisoryEscalation(
    data: AdvisoryEscalationRequest,
  ): Promise<AdvisoryEscalationResponse> {
    return apiClient.post<AdvisoryEscalationResponse>(
      "/emergency/escalation",
      data,
    );
  },
} as const;
