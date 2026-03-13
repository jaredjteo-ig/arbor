/* ── Calculator Hooks ─────────────────────────────────────── */

"use client";

import { useMutation } from "@tanstack/react-query";
import { calculatorsApi } from "@/services/api/calculators";
import type {
  CpfCalculationRequest,
  CpfCalculationResponse,
  LeaveCalculationRequest,
  LeaveCalculationResponse,
  SalaryCalculationRequest,
  SalaryCalculationResponse,
} from "@/types/api";

/**
 * Calculate CPF contributions.
 * Mutation because the user submits a form to trigger it.
 */
export function useCpfCalculation() {
  return useMutation<CpfCalculationResponse, Error, CpfCalculationRequest>({
    mutationFn: (data) => calculatorsApi.cpf(data),
  });
}

/**
 * Calculate leave entitlements.
 */
export function useLeaveCalculation() {
  return useMutation<LeaveCalculationResponse, Error, LeaveCalculationRequest>({
    mutationFn: (data) => calculatorsApi.leave(data),
  });
}

/**
 * Calculate salary breakdown.
 */
export function useSalaryCalculation() {
  return useMutation<SalaryCalculationResponse, Error, SalaryCalculationRequest>({
    mutationFn: (data) => calculatorsApi.salary(data),
  });
}
