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
  salary_range_min: number | null;
  salary_range_max: number | null;
  status: "draft" | "open" | "closed" | "on_hold" | "filled";
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
  created_at: string;
  overall_score: number | null;
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

export interface CandidateActivity {
  id: number;
  candidate_id: number;
  activity_type: string;
  description: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  actor_id?: number | null;
  actor_name?: string | null;
}

export interface ScreeningQuestion {
  id: number;
  job_listing_id: number;
  question_text: string;
  question_type: "text" | "yes_no" | "multiple_choice" | "number";
  is_required: boolean;
  is_knockout: boolean;
  knockout_value?: string | null;
  options?: string[];
  sort_order: number;
}

export interface ScreeningResponse {
  id: number;
  candidate_id: number;
  question_id: number;
  question_text?: string;
  is_knockout?: boolean;
  knockout_value?: string | null;
  answer: string;
  is_failure?: boolean;
  created_at: string;
}

export interface ScorecardCriterion {
  id?: number;
  name: string;
  description?: string;
  weight?: number;
  sort_order?: number;
}

export interface ScorecardTemplate {
  id: number;
  company_id: number;
  name: string;
  description?: string;
  criteria: ScorecardCriterion[];
  is_active: boolean;
  created_at: string;
}

export interface ScorecardEntryScore {
  criterion_id?: number;
  criterion_name: string;
  rating: number; // 1-5
  notes?: string;
}

export interface ScorecardEntry {
  id: number;
  candidate_id: number;
  interview_id?: number | null;
  template_id: number;
  template_name?: string;
  interviewer_id: number;
  interviewer_name?: string;
  scores: ScorecardEntryScore[];
  overall_score?: number;
  notes?: string;
  created_at: string;
}

export interface PublicJobSummary {
  id: number;
  slug?: string;
  title: string;
  department: string;
  location: string;
  employment_type: string;
  description: string;
  requirements?: string;
  salary_range_min: number | null;
  salary_range_max: number | null;
  posted_date: string | null;
  questions?: ScreeningQuestion[];
}

export interface PublicCompanyCareers {
  company: {
    name: string;
    slug: string;
    sector?: string;
    description?: string;
  };
  jobs: PublicJobSummary[];
}

export interface Offer {
  id: number;
  candidate_id: number;
  job_listing_id: number;
  company_id: number;
  salary: number;
  currency: string;
  salary_period: "monthly" | "annual";
  start_date: string;
  position_title: string;
  employment_type: string;
  probation_months: number;
  notice_period_days: number;
  benefits_summary: string;
  terms_text: string;
  status:
    | "draft"
    | "pending_approval"
    | "approved"
    | "sent"
    | "accepted"
    | "declined"
    | "expired";
  expiry_date: string;
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

  /* Resume */
  uploadResume: (candidateId: number, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.postFormData<{ message: string; resume_url: string }>(
      `/recruitment/candidates/${candidateId}/resume`,
      formData,
    );
  },
  getResumeUrl: (candidateId: number) =>
    `/recruitment/candidates/${candidateId}/resume`,

  /* Hiring */
  hireCandidate: (
    candidateId: number,
    data: {
      start_date: string;
      department: string;
      designation: string;
      onboarding_template_id?: number | null;
    },
  ) =>
    apiClient.post<{
      message: string;
      employee_id: number;
      onboarding_assignment_id?: number;
    }>(`/recruitment/candidates/${candidateId}/hire`, data),

  /* Activity timeline (T-R013) — endpoint may not yet be deployed; callers
     should swallow 404 and render an empty-state. */
  listCandidateActivity: (candidateId: number) =>
    apiClient.get<{ activities: CandidateActivity[]; count: number }>(
      `/recruitment/candidates/${candidateId}/activity`,
    ),

  /* Screening questions (T-R033 / T-R034) */
  listJobQuestions: (jobId: number) =>
    apiClient.get<{ questions: ScreeningQuestion[]; count: number }>(
      `/recruitment/jobs/${jobId}/questions`,
    ),
  createJobQuestion: (jobId: number, data: Partial<ScreeningQuestion>) =>
    apiClient.post<{ question: ScreeningQuestion }>(
      `/recruitment/jobs/${jobId}/questions`,
      data,
    ),
  updateJobQuestion: (
    jobId: number,
    questionId: number,
    data: Partial<ScreeningQuestion>,
  ) =>
    apiClient.patch<{ question: ScreeningQuestion }>(
      `/recruitment/jobs/${jobId}/questions/${questionId}`,
      data,
    ),
  deleteJobQuestion: (jobId: number, questionId: number) =>
    apiClient.delete<{ message: string }>(
      `/recruitment/jobs/${jobId}/questions/${questionId}`,
    ),
  listScreeningResponses: (candidateId: number) =>
    apiClient.get<{ responses: ScreeningResponse[]; count: number }>(
      `/recruitment/candidates/${candidateId}/screening-responses`,
    ),

