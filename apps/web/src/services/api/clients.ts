import { apiClient } from "./client";
import type {
  ClientListResponse,
  ClientCompany,
  ClientCreateRequest,
} from "@/types/api";

export const clientsApi = {
  list(): Promise<ClientListResponse> {
    return apiClient.get<ClientListResponse>("/clients/");
  },

  get(clientId: number): Promise<ClientCompany> {
    return apiClient.get<ClientCompany>(`/clients/${clientId}`);
  },

  create(data: ClientCreateRequest): Promise<ClientCompany> {
    return apiClient.post<ClientCompany>("/clients/", data);
  },

  update(
    clientId: number,
    data: Partial<ClientCreateRequest>,
  ): Promise<ClientCompany> {
    return apiClient.put<ClientCompany>(`/clients/${clientId}`, data);
  },
};
