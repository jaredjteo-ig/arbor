/* ── Compliance API Service ───────────────────────────────── */

import { apiClient } from "./client";
import type {
  ComplianceCheckRequest,
  ComplianceCheckResponse,
  ComplianceStatusResponse,
  ComplianceGapAnalysisRequest,
  ComplianceGapAnalysisResponse,
} from "@/types/api";

export const complianceApi = {
  /** Run a compliance check for a company across specified domains. */
  check(data: ComplianceCheckRequest): Promise<ComplianceCheckResponse> {
    return apiClient.post<ComplianceCheckResponse>("/compliance/check", data);
  },

  /** Get current compliance status for a company. */
  status(companyId: number): Promise<ComplianceStatusResponse> {
    return apiClient.get<ComplianceStatusResponse>(
      `/compliance/status/${companyId}`,
    );
  },

  /** Perform a gap analysis for a company's compliance posture. */
  gapAnalysis(
    data: ComplianceGapAnalysisRequest,
  ): Promise<ComplianceGapAnalysisResponse> {
    return apiClient.post<ComplianceGapAnalysisResponse>(
      "/compliance/gap-analysis",
      data,
    );
  },
};
