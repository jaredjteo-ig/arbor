/* ── Help Hooks ───────────────────────────────────────────── */

"use client";

import { useQuery } from "@tanstack/react-query";
import { helpApi } from "@/services/api/help";
import type {
  HelpArticleListResponse,
  GettingStartedResponse,
} from "@/types/api";

/** Query keys for help domain. */
export const helpKeys = {
  all: ["help"] as const,
  articles: (category?: string) =>
    [...helpKeys.all, "articles", category] as const,
  gettingStarted: [...(["help", "getting-started"] as const)] as const,
};

/**
 * Fetch FAQ articles, optionally filtered by category.
 */
export function useHelpArticles(category?: string) {
  return useQuery<HelpArticleListResponse, Error>({
    queryKey: helpKeys.articles(category),
    queryFn: () => helpApi.listArticles(category),
    staleTime: 5 * 60 * 1000, // Help content rarely changes
  });
}

/**
 * Fetch the getting-started guide.
 */
export function useGettingStarted() {
  return useQuery<GettingStartedResponse, Error>({
    queryKey: helpKeys.gettingStarted,
    queryFn: () => helpApi.gettingStarted(),
    staleTime: 10 * 60 * 1000,
  });
}
