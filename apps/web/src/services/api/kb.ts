/* ── Knowledge Base API Service ───────────────────────────── */

import { apiClient } from "./client";
import type {
  ActListResponse,
  DomainListResponse,
  Provision,
  KbQueryRequest,
  KbQueryResponse,
} from "@/types/api";

export const kbApi = {
  /** List all acts in the knowledge base. */
  acts(): Promise<ActListResponse> {
    return apiClient.get<ActListResponse>("/kb/acts");
  },

  /** List all regulatory domains. */
  domains(): Promise<DomainListResponse> {
    return apiClient.get<DomainListResponse>("/kb/domains");
  },

  /** Get a specific provision by ID. */
  provision(provisionId: string): Promise<Provision> {
    return apiClient.get<Provision>(`/kb/provisions/${provisionId}`);
  },

  /** Query the knowledge base with natural language. */
  query(data: KbQueryRequest): Promise<KbQueryResponse> {
    return apiClient.post<KbQueryResponse>("/kb/query", data);
  },
};
