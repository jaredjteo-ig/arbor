/* ── Claims API Service ───────────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface ClaimCategory {
  id: number;
  name: string;
  description: string;
  max_amount: number | null;
  requires_receipt: boolean;
  is_active: boolean;
}

export interface ClaimItem {
  id: number;
  claim_id: number;
  category_id: number;
  category_name: string;
  description: string;
  amount: number;
  receipt_date: string;
  receipt_files: string[] | null;
}

export interface Claim {
  id: number;
  employee_id: number;
  employee_name: string;
  claim_month: string;
  status: "draft" | "pending_approval" | "approved" | "rejected";
  total_amount: number;
  items: ClaimItem[];
  reviewed_by: number | null;
  reviewed_at: string | null;
  reviewer_remarks: string | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditTrailEntry {
  id: number;
  action: string;
  actor_name: string;
  timestamp: string;
  details: string;
}

export interface CreateClaimData {
  claim_month: string;
}

export interface AddClaimItemData {
  category_id: number;
  description: string;
  amount: number;
  receipt_date: string;
}

/* ── API Methods ─────────────────────────────────────────── */

export const claimsApi = {
  /** List all claim categories. */
  listCategories(): Promise<{ categories: ClaimCategory[] }> {
    return apiClient.get<{ categories: ClaimCategory[] }>("/claims/categories");
  },

  /** Create a new claim (starts as draft). */
  async createClaim(data: CreateClaimData): Promise<Claim> {
    const response = await apiClient.post<{ claim: Claim }>("/claims", data);
    return response.claim;
  },

  /** List claims with optional filters. */
  listClaims(params?: {
    status?: string;
    employee_id?: string;
  }): Promise<{ claims: Claim[]; count: number }> {
    return apiClient.get<{ claims: Claim[]; count: number }>("/claims", params);
  },

  /** Get a single claim with full details. */
  async getClaim(claimId: number): Promise<Claim> {
    const response = await apiClient.get<{
      claim: Record<string, unknown>;
      items: ClaimItem[];
    }>(`/claims/${claimId}`);
    return { ...response.claim, items: response.items } as Claim;
  },

  /** Submit a draft claim for approval. */
  submitClaim(claimId: number): Promise<Claim> {
    return apiClient.patch<Claim>(`/claims/${claimId}/submit`);
  },

  /** Approve a claim (admin). */
  approveClaim(claimId: number): Promise<Claim> {
    return apiClient.patch<Claim>(`/claims/${claimId}/approve`);
  },

  /** Reject a claim (admin). */
  rejectClaim(claimId: number, reason: string): Promise<Claim> {
    return apiClient.patch<Claim>(`/claims/${claimId}/reject`, {
      reviewer_remarks: reason,
    });
  },

  /** Add a line item to a draft claim. */
  addItem(claimId: number, data: AddClaimItemData): Promise<ClaimItem> {
    return apiClient.post<ClaimItem>(`/claims/${claimId}/items`, data);
  },

  /** Upload a receipt for a claim item. */
  uploadReceipt(
    claimId: number,
    itemId: number,
    formData: FormData,
  ): Promise<{ url: string }> {
    return apiClient.postFormData<{ url: string }>(
      `/claims/${claimId}/items/${itemId}/receipts`,
      formData,
    );
  },

  /** Get audit trail for a claim. */
  getAuditTrail(claimId: number): Promise<{ entries: AuditTrailEntry[] }> {
    return apiClient.get<{ entries: AuditTrailEntry[] }>(
      `/claims/${claimId}/audit-trail`,
    );
  },
};
