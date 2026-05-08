/* ── Xero Payroll-Export Hooks ─────────────────────────────── */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  xeroPayrollApi,
  type XeroAccountMapping,
  type XeroChartOfAccountsResponse,
  type XeroExportRequest,
  type XeroExportResponse,
  type XeroMappingResponse,
  type XeroStatusResponse,
} from "@/services/api/payroll";

export const xeroPayrollKeys = {
  all: ["xero-payroll"] as const,
  status: () => [...xeroPayrollKeys.all, "status"] as const,
  chart: () => [...xeroPayrollKeys.all, "chart"] as const,
  mapping: () => [...xeroPayrollKeys.all, "mapping"] as const,
};

/** Connection + mapping completeness flags. Cheap, refresh on focus. */
export function useXeroPayrollStatus() {
  return useQuery<XeroStatusResponse, Error>({
    queryKey: xeroPayrollKeys.status(),
    queryFn: () => xeroPayrollApi.getStatus(),
    staleTime: 30_000,
  });
}

/** Xero chart of accounts — for dropdowns. Only fetch when modal opens. */
export function useXeroChartOfAccounts(enabled: boolean) {
  return useQuery<XeroChartOfAccountsResponse, Error>({
    queryKey: xeroPayrollKeys.chart(),
    queryFn: () => xeroPayrollApi.getChartOfAccounts(),
    enabled,
    staleTime: 5 * 60_000,
  });
}

/**
 * Saved mapping or auto-match suggestions. ``source`` distinguishes:
 *  - "saved"      — user previously confirmed
 *  - "auto_match" — fuzzy-match suggestions, not yet saved
 *  - "empty"      — Xero not connected or chart unavailable
 */
export function useXeroMapping(enabled: boolean) {
  return useQuery<XeroMappingResponse, Error>({
    queryKey: xeroPayrollKeys.mapping(),
    queryFn: () => xeroPayrollApi.getMapping(),
    enabled,
  });
}

export function useSaveXeroMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mapping: XeroAccountMapping) =>
      xeroPayrollApi.putMapping(mapping),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: xeroPayrollKeys.status() });
      qc.invalidateQueries({ queryKey: xeroPayrollKeys.mapping() });
    },
  });
}

export function useExportRunToXero() {
  const qc = useQueryClient();
  return useMutation<
    XeroExportResponse,
    Error,
    { runId: number; body?: XeroExportRequest }
  >({
    mutationFn: ({ runId, body }) => xeroPayrollApi.exportRun(runId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: xeroPayrollKeys.status() });
    },
  });
}
