/* ── Knowledge Base Hooks ─────────────────────────────────── */

"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { kbApi } from "@/services/api/kb";
import type {
  ActListResponse,
  DomainListResponse,
  Provision,
  KbQueryRequest,
  KbQueryResponse,
} from "@/types/api";

/** Query keys for knowledge base domain. */
export const kbKeys = {
  all: ["kb"] as const,
  acts: () => [...kbKeys.all, "acts"] as const,
  domains: () => [...kbKeys.all, "domains"] as const,
  provision: (provisionId: string) =>
    [...kbKeys.all, "provision", provisionId] as const,
};

/**
 * Fetch all acts in the knowledge base.
 * This is reference data that rarely changes — good candidate for long staleTime.
 */
export function useActs() {
  return useQuery<ActListResponse, Error>({
    queryKey: kbKeys.acts(),
    queryFn: () => kbApi.acts(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch all regulatory domains.
 * Reference data — cached for 5 minutes.
 */
export function useDomains() {
  return useQuery<DomainListResponse, Error>({
    queryKey: kbKeys.domains(),
    queryFn: () => kbApi.domains(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch a specific provision by ID.
 * Only fetches when provisionId is provided.
 */
export function useProvision(provisionId: string) {
  return useQuery<Provision, Error>({
    queryKey: kbKeys.provision(provisionId),
    queryFn: () => kbApi.provision(provisionId),
    enabled: !!provisionId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Query the knowledge base with natural language.
 * Mutation because it is user-initiated and not idempotent caching.
 */
export function useKbQuery() {
  return useMutation<KbQueryResponse, Error, KbQueryRequest>({
    mutationFn: (data) => kbApi.query(data),
  });
}
