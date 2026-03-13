/* ── Profile Hooks ────────────────────────────────────────── */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { profileApi } from "@/services/api/profile";
import type {
  CompanyProfile,
  CompanyProfileCreateRequest,
  CompanyProfileUpdateRequest,
  CompanyProfileUpdateResponse,
  WorkforceBreakdown,
} from "@/types/api";

/** Query keys for profile domain. */
export const profileKeys = {
  all: ["profile"] as const,
  detail: (companyId: number) =>
    [...profileKeys.all, "detail", companyId] as const,
  workforce: (companyId: number) =>
    [...profileKeys.all, "workforce", companyId] as const,
};

/**
 * Fetch a company profile by ID.
 * Only fetches when companyId is provided (> 0).
 */
export function useCompanyProfile(companyId: number) {
  return useQuery<CompanyProfile, Error>({
    queryKey: profileKeys.detail(companyId),
    queryFn: () => profileApi.get(companyId),
    enabled: companyId > 0,
  });
}

/**
 * Fetch workforce breakdown for a company.
 * Only fetches when companyId is provided (> 0).
 */
export function useWorkforceBreakdown(companyId: number) {
  return useQuery<WorkforceBreakdown, Error>({
    queryKey: profileKeys.workforce(companyId),
    queryFn: () => profileApi.workforce(companyId),
    enabled: companyId > 0,
  });
}

/**
 * Create a new company profile.
 * Invalidates the profile list/detail caches on success.
 */
export function useCreateProfile() {
  const queryClient = useQueryClient();

  return useMutation<
    {
      id: number | null;
      name: string;
      uen: string | null;
      sector: string | null;
      created: boolean;
      timestamp: string;
    },
    Error,
    CompanyProfileCreateRequest
  >({
    mutationFn: (data) => profileApi.create(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: profileKeys.all });
    },
  });
}

/**
 * Update an existing company profile.
 * Invalidates the specific profile cache on success.
 */
export function useUpdateProfile(companyId: number) {
  const queryClient = useQueryClient();

  return useMutation<
    CompanyProfileUpdateResponse,
    Error,
    CompanyProfileUpdateRequest
  >({
    mutationFn: (data) => profileApi.update(companyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: profileKeys.detail(companyId),
      });
    },
  });
}