  /* Scorecard (T-R036) — backend may not be deployed yet */
  listScorecardTemplates: () =>
    apiClient.get<{ templates: ScorecardTemplate[]; count: number }>(
      "/recruitment/scorecard-templates",
    ),
  getScorecardTemplate: (id: number) =>
    apiClient.get<{ template: ScorecardTemplate }>(
      `/recruitment/scorecard-templates/${id}`,
    ),
  createScorecardTemplate: (data: {
    name: string;
    description?: string;
    criteria: Array<{ name: string; weight: number }>;
  }) =>
    apiClient.post<{ template: ScorecardTemplate }>(
      "/recruitment/scorecard-templates",
      data,
    ),
  updateScorecardTemplate: (
    id: number,
    data: Partial<{
      name: string;
      description: string;
      criteria: Array<{ name: string; weight: number }>;
      is_active: boolean;
    }>,
  ) =>
    apiClient.patch<{ template: ScorecardTemplate }>(
      `/recruitment/scorecard-templates/${id}`,
      data,
    ),
  deleteScorecardTemplate: (id: number) =>
    apiClient.delete<{ message: string }>(
      `/recruitment/scorecard-templates/${id}`,
    ),
  createScorecardEntry: (data: {
    candidate_id: number;
    interview_id?: number | null;
    template_id: number;
    scores: ScorecardEntryScore[];
    notes?: string;
  }) =>
    apiClient.post<{ entry: ScorecardEntry }>(
      "/recruitment/scorecard-entries",
      data,
    ),
  listCandidateScorecards: (candidateId: number) =>
    apiClient.get<{ entries: ScorecardEntry[]; count: number }>(
      `/recruitment/candidates/${candidateId}/scorecard-entries`,
    ),

  /* T-R054: AI-generated candidate scorecards */
  generateAIScorecard: (candidateId: number, data: { template_id: number }) =>
    apiClient.post<{
      scorecard: {
        template_id: number | null;
        template_name: string;
        overall_fit: number;
        competency_ratings: Record<string, number>;
        strengths: string[];
        concerns: string[];
        recommended_decision: "proceed" | "reject" | "further_interview";
        narrative: string;
        criteria: Array<{ name: string; weight: number }>;
      };
      generation_id: string;
      degraded: boolean;
      persisted_entry_id?: number | null;
    }>(`/recruitment/candidates/${candidateId}/scorecard/generate`, data),

  /* Maintenance sweeps (admin/cron-callable, T-R020 / T-R030) */
  runDataRetentionSweep: () =>
    apiClient.post<{
      eligible_candidates: number;
      notified: number;
      message: string;
    }>("/recruitment/run-data-retention-sweep"),
  runOverdueReminderSweep: () =>
    apiClient.post<{
      reminders_sent: number;
      message: string;
    }>("/recruitment/feedback/run-overdue-reminder-sweep"),

  /* Onboarding templates (used in hire review) */
  listOnboardingTemplatesForHire: () =>
    apiClient.get<{
      templates: Array<{ id: number; name: string; is_default: boolean }>;
      count: number;
    }>("/onboarding/templates"),

  /* Public careers (T-R045 / T-R046) — no auth required */
  getPublicCompanyCareers: async (
    slug: string,
  ): Promise<PublicCompanyCareers> =>
    apiClient.get<PublicCompanyCareers>(`/recruitment/careers/${slug}/jobs`),
  getPublicJob: async (
    slug: string,
    jobSlug: string,
  ): Promise<PublicJobSummary> => {
    const resp = await apiClient.get<{ job: PublicJobSummary }>(
      `/recruitment/careers/${slug}/jobs/${jobSlug}`,
    );
    return (resp as { job: PublicJobSummary }).job;
  },
  submitPublicApplication: (
    slug: string,
    jobSlug: string,
    formData: FormData,
  ) =>
    apiClient.postFormData<{
      message: string;
      reference_number: string;
      candidate_id: number;
    }>(`/recruitment/careers/${slug}/jobs/${jobSlug}/apply`, formData),

  /* TAFEP Compliance Scan — optional `aiCheck` enables LLM second-pass (T-R053) */
  scanJob: (jobId: number, aiCheck = false) => {
    const qs = aiCheck ? "?ai_check=true" : "";
    return apiClient.post<{
      job_id: number;
      findings: Array<{
        matched_text: string;
        category: string;
        suggestion: string;
        field: string;
        position: number;
      }>;
      count: number;
      compliant: boolean;
      ai_unavailable?: boolean;
    }>(`/recruitment/jobs/${jobId}/scan${qs}`);
  },

  /* Offers */
  createOffer: (candidateId: number, data: Partial<Offer>) =>
    apiClient.post<{ offer: Offer }>(
      `/recruitment/candidates/${candidateId}/offer`,
      data,
    ),
  listOffers: (params?: Record<string, string>) =>
    apiClient.get<{ offers: Offer[]; count: number }>(
      "/recruitment/offers",
      params,
    ),
  approveOffer: (offerId: number) =>
    apiClient.post<{ offer: Offer; message: string }>(
      `/recruitment/offers/${offerId}/approve`,
    ),
  sendOffer: (offerId: number) =>
    apiClient.post<{ offer: Offer; message: string }>(
      `/recruitment/offers/${offerId}/send`,
    ),
  getOfferLetterUrl: (offerId: number) =>
    `${process.env.NEXT_PUBLIC_API_URL || ""}/recruitment/offers/${offerId}/letter`,

  /* Analytics */
  getAnalyticsSummary: () =>
    apiClient.get<{
      open_jobs: number;
      total_candidates: number;
      pipeline: Record<string, number>;
      interviews_this_week: number;
      sources: Record<string, number>;
      total_offers: number;
      accepted_offers: number;
      offer_acceptance_rate: number;
    }>("/recruitment/analytics/summary"),

  /* Rejection */
  rejectCandidate: (
    id: number,
    data: { reason: string; notes?: string; send_email?: boolean },
  ) =>
    apiClient.post<{ candidate: Candidate; message: string }>(
      `/recruitment/candidates/${id}/reject`,
      data,
    ),
};
