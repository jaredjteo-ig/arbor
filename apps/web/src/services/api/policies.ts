/* ── Policies API Service ─────────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface PolicyRecord {
  id: number;
  company_id: number;
  policy_type: string;
  category: string;
  title: string;
  content: string;
  effective_date: string;
  is_active: boolean;
  version_number: number;
  status: "draft" | "active" | "archived";
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  extraction_status: string;
  requires_acknowledgment: boolean;
  created_at: string;
  updated_at: string;
}

export interface PolicyAcknowledgmentRecord {
  id: number;
  policy_id: number;
  employee_id: number;
  version_acknowledged: number;
  acknowledged_at: string;
}

export interface StatutoryFloorWarning {
  field: string;
  company_value: number | null;
  statutory_minimum: number;
  status: "above_minimum" | "meets_minimum" | "below_minimum" | "not_detected";
  message: string;
}

/* ── API Methods ─────────────────────────────────────────── */

export const policiesApi = {
  /** Admin: list all policies for the current company. */
  list(): Promise<{ policies: PolicyRecord[]; count: number }> {
    return apiClient.get<{ policies: PolicyRecord[]; count: number }>(
      "/policies",
    );
  },

  /** Admin: get a single policy by ID. */
  get(id: number): Promise<PolicyRecord> {
    return apiClient.get<PolicyRecord>(`/policies/${id}`);
  },

  /** Admin: create a new policy record. */
  create(data: Partial<PolicyRecord>): Promise<PolicyRecord> {
    return apiClient.post<PolicyRecord>("/policies", data);
  },

  /** Admin: upload a policy document (PDF/DOCX). */
  upload(formData: FormData): Promise<PolicyRecord> {
    return apiClient.postFormData<PolicyRecord>("/policies/upload", formData);
  },

  /** Admin: update policy metadata. */
  update(id: number, data: Partial<PolicyRecord>): Promise<PolicyRecord> {
    return apiClient.patch<PolicyRecord>(`/policies/${id}`, data);
  },

  /** Admin: update extracted policy content. */
  updateContent(id: number, content: string): Promise<PolicyRecord> {
    return apiClient.patch<PolicyRecord>(`/policies/${id}/content`, {
      content,
    });
  },

  /** Admin: archive a policy (soft delete). */
  archive(id: number): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/policies/${id}/archive`);
  },

  /** Admin: list all versions of a policy. */
  versions(id: number): Promise<{ versions: PolicyRecord[]; count: number }> {
    return apiClient.get<{ versions: PolicyRecord[]; count: number }>(
      `/policies/${id}/versions`,
    );
  },

  /** Employee: acknowledge a policy version. */
  acknowledge(
    id: number,
    versionNumber: number,
  ): Promise<PolicyAcknowledgmentRecord> {
    return apiClient.post<PolicyAcknowledgmentRecord>(
      `/policies/${id}/acknowledge`,
      { version_number: versionNumber },
    );
  },

  /** Admin: list acknowledgments for a policy. */
  acknowledgments(id: number): Promise<{
    acknowledgments: PolicyAcknowledgmentRecord[];
    count: number;
  }> {
    return apiClient.get<{
      acknowledgments: PolicyAcknowledgmentRecord[];
      count: number;
    }>(`/policies/${id}/acknowledgments`);
  },

  /** Employee: list policies pending acknowledgment. */
  pendingAcknowledgments(): Promise<{
    pending_policies: PolicyRecord[];
    count: number;
  }> {
    return apiClient.get<{ pending_policies: PolicyRecord[]; count: number }>(
      "/policies/pending-acknowledgments",
    );
  },

  /** Admin: run statutory floor compliance check for a policy. */
  complianceCheck(id: number): Promise<{
    policy_id: number;
    warnings: StatutoryFloorWarning[];
    compliant: boolean;
  }> {
    return apiClient.get<{
      policy_id: number;
      warnings: StatutoryFloorWarning[];
      compliant: boolean;
    }>(`/policies/${id}/compliance-check`);
  },
};
