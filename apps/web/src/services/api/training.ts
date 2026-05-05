/* ── Training (L&D) API Service ───────────────────────────── */
/*  P2-LD obayashi. Backed by /training/* endpoints.            */

import { apiClient } from "./client";

export interface TrainingRecord {
  id: number;
  company_id: number;
  employee_id: number;
  course_name: string;
  course_provider: string;
  course_type: "internal" | "external" | "skillsfuture";
  start_date: string;
  completion_date: string;
  hours: number;
  cost: number;
  funding_source: "self" | "employer" | "skillsfuture_credit";
  certificate_url: string;
  notes: string;
  is_archived: boolean;
}

export interface Certification {
  id: number;
  company_id: number;
  employee_id: number;
  certification_name: string;
  issuing_body: string;
  issued_date: string;
  expires_at: string;
  cert_number: string;
  attachment_url: string;
  notes: string;
  is_archived: boolean;
}

export interface MandatoryRequirement {
  id: number;
  company_id: number;
  requirement_name: string;
  applicable_to: string;
  required_certification_name: string;
  due_within_days_of_hire: number;
  is_active: boolean;
  notes: string;
}

export interface CoverageRow {
  requirement_id: number;
  requirement_name: string;
  applicable_to: string;
  applicable_count: number;
  compliant_count: number;
  non_compliant_employee_ids: number[];
}

export interface CoverageResponse {
  coverage: CoverageRow[];
  totals: {
    compliant_pairs: number;
    total_pairs: number;
    rate: number;
  };
}

export const trainingApi = {
  // Records
  listRecords: (filters?: {
    employee_id?: number;
    course_type?: string;
    include_archived?: boolean;
  }) => {
    const qs = new URLSearchParams();
    if (filters?.employee_id !== undefined)
      qs.set("employee_id", String(filters.employee_id));
    if (filters?.course_type) qs.set("course_type", filters.course_type);
    if (filters?.include_archived) qs.set("include_archived", "true");
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return apiClient.get<{ records: TrainingRecord[]; count: number }>(
      `/training/records${suffix}`,
    );
  },
  createRecord: (data: Partial<TrainingRecord>) =>
    apiClient.post<{ record: TrainingRecord }>("/training/records", data),
  updateRecord: (id: number, data: Partial<TrainingRecord>) =>
    apiClient.patch<{ record: TrainingRecord }>(
      `/training/records/${id}`,
      data,
    ),
  archiveRecord: (id: number) =>
    apiClient.delete<{ id: number }>(`/training/records/${id}`),

  // Certifications
  listCertifications: (filters?: {
    employee_id?: number;
    include_archived?: boolean;
  }) => {
    const qs = new URLSearchParams();
    if (filters?.employee_id !== undefined)
      qs.set("employee_id", String(filters.employee_id));
    if (filters?.include_archived) qs.set("include_archived", "true");
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return apiClient.get<{ certifications: Certification[]; count: number }>(
      `/training/certifications${suffix}`,
    );
  },
  expiringCertifications: (within_days = 30) =>
    apiClient.get<{
      expired: Certification[];
      expiring: Certification[];
      active_total: number;
      within_days: number;
    }>(`/training/certifications/expiring?within_days=${within_days}`),
  createCertification: (data: Partial<Certification>) =>
    apiClient.post<{ certification: Certification }>(
      "/training/certifications",
      data,
    ),
  updateCertification: (id: number, data: Partial<Certification>) =>
    apiClient.patch<{ certification: Certification }>(
      `/training/certifications/${id}`,
      data,
    ),
  archiveCertification: (id: number) =>
    apiClient.delete<{ id: number }>(`/training/certifications/${id}`),

  // Mandatory requirements
  listMandatory: () =>
    apiClient.get<{ requirements: MandatoryRequirement[]; count: number }>(
      "/training/mandatory",
    ),
  createMandatory: (data: Partial<MandatoryRequirement>) =>
    apiClient.post<{ requirement: MandatoryRequirement }>(
      "/training/mandatory",
      data,
    ),
  updateMandatory: (id: number, data: Partial<MandatoryRequirement>) =>
    apiClient.patch<{ requirement: MandatoryRequirement }>(
      `/training/mandatory/${id}`,
      data,
    ),
  mandatoryCoverage: () =>
    apiClient.get<CoverageResponse>("/training/mandatory/coverage"),
};
