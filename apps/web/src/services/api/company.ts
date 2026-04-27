import { apiClient } from "./client";
import type {
  CompanyListResponse,
  Company,
  CompanyCreateRequest,
} from "@/types/api";

export const companyApi = {
  list(): Promise<CompanyListResponse> {
    return apiClient.get<CompanyListResponse>("/company");
  },

  get(companyId: number): Promise<Company> {
    return apiClient.get<Company>(`/company/${companyId}`);
  },

  create(data: CompanyCreateRequest): Promise<Company> {
    return apiClient.post<Company>("/company", data);
  },

  update(
    companyId: number,
    data: Partial<CompanyCreateRequest>,
  ): Promise<Company> {
    return apiClient.put<Company>(`/company/${companyId}`, data);
  },
};
