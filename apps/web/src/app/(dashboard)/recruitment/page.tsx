"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  UserPlus,
  Plus,
  Briefcase,
  X,
  Users,
  Calendar,
  ChevronRight,
  CheckCircle,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  recruitmentApi,
  type JobListing,
  type Candidate,
  type CandidateStage,
  type InterviewSchedule,
} from "@/services/api/recruitment";

/* ── Helpers ──────────────────────────────────────────────── */

function formatDate(d: string): string {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("en-SG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/* ── Status styles ────────────────────────────────────────── */

const JOB_STATUS_STYLES: Record<string, string> = {
  draft:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
  open: "bg-emerald-50 text-emerald-700 border-emerald-200",
  closed: "bg-red-50 text-red-700 border-red-200",
  on_hold: "bg-amber-50 text-amber-700 border-amber-200",
};

const STAGE_STYLES: Record<string, string> = {
  new: "bg-blue-50 text-blue-700 border-blue-200",
  screening: "bg-violet-50 text-violet-700 border-violet-200",
  interview: "bg-amber-50 text-amber-700 border-amber-200",
  assessment: "bg-orange-50 text-orange-700 border-orange-200",
  offered: "bg-teal-50 text-teal-700 border-teal-200",
  hired: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
  withdrawn:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
};

function StatusBadge({
  status,
  styles,
}: {
  status: string;
  styles: Record<string, string>;
}) {
  const label = (status || "new").replace(/_/g, " ");
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${styles[safeStatus] || styles.new || ""}`}
    >
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
}

/* ── Tab button ───────────────────────────────────────────── */

type Tab = "jobs" | "candidates" | "interviews";

function TabButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        active
          ? "bg-[var(--color-primary)] text-white"
          : "text-[var(--color-gray-600)] hover:bg-[var(--color-gray-100)]"
      }`}
    >
      {label}
    </button>
  );
}

/* ── Skeleton ─────────────────────────────────────────────── */

function TableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-5 border-b border-[var(--color-gray-100)] last:border-0"
        >
          <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* ── Create Job Modal ─────────────────────────────────────── */

