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
  expense_date: string;
  receipt_url: string | null;
}

export interface Claim {
  id: number;
  employee_id: number;
  employee_name: string;
  title: string;
  status: "draft" | "pending" | "approved" | "rejected";
  total_amount: number;
  items: ClaimItem[];
  approver_id: number | null;
  approver_name: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
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
  title: string;
}

export interface AddClaimItemData {
  category_id: number;
  description: string;
  amount: number;
  expense_date: string;
}

/* ── API Methods ─────────────────────────────────────────── */

export const claimsApi = {
  /** List all claim categories. */
  listCategories(): Promise<{ categories: ClaimCategory[] }> {
    return apiClient.get<{ categories: ClaimCategory[] }>("/claims/categories");
  },

  /** Create a new claim (starts as draft). */
  createClaim(data: CreateClaimData): Promise<Claim> {
    return apiClient.post<Claim>("/claims", data);
  },

  /** List claims with optional filters. */
  listClaims(params?: {
    status?: string;
    employee_id?: string;
  }): Promise<{ claims: Claim[]; count: number }> {
    return apiClient.get<{ claims: Claim[]; count: number }>("/claims", params);
  },

  /** Get a single claim with full details. */
  getClaim(claimId: number): Promise<Claim> {
    return apiClient.get<Claim>(`/claims/${claimId}`);
  },

  /** Submit a draft claim for approval. */
  submitClaim(claimId: number): Promise<Claim> {
    return apiClient.post<Claim>(`/claims/${claimId}/submit`);
  },

  /** Approve a claim (admin). */
  approveClaim(claimId: number): Promise<Claim> {
    return apiClient.post<Claim>(`/claims/${claimId}/approve`);
  },

  /** Reject a claim (admin). */
  rejectClaim(claimId: number, reason: string): Promise<Claim> {
    return apiClient.post<Claim>(`/claims/${claimId}/reject`, { reason });
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
      `/claims/${claimId}/items/${itemId}/receipt`,
      formData,
    );
  },

  /** Get audit trail for a claim. */
  getAuditTrail(claimId: number): Promise<{ entries: AuditTrailEntry[] }> {
    return apiClient.get<{ entries: AuditTrailEntry[] }>(
      `/claims/${claimId}/audit`,
    );
  },
};
