/* ── Calculator API Service ───────────────────────────────── */

import { apiClient } from "./client";
import type {
  CpfCalculationRequest,
  CpfCalculationResponse,
  LeaveCalculationRequest,
  LeaveCalculationResponse,
  SalaryCalculationRequest,
  SalaryCalculationResponse,
} from "@/types/api";

export const calculatorsApi = {
  /** Calculate CPF contributions based on salary, age, and citizenship. */
  cpf(data: CpfCalculationRequest): Promise<CpfCalculationResponse> {
    return apiClient.post<CpfCalculationResponse>("/calculator/cpf", data);
  },

  /** Calculate statutory leave entitlements. */
  leave(data: LeaveCalculationRequest): Promise<LeaveCalculationResponse> {
    return apiClient.post<LeaveCalculationResponse>("/calculator/leave", data);
  },

  /** Calculate salary breakdown including CPF deductions. */
  salary(data: SalaryCalculationRequest): Promise<SalaryCalculationResponse> {
    return apiClient.post<SalaryCalculationResponse>("/calculator/salary", data);
  },
};
