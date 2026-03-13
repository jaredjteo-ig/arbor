/* ── Search Hooks ─────────────────────────────────────────── */

"use client";

import { useMutation } from "@tanstack/react-query";
import { searchApi } from "@/services/api/search";
import type {
  SemanticSearchRequest,
  SemanticSearchResponse,
  FulltextSearchRequest,
  FulltextSearchResponse,
} from "@/types/api";

/**
 * Perform a semantic (vector) search.
 * Mutation because the user submits a search query to trigger it.
 */
export function useSemanticSearch() {
  return useMutation<SemanticSearchResponse, Error, SemanticSearchRequest>({
    mutationFn: (data) => searchApi.semantic(data),
  });
}

/**
 * Perform a full-text search with optional filters.
 */
export function useFulltextSearch() {
  return useMutation<FulltextSearchResponse, Error, FulltextSearchRequest>({
    mutationFn: (data) => searchApi.fulltext(data),
  });
}
