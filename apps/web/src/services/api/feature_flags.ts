/* ── Feature Flags API Service ────────────────────────────── *
 *
 * Round-13 S1-T2: server-side feature flags. The flag truth lives on the
 * company record, not in localStorage. This module wraps the two
 * endpoints exposed by `routers/feature_flags.py`:
 *
 *   GET   /companies/me/feature-flags  — any authenticated user
 *   PATCH /companies/me/feature-flags  — owners only (merge semantics)
 *
 * Frontends should NEVER read or write `localStorage.arbor.*` for these
 * three flags any more — call this client and let `AuthContext` cache
 * the result. Falling back to `false` is the right behaviour when the
 * API is unreachable; never treat localStorage as a source of truth.
 */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

/** Allow-listed flag keys mirrored from `routers/feature_flags.py`. */
export const FEATURE_FLAG_KEYS = [
  "ai-scorecards",
  "tafep-ai",
  "chat-onboarding",
] as const;

export type FeatureFlagKey = (typeof FEATURE_FLAG_KEYS)[number];

/** Canonical feature-flag map. The backend always returns every key. */
export type FeatureFlags = Record<FeatureFlagKey, boolean>;

export interface FeatureFlagsResponse {
  /** May be null when the user hasn't completed onboarding yet. */
  company_id: number | null;
  flags: FeatureFlags;
  /** True when no company exists yet — flags are pure defaults. */
  defaulted?: boolean;
  /** Set on PATCH responses only. */
  updated_at?: string;
}

/** Default-off baseline; matches the backend's DEFAULT_FLAGS. */
export const DEFAULT_FEATURE_FLAGS: FeatureFlags = {
  "ai-scorecards": false,
  "tafep-ai": false,
  "chat-onboarding": false,
};

/* ── API methods ──────────────────────────────────────────── */

export const featureFlagsApi = {
  /** Fetch the current company's feature flags. */
  get(): Promise<FeatureFlagsResponse> {
    return apiClient.get<FeatureFlagsResponse>("/companies/me/feature-flags");
  },

  /**
   * Merge a partial flag map into the current company's flags.
   * Owner-only on the server side; non-owners get 403.
   */
  update(flags: Partial<FeatureFlags>): Promise<FeatureFlagsResponse> {
    return apiClient.patch<FeatureFlagsResponse>(
      "/companies/me/feature-flags",
      { flags },
    );
  },
};