function CreateJobModal({
  isOpen,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [location, setLocation] = useState("");
  const [employmentType, setEmploymentType] = useState("full_time");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setIsSubmitting(true);
    try {
      await recruitmentApi.createJob({
        title: title.trim(),
        department: department.trim(),
        location: location.trim(),
        employment_type: employmentType as JobListing["employment_type"],
        description: description.trim(),
      });
      toast.success("Job listing created");
      setTitle("");
      setDepartment("");
      setLocation("");
      setDescription("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to create job listing";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              New Job Listing
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <AppInput
            label="Job Title"
            value={title}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setTitle(e.target.value)
            }
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <AppInput
              label="Department"
              value={department}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setDepartment(e.target.value)
              }
            />
            <AppInput
              label="Location"
              value={location}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setLocation(e.target.value)
              }
              placeholder="e.g. Singapore"
            />
          </div>
          <div>
            <label
              htmlFor="emp-type"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Employment Type
            </label>
            <select
              id="emp-type"
              value={employmentType}
              onChange={(e) => setEmploymentType(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
            >
              <option value="full_time">Full-time</option>
              <option value="part_time">Part-time</option>
              <option value="contract">Contract</option>
              <option value="intern">Intern</option>
            </select>
          </div>
          <AppInput
            variant="textarea"
            label="Description"
            value={description}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
              setDescription(e.target.value)
            }
            placeholder="Job description and requirements..."
          />
          <div className="flex gap-3 pt-2">
            <AppButton
              type="button"
              variant="outlined"
              size="sm"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </AppButton>
            <AppButton
              type="submit"
              variant="primary"
              size="sm"
              loading={isSubmitting}
              className="flex-1"
            >
              Create Listing
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Add Candidate Modal ──────────────────────────────────── */

function AddCandidateModal({
  isOpen,
  onClose,
  onSuccess,
  jobs,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  jobs: JobListing[];
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [source, setSource] = useState("direct");
  const [jobId, setJobId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !jobId) return;
    setIsSubmitting(true);
    try {
      await recruitmentApi.createCandidate({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        source,
        job_listing_id: Number(jobId),
      });
      toast.success("Candidate added");
      setName("");
      setEmail("");
      setPhone("");
      setSource("direct");
      setJobId("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to add candidate";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Add Candidate
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <AppInput
            label="Name"
            value={name}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setName(e.target.value)
            }
            required
          />
          <AppInput
            label="Email"
            value={email}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setEmail(e.target.value)
            }
            required
          />
          <AppInput
            label="Phone"
            value={phone}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setPhone(e.target.value)
            }
          />
          <div>
            <label
              htmlFor="cand-source"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Source
            </label>
            <select
              id="cand-source"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
            >
              <option value="direct">Direct</option>
              <option value="referral">Referral</option>
              <option value="job_board">Job Board</option>
              <option value="linkedin">LinkedIn</option>
              <option value="agency">Agency</option>
              <option value="career_fair">Career Fair</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="cand-job"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Job Listing
            </label>
            <select
              id="cand-job"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              required
            >
              <option value="">Select job listing</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <AppButton
              type="button"
              variant="outlined"
              size="sm"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </AppButton>
            <AppButton
              type="submit"
              variant="primary"
              size="sm"
              loading={isSubmitting}
              className="flex-1"
            >
              Add Candidate
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Schedule Interview Modal ────────────────────────────── */

function ScheduleInterviewModal({
  isOpen,
  onClose,
  onSuccess,
  candidateId,
  candidateName,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  candidateId: number;
  candidateName: string;
}) {
  const [interviewType, setInterviewType] = useState("onsite");
  const [scheduledAt, setScheduledAt] = useState("");
  const [duration, setDuration] = useState("60");
  const [location, setLocation] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!scheduledAt) return;
    setIsSubmitting(true);
    try {
      await recruitmentApi.scheduleInterview({
        candidate_id: candidateId,
        interview_type: interviewType as InterviewSchedule["interview_type"],
        scheduled_at: scheduledAt,
        duration_minutes: Number(duration) || 60,
        location: location.trim(),
      });
      toast.success("Interview scheduled");
      setScheduledAt("");
      setLocation("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to schedule interview";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Schedule Interview
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>
        <p className="text-sm text-[var(--color-gray-600)] mb-4">
          For{" "}
          <span className="font-medium text-[var(--color-gray-900)]">
            {candidateName}
          </span>
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="iv-type"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Interview Type
            </label>
            <select
              id="iv-type"
              value={interviewType}
              onChange={(e) => setInterviewType(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
            >
              <option value="phone">Phone</option>
              <option value="video">Video</option>
              <option value="onsite">On-site</option>
              <option value="panel">Panel</option>
            </select>
          </div>
          <AppInput
            label="Date & Time"
            variant="datetime-local"
            value={scheduledAt}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setScheduledAt(e.target.value)
            }
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <AppInput
              label="Duration (min)"
              value={duration}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setDuration(e.target.value)
              }
            />
            <AppInput
              label="Location"
              value={location}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setLocation(e.target.value)
              }
              placeholder="e.g. Meeting Room A"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <AppButton
              type="button"
              variant="outlined"
              size="sm"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </AppButton>
            <AppButton
              type="submit"
              variant="primary"
              size="sm"
              loading={isSubmitting}
              className="flex-1"
            >
              Schedule
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Candidate Pipeline ───────────────────────────────────── */

const PIPELINE_STAGES: CandidateStage[] = [
  "new",
  "screening",
  "interview",
  "offered",
  "hired",
];

const NEXT_STAGE: Partial<Record<CandidateStage, CandidateStage>> = {
  new: "screening",
  screening: "interview",
  interview: "offered",
};

function CandidatePipeline({
  candidates,
  onMoveStage,
  onScheduleInterview,
  onHire,
}: {
  candidates: Candidate[];
  onMoveStage: (id: number, stage: CandidateStage) => void;
  onScheduleInterview: (candidate: Candidate) => void;
  onHire: (candidateId: number) => void;
}) {
  if (candidates.length === 0) {
    return (
      <EmptyState
        icon={<Users className="h-12 w-12" aria-hidden="true" />}
        message="No candidates yet"
        description="Candidates will appear here as they apply."
      />
    );
  }

  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {PIPELINE_STAGES.map((stage) => {
        const stageCandidates = candidates.filter((c) => c.stage === stage);
        return (
          <div key={stage} className="min-w-[220px] flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                {stage.charAt(0).toUpperCase() + stage.slice(1)}
              </h3>
              <span className="inline-flex items-center justify-center h-5 min-w-[20px] px-1 rounded-full bg-[var(--color-gray-200)] text-[10px] font-bold text-[var(--color-gray-600)]">
                {stageCandidates.length}
              </span>
            </div>
            <div className="space-y-2">
              {stageCandidates.map((c) => (
                <div
                  key={c.id}
                  className="rounded-lg border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-3"
                >
                  <p className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                    {c.name}
                  </p>
                  <p className="text-xs text-[var(--color-gray-500)] truncate">
                    {c.email}
                  </p>
                  {c.job_title && (
                    <p className="text-xs text-[var(--color-gray-500)] mt-1">
                      {c.job_title}
                    </p>
                  )}
                  {c.rating !== null && c.rating > 0 && (
                    <div className="flex items-center gap-1 mt-1">
                      {Array.from({ length: 5 }, (_, i) => (
                        <div
                          key={i}
                          className={`h-1.5 w-1.5 rounded-full ${i < (c.rating ?? 0) ? "bg-amber-400" : "bg-[var(--color-gray-200)]"}`}
                        />
                      ))}
                    </div>
                  )}
                  {/* Action buttons */}
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {NEXT_STAGE[c.stage] && (
                      <button
                        type="button"
                        onClick={() => onMoveStage(c.id, NEXT_STAGE[c.stage]!)}
                        className="inline-flex items-center gap-0.5 px-2 py-1 rounded text-[10px] font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
                      >
                        <ChevronRight className="h-3 w-3" />
                        {(NEXT_STAGE[c.stage] ?? "").charAt(0).toUpperCase() +
                          (NEXT_STAGE[c.stage] ?? "").slice(1)}
                      </button>
                    )}
                    {(c.stage === "screening" || c.stage === "interview") && (
                      <button
                        type="button"
                        onClick={() => onScheduleInterview(c)}
                        className="inline-flex items-center gap-0.5 px-2 py-1 rounded text-[10px] font-medium bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors"
                      >
                        <Calendar className="h-3 w-3" />
                        Interview
                      </button>
                    )}
                    {c.stage === "offered" && (
                      <button
                        type="button"
                        onClick={() => onHire(c.id)}
                        className="inline-flex items-center gap-0.5 px-2 py-1 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors"
                      >
                        <CheckCircle className="h-3 w-3" />
                        Hire
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {stageCandidates.length === 0 && (
                <div className="rounded-lg border border-dashed border-[var(--color-gray-200)] p-4 text-center">
                  <p className="text-xs text-[var(--color-gray-400)]">
                    No candidates
                  </p>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function RecruitmentPage() {
  const { user } = useAuth();
  const isAdmin =
    user?.role === "owner" ||
    user?.role === "hr_manager" ||
    user?.role === "consultant";

  const [tab, setTab] = useState<Tab>("jobs");
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [interviews, setInterviews] = useState<InterviewSchedule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showJobModal, setShowJobModal] = useState(false);
  const [showCandidateModal, setShowCandidateModal] = useState(false);
  const [interviewTarget, setInterviewTarget] = useState<{
    id: number;
    name: string;
  } | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [jobsRes, candidatesRes, interviewsRes] = await Promise.all([
        recruitmentApi.listJobs(),
        recruitmentApi.listCandidates(),
        recruitmentApi.listInterviews(),
      ]);
      setJobs(jobsRes.jobs ?? []);
      setCandidates(candidatesRes.candidates ?? []);
      setInterviews(interviewsRes.interviews ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load recruitment data.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handlePublish(jobId: number) {
    try {
      await recruitmentApi.publishJob(jobId);
      toast.success("Job listing published");
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to publish listing";
      toast.error(message);
    }
  }

  async function handleMoveStage(candidateId: number, stage: CandidateStage) {
    try {
      await recruitmentApi.moveStage(candidateId, stage);
      toast.success(`Candidate moved to ${stage}`);
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to move candidate";
      toast.error(message);
    }
  }

  async function handleHire(candidateId: number) {
    try {
      await recruitmentApi.hireCandidate(candidateId, {
        start_date: new Date().toISOString().slice(0, 10),
        department: "",
        designation: "",
      });
      toast.success("Candidate hired and invitation sent");
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to hire candidate";
      toast.error(message);
    }
  }

  if (error && !isLoading) {
    return (
      <div className="max-w-5xl mx-auto space-y-6 pb-8">
        <div className="flex items-center gap-3">
          <UserPlus
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Recruitment
          </h1>
        </div>
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={fetchData}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <UserPlus
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Recruitment
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Manage job listings, candidates, and interviews
            </p>
          </div>
        </div>
        {isAdmin && (
          <AppButton
            variant="primary"
            size="sm"
            onClick={() => setShowJobModal(true)}
          >
            <Plus className="h-4 w-4 mr-1" /> New Job Listing
          </AppButton>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-lg bg-[var(--color-gray-100)] w-fit">
        <TabButton
          active={tab === "jobs"}
          label="Job Listings"
          onClick={() => setTab("jobs")}
        />
        <TabButton
          active={tab === "candidates"}
          label="Candidates"
          onClick={() => setTab("candidates")}
        />
        <TabButton
          active={tab === "interviews"}
          label="Interviews"
          onClick={() => setTab("interviews")}
        />
      </div>

      {/* Jobs Tab */}
      {tab === "jobs" && (
        <>
          {isLoading ? (
            <AppCard variant="standard">
              <div className="-mx-5 -my-4">
                <TableSkeleton />
              </div>
            </AppCard>
          ) : jobs.length === 0 ? (
            <EmptyState
              icon={<Briefcase className="h-12 w-12" aria-hidden="true" />}
              message="No job listings"
              description="Create your first job listing to start hiring."
            />
          ) : (
            <AppCard variant="standard">
              <div className="overflow-x-auto -mx-5 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--color-gray-200)]">
                      <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Title
                      </th>
                      <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Department
                      </th>
                      <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Type
                      </th>
                      <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Candidates
                      </th>
                      <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Status
                      </th>
                      <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map((job) => (
                      <tr
                        key={job.id}
                        className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                      >
                        <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                          {job.title || (job as any).position_title || "-"}
                        </td>
                        <td className="py-3 px-3 text-[var(--color-gray-600)]">
                          {job.department || "-"}
                        </td>
                        <td className="py-3 px-3 text-[var(--color-gray-600)]">
                          {(job.employment_type || "full_time").replace(
                            /_/g,
                            " ",
                          )}
                        </td>
                        <td className="py-3 px-3 text-center text-[var(--color-gray-700)]">
                          {job.candidate_count ?? 0}
                        </td>
                        <td className="py-3 px-3 text-center">
                          <StatusBadge
                            status={job.status}
                            styles={JOB_STATUS_STYLES}
                          />
                        </td>
                        <td className="py-3 px-5 text-center">
                          {job.status === "draft" && (
                            <AppButton
                              variant="primary"
                              size="sm"
                              onClick={() => handlePublish(job.id)}
                            >
                              Publish
                            </AppButton>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AppCard>
          )}
        </>
      )}

      {/* Candidates Tab */}
      {tab === "candidates" && (
        <>
          {isAdmin && (
            <div className="flex justify-end">
              <AppButton
                variant="primary"
                size="sm"
                onClick={() => setShowCandidateModal(true)}
              >
                <Plus className="h-4 w-4 mr-1" /> Add Candidate
              </AppButton>
            </div>
          )}
          {isLoading ? (
            <AppCard variant="standard">
              <div className="-mx-5 -my-4">
                <TableSkeleton />
              </div>
            </AppCard>
          ) : (
            <CandidatePipeline
              candidates={candidates}
              onMoveStage={handleMoveStage}
              onScheduleInterview={(c) =>
                setInterviewTarget({ id: c.id, name: c.name })
              }
              onHire={handleHire}
            />
          )}
        </>
      )}

      {/* Interviews Tab */}
      {tab === "interviews" && (
        <>
          {isLoading ? (
            <AppCard variant="standard">
              <div className="-mx-5 -my-4">
                <TableSkeleton />
              </div>
            </AppCard>
          ) : interviews.length === 0 ? (
            <EmptyState
              icon={<Calendar className="h-12 w-12" aria-hidden="true" />}
              message="No interviews scheduled"
              description="Scheduled interviews will appear here."
            />
          ) : (
            <AppCard variant="standard">
              <div className="overflow-x-auto -mx-5 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--color-gray-200)]">
                      <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Candidate
                      </th>
                      <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Interviewer
                      </th>
                      <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Date
                      </th>
                      <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Type
                      </th>
                      <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {interviews.map((iv) => (
                      <tr
                        key={iv.id}
                        className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                      >
                        <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                          {iv.candidate_name || `#${iv.candidate_id}`}
                        </td>
                        <td className="py-3 px-3 text-[var(--color-gray-600)]">
                          {iv.interviewer_name || `#${iv.interviewer_id}`}
                        </td>
                        <td className="py-3 px-3 text-[var(--color-gray-600)]">
                          {formatDate(iv.scheduled_at)}
                        </td>
                        <td className="py-3 px-3 text-center text-[var(--color-gray-600)]">
                          {iv.interview_type}
                        </td>
                        <td className="py-3 px-5 text-center">
                          <StatusBadge
                            status={iv.status}
                            styles={JOB_STATUS_STYLES}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AppCard>
          )}
        </>
      )}

      <CreateJobModal
        isOpen={showJobModal}
        onClose={() => setShowJobModal(false)}
        onSuccess={fetchData}
      />

      <AddCandidateModal
        isOpen={showCandidateModal}
        onClose={() => setShowCandidateModal(false)}
        onSuccess={fetchData}
        jobs={jobs}
      />

      <ScheduleInterviewModal
        isOpen={interviewTarget !== null}
        onClose={() => setInterviewTarget(null)}
        onSuccess={fetchData}
        candidateId={interviewTarget?.id ?? 0}
        candidateName={interviewTarget?.name ?? ""}
      />
    </div>
  );
}
