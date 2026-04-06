/* ── Recruitment API Service ──────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface JobListing {
  id: number;
  company_id: number;
  title: string;
  department: string;
  location: string;
  employment_type: "full_time" | "part_time" | "contract" | "intern";
  description: string;
  requirements: string;
  salary_min: number | null;
  salary_max: number | null;
  status: "draft" | "open" | "closed" | "on_hold";
  posted_date: string | null;
  closing_date: string | null;
  candidate_count?: number;
}

export type CandidateStage =
  | "new"
  | "screening"
  | "interview"
  | "assessment"
  | "offered"
  | "hired"
  | "rejected"
  | "withdrawn";

export interface Candidate {
  id: number;
  job_listing_id: number;
  job_title?: string;
  name: string;
  email: string;
  phone: string;
  resume_url: string;
  stage: CandidateStage;
  source: string;
  notes: string;
  applied_date: string;
  rating: number | null;
}

export interface InterviewSchedule {
  id: number;
  candidate_id: number;
  candidate_name?: string;
  interviewer_id: number;
  interviewer_name?: string;
  scheduled_at: string;
  duration_minutes: number;
  interview_type: "phone" | "video" | "onsite" | "panel";
  location: string;
  status: "scheduled" | "completed" | "cancelled" | "no_show";
  notes: string;
}

export interface InterviewFeedback {
  id: number;
  interview_id: number;
  interviewer_id: number;
  interviewer_name?: string;
  rating: number;
  strengths: string;
  weaknesses: string;
  recommendation: "strong_hire" | "hire" | "no_hire" | "strong_no_hire";
  notes: string;
}

/* ── API ──────────────────────────────────────────────────── */

export const recruitmentApi = {
  /* Job Listings */
  listJobs: () =>
    apiClient.get<{ jobs: JobListing[]; count: number }>("/recruitment/jobs"),
  getJob: async (id: number | string): Promise<JobListing> => {
    const resp = await apiClient.get<{ job: JobListing }>(
      `/recruitment/jobs/${id}`,
    );
    return (resp as { job: JobListing }).job;
  },
  createJob: (data: Partial<JobListing>) =>
    apiClient.post<JobListing>("/recruitment/jobs", data),
  updateJob: (id: number, data: Partial<JobListing>) =>
    apiClient.patch<JobListing>(`/recruitment/jobs/${id}`, data),
  publishJob: (id: number) =>
    apiClient.post<{ message: string }>(`/recruitment/jobs/${id}/publish`),
  closeJob: (id: number) =>
    apiClient.post<{ message: string }>(`/recruitment/jobs/${id}/close`),

  /* Candidates — backend uses /jobs/{jobId}/candidates */
  listCandidates: async (
    jobId?: number,
    params?: Record<string, string>,
  ): Promise<{ candidates: Candidate[]; count: number }> => {
    if (jobId) {
      return apiClient.get<{ candidates: Candidate[]; count: number }>(
        `/recruitment/jobs/${jobId}/candidates`,
        params,
      );
    }
    // Global list: backend has GET /recruitment/candidates
    return apiClient.get<{ candidates: Candidate[]; count: number }>(
      "/recruitment/candidates",
      params,
    );
  },
  getCandidate: async (id: number | string): Promise<Candidate> => {
    const resp = await apiClient.get<{ candidate: Candidate }>(
      `/recruitment/candidates/${id}`,
    );
    return (resp as { candidate: Candidate }).candidate;
  },
  createCandidate: (data: Partial<Candidate>) =>
    apiClient.post<Candidate>(
      `/recruitment/jobs/${data.job_listing_id}/candidates`,
      data,
    ),
  updateCandidate: (id: number, data: Partial<Candidate>) =>
    apiClient.patch<Candidate>(`/recruitment/candidates/${id}`, data),
  moveStage: (id: number, stage: CandidateStage) =>
    apiClient.patch<{ candidate: Candidate }>(`/recruitment/candidates/${id}`, {
      stage,
    }),

  /* Interviews — backend uses /candidates/{candidateId}/interviews */
  listInterviews: async (
    params?: Record<string, string>,
  ): Promise<{ interviews: InterviewSchedule[]; count: number }> => {
    // Global list: backend has GET /recruitment/interviews
    return apiClient.get<{ interviews: InterviewSchedule[]; count: number }>(
      "/recruitment/interviews",
      params,
    );
  },
  scheduleInterview: (data: Partial<InterviewSchedule>) =>
    apiClient.post<InterviewSchedule>(
      `/recruitment/candidates/${data.candidate_id}/interviews`,
      data,
    ),
  cancelInterview: (id: number) =>
    apiClient.patch<{ interview: InterviewSchedule }>(
      `/recruitment/interviews/${id}`,
      { status: "cancelled" },
    ),

  /* Feedback */
  submitFeedback: (interviewId: number, data: Partial<InterviewFeedback>) =>
    apiClient.post<InterviewFeedback>(
      `/recruitment/interviews/${interviewId}/feedback`,
      data,
    ),

  /* Hiring */
  hireCandidate: (
    candidateId: number,
    data: { start_date: string; department: string; designation: string },
  ) =>
    apiClient.post<{ message: string; employee_id: number }>(
      `/recruitment/candidates/${candidateId}/hire`,
      data,
    ),
};
