/* ── Xero Payroll-Export Hooks ─────────────────────────────── */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  xeroPayrollApi,
  type XeroAccountMapping,
  type XeroChartOfAccountsResponse,
  type XeroExportRequest,
  type XeroExportResponse,
  type XeroExportStatusResponse,
  type XeroMappingHealthResponse,
  type XeroMappingResponse,
  type XeroStatusResponse,
} from "@/services/api/payroll";

export const xeroPayrollKeys = {
  all: ["xero-payroll"] as const,
  status: () => [...xeroPayrollKeys.all, "status"] as const,
  chart: () => [...xeroPayrollKeys.all, "chart"] as const,
  mapping: () => [...xeroPayrollKeys.all, "mapping"] as const,
  suggestedBonus: (runId: number) =>
    [...xeroPayrollKeys.all, "suggested-bonus", runId] as const,
};

/** Most recent export attempt status for a run (M2-T07). */
export function useXeroExportStatus(runId: number, enabled: boolean) {
  return useQuery<XeroExportStatusResponse, Error>({
    queryKey: [...xeroPayrollKeys.all, "export-status", runId] as const,
    queryFn: () => xeroPayrollApi.getExportStatus(runId),
    enabled: enabled && runId > 0,
    staleTime: 30_000,
  });
}

/** Sum of bonus+commission payslip items for a run — pre-fills the
 *  modal's bonus_total field so the Salary/Bonus split mirrors what
 *  was actually paid (M2-T05). */
export function useXeroSuggestedBonus(runId: number, enabled: boolean) {
  return useQuery<{ suggested_bonus_total: number }, Error>({
    queryKey: xeroPayrollKeys.suggestedBonus(runId),
    queryFn: () => xeroPayrollApi.getSuggestedBonus(runId),
    enabled: enabled && runId > 0,
    staleTime: 5 * 60_000,
  });
}

/** Connection + mapping completeness flags. Cheap, refresh on focus. */
export function useXeroPayrollStatus() {
  return useQuery<XeroStatusResponse, Error>({
    queryKey: xeroPayrollKeys.status(),
    queryFn: () => xeroPayrollApi.getStatus(),
    staleTime: 30_000,
  });
}

/** Xero chart of accounts — for dropdowns. Only fetch when needed.
 *  ``forceRefresh=true`` bypasses the 24h server-side cache (used by the
 *  mapping settings page's "Refresh accounts" button). */
export function useXeroChartOfAccounts(enabled: boolean, forceRefresh = false) {
  return useQuery<XeroChartOfAccountsResponse, Error>({
    queryKey: [...xeroPayrollKeys.chart(), forceRefresh],
    queryFn: () => xeroPayrollApi.getChartOfAccounts(forceRefresh),
    enabled,
    staleTime: 5 * 60_000,
  });
}

/** Compares saved mapping to current Xero chart, returns
 *  archived/missing/system_managed codes for the mapping page banner. */
export function useXeroMappingHealth(enabled: boolean) {
  return useQuery<XeroMappingHealthResponse, Error>({
    queryKey: [...xeroPayrollKeys.all, "mapping-health"] as const,
    queryFn: () => xeroPayrollApi.getMappingHealth(),
    enabled,
    staleTime: 60_000,
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

/** Void a previously-exported Xero ManualJournal (M2-T01). */
export function useVoidXeroExport() {
  return useMutation({
    mutationFn: (runId: number) => xeroPayrollApi.voidExport(runId),
  });
}
