/* ── Search API Service ───────────────────────────────────── */

import { apiClient } from "./client";
import type {
  SemanticSearchRequest,
  SemanticSearchResponse,
  FulltextSearchRequest,
  FulltextSearchResponse,
} from "@/types/api";

export const searchApi = {
  /** Perform a semantic (vector) search across provisions. */
  semantic(data: SemanticSearchRequest): Promise<SemanticSearchResponse> {
    return apiClient.post<SemanticSearchResponse>("/search/semantic", data);
  },

  /** Perform a full-text search with optional filters. */
  fulltext(data: FulltextSearchRequest): Promise<FulltextSearchResponse> {
    return apiClient.post<FulltextSearchResponse>("/search/fulltext", data);
  },
};
