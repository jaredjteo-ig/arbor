/* ── Knowledge Base API Service ───────────────────────────── */

import { apiClient } from "./client";
import type {
  ActListResponse,
  DomainListResponse,
  Provision,
  ProvisionDetail,
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

  /** Get a specific provision by numeric ID. */
  provision(provisionId: string): Promise<Provision> {
    return apiClient.get<Provision>(`/kb/provisions/${provisionId}`);
  },

  /** Look up a provision by its string reference (e.g. "EA-S10-notice"). */
  provisionByRef(reference: string): Promise<ProvisionDetail> {
    return apiClient.get<ProvisionDetail>(
      `/kb/provisions/ref/${encodeURIComponent(reference)}`,
    );
  },

  /** Query the knowledge base with natural language. */
  query(data: KbQueryRequest): Promise<KbQueryResponse> {
    return apiClient.post<KbQueryResponse>("/kb/query", data);
  },
};
