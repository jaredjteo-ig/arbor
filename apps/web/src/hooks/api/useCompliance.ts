/* ── Compliance Hooks ─────────────────────────────────────── */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { complianceApi } from "@/services/api/compliance";
import type {
  ComplianceCheckRequest,
  ComplianceCheckResponse,
  ComplianceStatusResponse,
  ComplianceGapAnalysisRequest,
  ComplianceGapAnalysisResponse,
} from "@/types/api";

/** Query keys for compliance domain. */
export const complianceKeys = {
  all: ["compliance"] as const,
  status: (companyId: number) =>
    [...complianceKeys.all, "status", companyId] as const,
};

/**
 * Fetch compliance status for a company.
 * Only fetches when companyId is provided (> 0).
 */
export function useComplianceStatus(companyId: number) {
  return useQuery<ComplianceStatusResponse, Error>({
    queryKey: complianceKeys.status(companyId),
    queryFn: () => complianceApi.status(companyId),
    enabled: companyId > 0,
  });
}

/**
 * Run a compliance check for a company.
 * Invalidates status cache on success so the dashboard updates.
 */
export function useComplianceCheck() {
  const queryClient = useQueryClient();

  return useMutation<ComplianceCheckResponse, Error, ComplianceCheckRequest>({
    mutationFn: (data) => complianceApi.check(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: complianceKeys.status(data.company_id),
      });
    },
  });
}

/**
 * Run a gap analysis for a company.
 */
export function useComplianceGapAnalysis() {
  return useMutation<
    ComplianceGapAnalysisResponse,
    Error,
    ComplianceGapAnalysisRequest
  >({
    mutationFn: (data) => complianceApi.gapAnalysis(data),
  });
}
