/* ── Profile API Service ──────────────────────────────────── */

import { apiClient } from "./client";
import type {
  CompanyProfile,
  CompanyProfileCreateRequest,
  CompanyProfileUpdateRequest,
  CompanyProfileUpdateResponse,
  WorkforceBreakdown,
} from "@/types/api";

export const profileApi = {
  /** Get a company profile by ID. */
  get(companyId: number): Promise<CompanyProfile> {
    return apiClient.get<CompanyProfile>(`/profile/${companyId}`);
  },

  /** Create a new company profile. */
  create(
    data: CompanyProfileCreateRequest,
  ): Promise<{
    id: number | null;
    name: string;
    uen: string | null;
    sector: string | null;
    created: boolean;
    timestamp: string;
  }> {
    return apiClient.post("/profile/", data);
  },

  /** Update an existing company profile. */
  update(
    companyId: number,
    data: CompanyProfileUpdateRequest,
  ): Promise<CompanyProfileUpdateResponse> {
    return apiClient.put<CompanyProfileUpdateResponse>(
      `/profile/${companyId}`,
      data,
    );
  },

  /** Get workforce breakdown for a company. */
  workforce(companyId: number): Promise<WorkforceBreakdown> {
    return apiClient.get<WorkforceBreakdown>(`/profile/${companyId}/workforce`);
  },
};
