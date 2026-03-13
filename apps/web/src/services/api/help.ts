/* ── Help API Service ─────────────────────────────────────── */

import { apiClient } from "./client";
import type {
  HelpArticle,
  HelpArticleListResponse,
  GettingStartedResponse,
} from "@/types/api";

export type { HelpArticle, HelpArticleListResponse, GettingStartedResponse };

export const helpApi = {
  /** List FAQ articles, optionally filtered by category. */
  listArticles(category?: string): Promise<HelpArticleListResponse> {
    const params: Record<string, string> = {};
    if (category) params.category = category;
    return apiClient.get<HelpArticleListResponse>("/help/articles", params);
  },

  /** Get the getting-started guide content. */
  gettingStarted(): Promise<GettingStartedResponse> {
    return apiClient.get<GettingStartedResponse>("/help/getting-started");
  },
} as const;
