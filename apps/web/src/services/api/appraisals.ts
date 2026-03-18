/* ── Appraisals API Service ───────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface AppraisalTemplate {
  id: number;
  company_id: number;
  name: string;
  sections: string;
  enable_weightage: boolean;
  require_employee_signoff: boolean;
  is_archived: boolean;
}

export interface AppraisalPeriod {
  id: number;
  company_id: number;
  template_id: number;
  name: string;
  start_date: string;
  end_date: string;
  status: string;
}

export interface Appraisal {
  id: number;
  period_id: number;
  employee_id: number;
  reviewer_id: number;
  template_id: number;
  status: string;
  responses: string;
  scores: string;
  overall_score: number;
  reviewer_comments: string;
  employee_comments: string;
  employee_name?: string;
  reviewer_name?: string;
}

/* ── API ──────────────────────────────────────────────────── */

export const appraisalsApi = {
  /* Templates */
  listTemplates: () =>
    apiClient.get<{ templates: AppraisalTemplate[]; count: number }>(
      "/appraisals/templates",
    ),
  getTemplate: (id: number) =>
    apiClient.get<AppraisalTemplate>(`/appraisals/templates/${id}`),
  createTemplate: (data: Partial<AppraisalTemplate>) =>
    apiClient.post<AppraisalTemplate>("/appraisals/templates", data),
  updateTemplate: (id: number, data: Partial<AppraisalTemplate>) =>
    apiClient.put<AppraisalTemplate>(`/appraisals/templates/${id}`, data),

  /* Periods */
  listPeriods: () =>
    apiClient.get<{ periods: AppraisalPeriod[]; count: number }>(
      "/appraisals/periods",
    ),
  createPeriod: (data: Partial<AppraisalPeriod>) =>
    apiClient.post<AppraisalPeriod>("/appraisals/periods", data),
  launchPeriod: (id: number) =>
    apiClient.post<{ message: string }>(`/appraisals/periods/${id}/launch`),

  /* Appraisals */
  listAppraisals: (periodId?: number) =>
    apiClient.get<{ appraisals: Appraisal[]; count: number }>(
      "/appraisals/my",
      periodId ? { period_id: String(periodId) } : undefined,
    ),
  getAppraisal: (id: number) => apiClient.get<Appraisal>(`/appraisals/${id}`),
  updateAppraisal: (id: number, data: Partial<Appraisal>) =>
    apiClient.put<Appraisal>(`/appraisals/${id}`, data),
  submitAppraisal: (id: number) =>
    apiClient.post<{ message: string }>(`/appraisals/${id}/submit`),
  signOffAppraisal: (id: number) =>
    apiClient.post<{ message: string }>(`/appraisals/${id}/sign-off`),
};
