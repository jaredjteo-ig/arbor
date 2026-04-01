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
      "/policies/",
    );
  },

  /** Admin: get a single policy by ID. */
  async get(id: number): Promise<PolicyRecord> {
    const data = await apiClient.get<{ policy: PolicyRecord }>(
      `/policies/${id}`,
    );
    return (
      (data as { policy: PolicyRecord }).policy ??
      (data as unknown as PolicyRecord)
    );
  },

  /** Admin: create a new policy record. */
  async create(data: Partial<PolicyRecord>): Promise<PolicyRecord> {
    const resp = await apiClient.post<{ policy: PolicyRecord }>(
      "/policies/",
      data,
    );
    return (
      (resp as { policy: PolicyRecord }).policy ??
      (resp as unknown as PolicyRecord)
    );
  },

  /** Admin: upload a policy document (PDF/DOCX). */
  async upload(formData: FormData): Promise<PolicyRecord> {
    const resp = await apiClient.postFormData<{ policy: PolicyRecord }>(
      "/policies/upload",
      formData,
    );
    return (
      (resp as { policy: PolicyRecord }).policy ??
      (resp as unknown as PolicyRecord)
    );
  },

  /** Admin: update policy metadata. */
  async update(id: number, data: Partial<PolicyRecord>): Promise<PolicyRecord> {
    const resp = await apiClient.patch<{ policy: PolicyRecord }>(
      `/policies/${id}`,
      data,
    );
    return (
      (resp as { policy: PolicyRecord }).policy ??
      (resp as unknown as PolicyRecord)
    );
  },

  /** Admin: update extracted policy content. */
  updateContent(
    id: number,
    content: string,
  ): Promise<{ policy_id: number; message: string }> {
    return apiClient.put<{ policy_id: number; message: string }>(
      `/policies/${id}/content`,
      {
        content,
      },
    );
  },

  /** Admin: archive a policy (soft delete). */
  archive(id: number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/policies/${id}`);
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
