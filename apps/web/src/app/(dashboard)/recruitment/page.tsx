"use client";

import { useState, useEffect, useCallback, useMemo, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
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
  Download,
  ExternalLink,
  Search,
  Filter,
  Loader2,
  FileText,
  Mail,
  Phone as PhoneIcon,
  MapPin,
  Clock,
  XCircle,
  ShieldCheck,
  Star,
  DollarSign,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  recruitmentApi,
  type JobListing,
  type Candidate,
  type CandidateStage,
  type InterviewSchedule,
  type Offer,
  type InterviewFeedback,
  type CandidateActivity,
  type ScreeningResponse,
  type ScreeningQuestion,
  type ScorecardEntry,
  type ScorecardTemplate,
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
  // "published" was renamed to "open" — keep alias so historical records render correctly
  published: "bg-emerald-50 text-emerald-700 border-emerald-200",
  closed: "bg-red-50 text-red-700 border-red-200",
  on_hold: "bg-amber-50 text-amber-700 border-amber-200",
  filled: "bg-blue-50 text-blue-700 border-blue-200",
  // Interview-status styles (the same map is reused for the interviews table)
  scheduled: "bg-amber-50 text-amber-700 border-amber-200",
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  cancelled: "bg-red-50 text-red-700 border-red-200",
  no_show:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
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

const STAGE_LABELS: Record<string, string> = {
  new: "New",
  screening: "Screening",
  interview: "Interview",
  assessment: "Assessment",
  offered: "Offered",
  hired: "Hired",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

/* Canonical stage order — kept in sync with the backend `stage` enum.
   Active pipeline stages are shown in the kanban by default; terminal
   stages (rejected, withdrawn) are revealed via the toggle. */
const STAGE_ORDER: CandidateStage[] = [
  "new",
  "screening",
  "interview",
  "assessment",
  "offered",
  "hired",
  "rejected",
  "withdrawn",
];

const ACTIVE_PIPELINE_STAGES: CandidateStage[] = [
  "new",
  "screening",
  "interview",
  "assessment",
  "offered",
  "hired",
];

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
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${styles[status] || styles.new || ""}`}
    >
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
}

/* ── Tab button ───────────────────────────────────────────── */

type Tab = "dashboard" | "jobs" | "candidates" | "interviews";

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
  const [salaryMin, setSalaryMin] = useState("");
  const [salaryMax, setSalaryMax] = useState("");
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
        salary_range_min: salaryMin ? Number(salaryMin) : null,
        salary_range_max: salaryMax ? Number(salaryMax) : null,
      });
      toast.success("Job listing created");
      setTitle("");
      setDepartment("");
      setLocation("");
      setDescription("");
      setSalaryMin("");
      setSalaryMax("");
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="salary-min"
                className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
              >
                Min Salary (SGD)
              </label>
              <input
                id="salary-min"
                type="number"
                value={salaryMin}
                onChange={(e) => setSalaryMin(e.target.value)}
                className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                placeholder="e.g. 4000"
                min="0"
              />
            </div>
            <div>
              <label
                htmlFor="salary-max"
                className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
              >
                Max Salary (SGD)
              </label>
              <input
                id="salary-max"
                type="number"
                value={salaryMax}
                onChange={(e) => setSalaryMax(e.target.value)}
                className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                placeholder="e.g. 6000"
                min="0"
              />
            </div>
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
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    if (file && file.size > MAX_FILE_SIZE) {
      toast.error("File size must be under 10 MB");
      e.target.value = "";
      return;
    }
    setResumeFile(file);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !jobId) return;
    setIsSubmitting(true);
    try {
      const newCandidate = (await recruitmentApi.createCandidate({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        source,
        job_listing_id: Number(jobId),
      })) as Candidate;
      // Upload resume as a second step if a file was selected
      if (resumeFile && newCandidate?.id) {
        try {
          await recruitmentApi.uploadResume(newCandidate.id, resumeFile);
        } catch {
          toast.error(
            "Candidate created but resume upload failed. You can upload it later.",
          );
        }
      }
      toast.success("Candidate added");
      setName("");
      setEmail("");
      setPhone("");
      setSource("direct");
      setJobId("");
      setResumeFile(null);
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
          <div>
            <label
              htmlFor="cand-resume"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Resume
            </label>
            <input
              id="cand-resume"
              type="file"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
              onChange={handleFileChange}
              className="block w-full text-sm text-[var(--color-gray-600)] file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-[var(--color-gray-200)] file:text-sm file:font-medium file:bg-[var(--color-gray-50)] file:text-[var(--color-gray-700)] hover:file:bg-[var(--color-gray-100)]"
            />
            {resumeFile && (
              <p className="text-xs text-[var(--color-gray-500)] mt-1">
                {resumeFile.name} ({(resumeFile.size / 1024).toFixed(0)} KB)
              </p>
            )}
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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

const NEXT_STAGE: Partial<Record<CandidateStage, CandidateStage>> = {
  new: "screening",
  screening: "interview",
  interview: "assessment",
  assessment: "offered",
};

function CandidatePipeline({
  candidates,
  onMoveStage,
  onScheduleInterview,
  onHire,
  onSelectCandidate,
  onReject,
  onRefresh,
}: {
  candidates: Candidate[];
  onMoveStage: (id: number, stage: CandidateStage) => void;
  onScheduleInterview: (candidate: Candidate) => void;
  onHire: (candidateId: number) => void;
  onSelectCandidate: (candidate: Candidate) => void;
  onReject: (candidate: Candidate) => void;
  onRefresh: () => void;
}) {
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);
  const [selectedCandidates, setSelectedCandidates] = useState<Set<number>>(
    new Set(),
  );
  const [showTerminalStages, setShowTerminalStages] = useState(false);
  const [bulkProgress, setBulkProgress] = useState<{
    total: number;
    done: number;
  } | null>(null);

  const visibleStages: CandidateStage[] = showTerminalStages
    ? STAGE_ORDER
    : ACTIVE_PIPELINE_STAGES;

  async function handleDrop(
    candidateId: number,
    fromStage: string,
    toStage: string,
  ) {
    if (fromStage === toStage) return;

    // If dropping into "rejected", open the rejection modal
    if (toStage === "rejected") {
      const candidate = candidates.find((c) => c.id === candidateId);
      if (candidate) {
        onReject(candidate);
      }
      return;
    }

    // Delegate to onMoveStage so "offered" triggers the offer modal
    onMoveStage(candidateId, toStage as CandidateStage);
  }

  if (candidates.length === 0) {
    return (
      <EmptyState
        icon={<Users className="h-12 w-12" aria-hidden="true" />}
        message="No candidates yet"
        description="Candidates will appear here as they apply."
      />
    );
  }

  function exportCandidatesAsCsv(rows: Candidate[]) {
    const sanitize = (val: unknown) => {
      let s = val == null ? "" : String(val);
      // CSV formula injection: prefix risky cells with a single quote
      if (/^[=+\-@]/.test(s)) s = "'" + s;
      // escape double quotes
      s = s.replace(/"/g, '""');
      return `"${s}"`;
    };
    const header = [
      "id",
      "name",
      "email",
      "phone",
      "stage",
      "source",
      "job_title",
      "created_at",
    ];
    const csv = [
      header.join(","),
      ...rows.map((c) =>
        [
          c.id,
          c.name,
          c.email,
          c.phone || "",
          c.stage,
          c.source || "",
          c.job_title || "",
          c.created_at,
        ]
          .map(sanitize)
          .join(","),
      ),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `candidates-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function runSequential(
    ids: number[],
    op: (id: number) => Promise<unknown>,
  ): Promise<void> {
    setBulkProgress({ total: ids.length, done: 0 });
    let done = 0;
    for (const id of ids) {
      try {
        await op(id);
      } catch {
        /* individual failures acceptable in bulk */
      }
      done += 1;
      setBulkProgress({ total: ids.length, done });
    }
    setBulkProgress(null);
  }

  return (
    <>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {visibleStages.map((stage) => {
          const stageCandidates = candidates.filter((c) => c.stage === stage);
          return (
            <div
              key={stage}
              className={`min-w-[220px] flex-1 rounded-lg p-2 transition-all ${
                dragOverStage === stage
                  ? "ring-2 ring-[var(--color-primary)] ring-opacity-50 bg-blue-50/30"
                  : ""
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
              }}
              onDragEnter={(e) => {
                e.preventDefault();
                setDragOverStage(stage);
              }}
              onDragLeave={(e) => {
                // Only clear if we're leaving the column itself, not entering a child
                if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                  setDragOverStage(null);
                }
              }}
              onDrop={(e) => {
                e.preventDefault();
                setDragOverStage(null);
                const candidateId = parseInt(
                  e.dataTransfer.getData("candidateId"),
                  10,
                );
                const fromStage = e.dataTransfer.getData("fromStage");
                if (!isNaN(candidateId) && fromStage !== stage) {
                  handleDrop(candidateId, fromStage, stage);
                }
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                  {STAGE_LABELS[stage] || stage}
                </h3>
                <span className="inline-flex items-center justify-center h-5 min-w-[20px] px-1 rounded-full bg-[var(--color-gray-200)] text-[10px] font-bold text-[var(--color-gray-600)]">
                  {stageCandidates.length}
                </span>
              </div>
              <div className="space-y-2">
                {stageCandidates.map((c) => (
                  <div
                    key={c.id}
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData("candidateId", String(c.id));
                      e.dataTransfer.setData("fromStage", c.stage);
                      e.dataTransfer.effectAllowed = "move";
                    }}
                    className="relative rounded-lg border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-3 cursor-grab active:cursor-grabbing hover:border-[var(--color-primary)] hover:shadow-sm transition-all"
                    onClick={() => onSelectCandidate(c)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelectCandidate(c);
                      }
                    }}
                  >
                    {/* Bulk selection checkbox */}
                    <input
                      type="checkbox"
                      checked={selectedCandidates.has(c.id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        const next = new Set(selectedCandidates);
                        if (next.has(c.id)) next.delete(c.id);
                        else next.add(c.id);
                        setSelectedCandidates(next);
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="absolute top-2 right-2 h-4 w-4 rounded border-[var(--color-gray-300)] cursor-pointer"
                    />
                    <p className="text-sm font-medium text-[var(--color-gray-900)] truncate pr-6">
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
                    {c.overall_score !== null && c.overall_score > 0 && (
                      <div className="flex items-center gap-1 mt-1">
                        {Array.from({ length: 5 }, (_, i) => (
                          <div
                            key={i}
                            className={`h-1.5 w-1.5 rounded-full ${i < (c.overall_score ?? 0) ? "bg-amber-400" : "bg-[var(--color-gray-200)]"}`}
                          />
                        ))}
                      </div>
                    )}
                    {/* Action buttons -- stopPropagation to avoid opening profile panel */}
                    <div
                      className="flex flex-wrap gap-1.5 mt-2"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {NEXT_STAGE[c.stage] && (
                        <button
                          type="button"
                          onClick={() =>
                            onMoveStage(c.id, NEXT_STAGE[c.stage]!)
                          }
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

      {/* Toggle for terminal stages */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setShowTerminalStages((v) => !v)}
          className="text-xs text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] underline"
        >
          {showTerminalStages
            ? "Hide rejected/withdrawn"
            : "Show rejected/withdrawn"}
        </button>
      </div>

      {/* Bulk action toolbar */}
      {selectedCandidates.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-[var(--color-gray-900)] text-white rounded-xl shadow-xl px-5 py-3 flex items-center gap-4 flex-wrap">
          <span className="text-sm font-medium">
            {selectedCandidates.size} selected
          </span>
          {bulkProgress && (
            <span className="text-xs text-white/70">
              {bulkProgress.done}/{bulkProgress.total}
            </span>
          )}
          <div className="h-4 w-px bg-white/30" />
          <select
            onChange={async (e) => {
              const targetStage = e.target.value;
              if (!targetStage) return;
              const ids = Array.from(selectedCandidates);
              await runSequential(ids, (id) =>
                recruitmentApi.moveStage(id, targetStage as CandidateStage),
              );
              toast.success(
                `${ids.length} candidates moved to ${STAGE_LABELS[targetStage] || targetStage}`,
              );
              setSelectedCandidates(new Set());
              onRefresh();
              // reset the select
              e.target.value = "";
            }}
            className="bg-transparent text-white text-sm border border-white/30 rounded-lg px-2 py-1"
            defaultValue=""
            disabled={!!bulkProgress}
          >
            <option value="" disabled>
              Move to...
            </option>
            {ACTIVE_PIPELINE_STAGES.map((s) => (
              <option key={s} value={s}>
                {STAGE_LABELS[s] || s}
              </option>
            ))}
          </select>
          <AppButton
            size="sm"
            variant="text"
            className="!text-red-300 hover:!text-red-200"
            disabled={!!bulkProgress}
            onClick={async () => {
              const ids = Array.from(selectedCandidates);
              await runSequential(ids, (id) =>
                recruitmentApi.rejectCandidate(id, {
                  reason: "Bulk rejection",
                  send_email: false,
                }),
              );
              toast.success(`${ids.length} candidates rejected`);
              setSelectedCandidates(new Set());
              onRefresh();
            }}
          >
            Bulk reject
          </AppButton>
          <AppButton
            size="sm"
            variant="text"
            className="!text-white"
            disabled={!!bulkProgress}
            onClick={() => {
              const rows = candidates.filter((c) =>
                selectedCandidates.has(c.id),
              );
              exportCandidatesAsCsv(rows);
              toast.success(`Exported ${rows.length} candidates to CSV`);
            }}
          >
            <Download className="h-3.5 w-3.5 mr-1" />
            Export
          </AppButton>
          <button
            onClick={() => setSelectedCandidates(new Set())}
            className="text-white/60 hover:text-white"
            disabled={!!bulkProgress}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </>
  );
}

/* ── Resume Viewer ───────────────────────────────────────── */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function ResumeViewer({
  candidateId,
  resumeFilename,
}: {
  candidateId: number;
  resumeFilename?: string;
}) {
  const resumeUrl = `${API_BASE}/recruitment/candidates/${candidateId}/resume`;
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [contentType, setContentType] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadResume() {
      try {
        const token =
          typeof window !== "undefined"
            ? localStorage.getItem("access_token")
            : null;
        const resp = await fetch(resumeUrl, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!resp.ok) throw new Error("Failed to load resume");
        const blob = await resp.blob();
        if (!cancelled) {
          setBlobUrl(URL.createObjectURL(blob));
          setContentType(resp.headers.get("Content-Type") || blob.type || "");
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      }
    }
    loadResume();
    return () => {
      cancelled = true;
    };
  }, [candidateId, resumeUrl]);

  // Clean up blob URL on unmount
  useEffect(() => {
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [blobUrl]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--color-gray-400)]" />
      </div>
    );
  }

  if (error || !blobUrl) {
    return (
      <p className="text-sm text-[var(--color-gray-500)] text-center py-8">
        No resume available
      </p>
    );
  }

  // Detect file type from filename or content type
  const filename = resumeFilename || "";
  const ext = filename.toLowerCase().split(".").pop() || "";
  const ctLower = contentType.toLowerCase();

  const isPdf = ext === "pdf" || ctLower.includes("pdf");
  const isImage =
    ["png", "jpg", "jpeg", "gif", "webp"].includes(ext) ||
    ctLower.startsWith("image/");
  const canEmbed = isPdf || isImage;

  const downloadName =
    filename || `resume-${candidateId}${ext ? "." + ext : ""}`;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <a
          href={blobUrl}
          download={downloadName}
          className="text-sm text-[var(--color-primary)] hover:underline flex items-center gap-1"
        >
          <Download className="h-4 w-4" /> Download
        </a>
        <a
          href={blobUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-[var(--color-primary)] hover:underline flex items-center gap-1"
        >
          <ExternalLink className="h-4 w-4" /> Open in new tab
        </a>
      </div>

      {canEmbed ? (
        isPdf ? (
          <iframe
            src={blobUrl}
            className="w-full h-[500px] rounded-lg border border-[var(--color-gray-200)]"
            title="Resume"
          />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={blobUrl}
            alt="Resume"
            className="w-full h-auto max-h-[500px] rounded-lg border border-[var(--color-gray-200)] object-contain bg-[var(--color-gray-50)]"
          />
        )
      ) : (
        <div className="rounded-lg border border-dashed border-[var(--color-gray-200)] p-6 text-center bg-[var(--color-gray-50)]">
          <FileText className="h-10 w-10 text-[var(--color-gray-400)] mx-auto mb-2" />
          <p className="text-sm font-medium text-[var(--color-gray-700)]">
            {filename || "Resume file"}
          </p>
          <p className="text-xs text-[var(--color-gray-500)] mt-1 mb-3">
            Preview not supported for this file type
            {ext ? ` (.${ext})` : ""}.
          </p>
          <a
            href={blobUrl}
            download={downloadName}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium hover:opacity-90"
          >
            <Download className="h-4 w-4" />
            Download to view
          </a>
        </div>
      )}
    </div>
  );
}

/* ── Activity Timeline (T-R013) ──────────────────────────── */

function ActivityTimeline({
  candidateId,
  fallbackNotes,
}: {
  candidateId: number;
  fallbackNotes: string;
}) {
  const [activities, setActivities] = useState<CandidateActivity[] | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [endpointMissing, setEndpointMissing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    recruitmentApi
      .listCandidateActivity(candidateId)
      .then((res) => {
        if (cancelled) return;
        setActivities(res.activities ?? []);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // Endpoint may not be deployed yet (T-R013): graceful fallback
        const status =
          (err as { status?: number })?.status ??
          (err instanceof Error && /404/.test(err.message) ? 404 : 0);
        if (status === 404) {
          setEndpointMissing(true);
        }
        setActivities([]);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [candidateId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-[var(--color-gray-400)]" />
      </div>
    );
  }

  // If we have proper activity records, render those
  if (activities && activities.length > 0) {
    return (
      <div className="space-y-3">
        {activities.map((a, i) => (
          <div key={a.id} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div className="h-2 w-2 rounded-full bg-[var(--color-primary)] mt-1.5" />
              {i < activities.length - 1 && (
                <div className="w-px flex-1 bg-[var(--color-gray-200)]" />
              )}
            </div>
            <div className="pb-3 flex-1 min-w-0">
              <p className="text-sm text-[var(--color-gray-900)]">
                {a.description}
              </p>
              <div className="flex items-center gap-2 text-xs text-[var(--color-gray-400)] mt-0.5">
                <span>{new Date(a.created_at).toLocaleString("en-SG")}</span>
                {a.actor_name && (
                  <>
                    <span>·</span>
                    <span>{a.actor_name}</span>
                  </>
                )}
                {a.activity_type && (
                  <>
                    <span>·</span>
                    <span className="capitalize">
                      {a.activity_type.replace(/_/g, " ")}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Fall back to parsing legacy "notes" field for inline timestamps if present
  const legacyEntries = (fallbackNotes || "")
    .split("\n")
    .filter((line) => line.trim().startsWith("["));

  if (legacyEntries.length > 0) {
    return (
      <div className="space-y-3">
        {legacyEntries.map((entry, i) => {
          const match = entry.match(/^\[(.+?)\]\s*(.+)$/);
          const timestamp = match?.[1] || "";
          const action = match?.[2] || entry;
          return (
            <div key={i} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div className="h-2 w-2 rounded-full bg-[var(--color-primary)] mt-1.5" />
                {i < legacyEntries.length - 1 && (
                  <div className="w-px flex-1 bg-[var(--color-gray-200)]" />
                )}
              </div>
              <div className="pb-3">
                <p className="text-sm text-[var(--color-gray-900)]">{action}</p>
                <p className="text-xs text-[var(--color-gray-400)]">
                  {timestamp}
                </p>
              </div>
            </div>
          );
        })}
        {endpointMissing && (
          <p className="text-xs text-[var(--color-gray-400)] italic pt-2 border-t border-[var(--color-gray-100)]">
            Showing legacy activity. Detailed timeline will appear once
            recording is enabled.
          </p>
        )}
      </div>
    );
  }

  return (
    <p className="text-sm text-[var(--color-gray-500)] text-center py-6">
      No activity recorded yet.
    </p>
  );
}

/* ── Screening Responses Panel (T-R034) ──────────────────── */

function ScreeningResponsesPanel({ candidateId }: { candidateId: number }) {
  const [responses, setResponses] = useState<ScreeningResponse[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    recruitmentApi
      .listScreeningResponses(candidateId)
      .then((res) => {
        if (!cancelled) {
          setResponses(res.responses ?? []);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setResponses([]);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [candidateId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-[var(--color-gray-400)]" />
      </div>
    );
  }

  if (!responses || responses.length === 0) {
    return (
      <p className="text-sm text-[var(--color-gray-500)] text-center py-6">
        No screening responses recorded.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {responses.map((r) => {
        const failed = !!r.is_failure;
        return (
          <div
            key={r.id}
            className={`rounded-lg border p-3 ${
              failed
                ? "border-red-200 bg-red-50"
                : "border-[var(--color-gray-200)] bg-[var(--color-gray-50)]"
            }`}
          >
            <div className="flex items-start justify-between gap-2 mb-1">
              <p className="text-sm font-medium text-[var(--color-gray-900)]">
                {r.question_text || `Question #${r.question_id}`}
              </p>
              {r.is_knockout && (
                <span
                  className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full whitespace-nowrap ${
                    failed
                      ? "bg-red-200 text-red-800"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  Knockout
                </span>
              )}
            </div>
            <p
              className={`text-sm ${
                failed
                  ? "text-red-700 font-medium"
                  : "text-[var(--color-gray-700)]"
              }`}
            >
              {r.answer || <span className="italic">No answer</span>}
            </p>
            {failed && (
              <p className="text-xs text-red-600 mt-1">
                Did not meet the required answer
                {r.knockout_value ? ` (expected: ${r.knockout_value})` : ""}.
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Scorecard Summary (T-R036, read-only) ────────────────── */

function ScorecardSummaryPanel({ candidateId }: { candidateId: number }) {
  const [entries, setEntries] = useState<ScorecardEntry[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    recruitmentApi
      .listCandidateScorecards(candidateId)
      .then((res) => {
        if (!cancelled) {
          setEntries(res.entries ?? []);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setEntries([]);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [candidateId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-[var(--color-gray-400)]" />
      </div>
    );
  }

  if (!entries || entries.length === 0) {
    return (
      <p className="text-sm text-[var(--color-gray-500)] text-center py-6">
        No scorecards submitted yet.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {entries.map((entry) => (
        <div
          key={entry.id}
          className="rounded-lg border border-[var(--color-gray-200)] p-3 bg-[var(--color-surface-card)]"
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-[var(--color-gray-900)]">
              {entry.template_name || `Template #${entry.template_id}`}
            </p>
            <span className="text-xs text-[var(--color-gray-400)]">
              {entry.interviewer_name ? `${entry.interviewer_name} · ` : ""}
              {new Date(entry.created_at).toLocaleDateString("en-SG", {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </span>
          </div>
          <div className="space-y-1.5">
            {entry.scores.map((s, i) => (
              <div
                key={s.criterion_id ?? i}
                className="flex items-center justify-between gap-3"
              >
                <span className="text-xs text-[var(--color-gray-600)]">
                  {s.criterion_name}
                </span>
                <div className="flex items-center gap-1">
                  {Array.from({ length: 5 }, (_, idx) => (
                    <Star
                      key={idx}
                      className={`h-3 w-3 ${
                        idx < (s.rating ?? 0)
                          ? "fill-amber-400 text-amber-400"
                          : "text-[var(--color-gray-300)]"
                      }`}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
          {entry.notes && (
            <p className="text-xs text-[var(--color-gray-600)] mt-2 italic">
              {entry.notes}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

/* ── Candidate Profile Panel ─────────────────────────────── */

type ProfileTab = "resume" | "activity" | "screening" | "scorecard" | "details";

function CandidateProfilePanel({
  candidate,
  onClose,
  onMoveStage,
  onScheduleInterview,
  onReject,
}: {
  candidate: Candidate;
  onClose: () => void;
  onMoveStage: (id: number, stage: CandidateStage) => void;
  onScheduleInterview: (candidate: Candidate) => void;
  onReject: (candidate: Candidate) => void;
}) {
  const [activeTab, setActiveTab] = useState<ProfileTab>("resume");

  const nextStage = NEXT_STAGE[candidate.stage];

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Panel */}
      <div className="absolute right-0 top-0 h-full w-full max-w-2xl bg-[var(--color-surface-card)] shadow-xl transition-transform translate-x-0 flex flex-col">
        {/* Header */}
        <div className="border-b border-[var(--color-gray-200)] px-6 py-4 flex-shrink-0">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-[var(--color-gray-900)] truncate">
                {candidate.name}
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <StatusBadge status={candidate.stage} styles={STAGE_STYLES} />
                {candidate.job_title && (
                  <span className="text-xs text-[var(--color-gray-500)]">
                    {candidate.job_title}
                  </span>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors flex-shrink-0"
            >
              <X className="h-5 w-5 text-[var(--color-gray-500)]" />
            </button>
          </div>
          {/* Action buttons */}
          <div className="flex flex-wrap gap-2 mt-3">
            {nextStage && (
              <AppButton
                variant="primary"
                size="sm"
                onClick={() => onMoveStage(candidate.id, nextStage)}
              >
                <ChevronRight className="h-4 w-4 mr-1" />
                Move to {nextStage.charAt(0).toUpperCase() + nextStage.slice(1)}
              </AppButton>
            )}
            {(candidate.stage === "screening" ||
              candidate.stage === "interview") && (
              <AppButton
                variant="outlined"
                size="sm"
                onClick={() => onScheduleInterview(candidate)}
              >
                <Calendar className="h-4 w-4 mr-1" />
                Schedule Interview
              </AppButton>
            )}
            {candidate.stage !== "rejected" &&
              candidate.stage !== "hired" &&
              candidate.stage !== "withdrawn" && (
                <AppButton
                  variant="outlined"
                  size="sm"
                  onClick={() => onReject(candidate)}
                  className="!text-red-600 !border-red-200 hover:!bg-red-50"
                >
                  <XCircle className="h-4 w-4 mr-1" />
                  Reject
                </AppButton>
              )}
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col md:flex-row h-full">
            {/* Left sidebar — contact info */}
            <div className="md:w-2/5 border-b md:border-b-0 md:border-r border-[var(--color-gray-200)] p-5 space-y-4 flex-shrink-0">
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                  Contact
                </h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Mail className="h-4 w-4 text-[var(--color-gray-400)] flex-shrink-0" />
                    <a
                      href={`mailto:${candidate.email}`}
                      className="text-[var(--color-primary)] hover:underline truncate"
                    >
                      {candidate.email}
                    </a>
                  </div>
                  {candidate.phone && (
                    <div className="flex items-center gap-2 text-sm">
                      <PhoneIcon className="h-4 w-4 text-[var(--color-gray-400)] flex-shrink-0" />
                      <span className="text-[var(--color-gray-700)]">
                        {candidate.phone}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                  Application
                </h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <MapPin className="h-4 w-4 text-[var(--color-gray-400)] flex-shrink-0" />
                    <span className="text-[var(--color-gray-700)]">
                      Source: {candidate.source?.replace(/_/g, " ") || "Direct"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="h-4 w-4 text-[var(--color-gray-400)] flex-shrink-0" />
                    <span className="text-[var(--color-gray-700)]">
                      Applied: {formatDate(candidate.created_at)}
                    </span>
                  </div>
                </div>
              </div>

              {candidate.overall_score !== null &&
                candidate.overall_score > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                      Rating
                    </h3>
                    <div className="flex items-center gap-1">
                      {Array.from({ length: 5 }, (_, i) => (
                        <div
                          key={i}
                          className={`h-2.5 w-2.5 rounded-full ${i < (candidate.overall_score ?? 0) ? "bg-amber-400" : "bg-[var(--color-gray-200)]"}`}
                        />
                      ))}
                      <span className="ml-1 text-xs text-[var(--color-gray-500)]">
                        {candidate.overall_score}/5
                      </span>
                    </div>
                  </div>
                )}

              {candidate.notes && (
                <div className="space-y-3">
                  <h3 className="text-xs font-semibold text-[var(--color-gray-500)] uppercase tracking-wider">
                    Notes
                  </h3>
                  <p className="text-sm text-[var(--color-gray-700)] whitespace-pre-wrap">
                    {candidate.notes}
                  </p>
                </div>
              )}
            </div>

            {/* Right content — tabs */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Tab bar */}
              <div className="flex gap-1 p-2 border-b border-[var(--color-gray-200)] flex-shrink-0 overflow-x-auto">
                {(
                  [
                    {
                      key: "resume" as ProfileTab,
                      label: "Resume",
                      icon: FileText,
                    },
                    {
                      key: "activity" as ProfileTab,
                      label: "Activity",
                      icon: Clock,
                    },
                    {
                      key: "screening" as ProfileTab,
                      label: "Screening",
                      icon: ShieldCheck,
                    },
                    {
                      key: "scorecard" as ProfileTab,
                      label: "Scorecard",
                      icon: Star,
                    },
                    {
                      key: "details" as ProfileTab,
                      label: "Details",
                      icon: Users,
                    },
                  ] as const
                ).map(({ key, label, icon: Icon }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setActiveTab(key)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${
                      activeTab === key
                        ? "bg-[var(--color-primary)] text-white"
                        : "text-[var(--color-gray-600)] hover:bg-[var(--color-gray-100)]"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="flex-1 p-5 overflow-y-auto">
                {activeTab === "resume" && (
                  <ResumeViewer candidateId={candidate.id} />
                )}

                {activeTab === "activity" && (
                  <ActivityTimeline
                    candidateId={candidate.id}
                    fallbackNotes={candidate.notes || ""}
                  />
                )}

                {activeTab === "screening" && (
                  <ScreeningResponsesPanel candidateId={candidate.id} />
                )}

                {activeTab === "scorecard" && (
                  <ScorecardSummaryPanel candidateId={candidate.id} />
                )}

                {activeTab === "details" && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-[var(--color-gray-500)]">
                          Stage
                        </span>
                        <p className="font-medium text-[var(--color-gray-900)] mt-0.5">
                          {candidate.stage.charAt(0).toUpperCase() +
                            candidate.stage.slice(1)}
                        </p>
                      </div>
                      <div>
                        <span className="text-[var(--color-gray-500)]">
                          Source
                        </span>
                        <p className="font-medium text-[var(--color-gray-900)] mt-0.5">
                          {(candidate.source || "direct").replace(/_/g, " ")}
                        </p>
                      </div>
                      <div>
                        <span className="text-[var(--color-gray-500)]">
                          Applied
                        </span>
                        <p className="font-medium text-[var(--color-gray-900)] mt-0.5">
                          {formatDate(candidate.created_at)}
                        </p>
                      </div>
                      {candidate.job_title && (
                        <div>
                          <span className="text-[var(--color-gray-500)]">
                            Position
                          </span>
                          <p className="font-medium text-[var(--color-gray-900)] mt-0.5">
                            {candidate.job_title}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Analytics Summary Type ──────────────────────────────── */

interface AnalyticsSummary {
  open_jobs: number;
  total_candidates: number;
  pipeline: Record<string, number>;
  interviews_this_week: number;
  sources: Record<string, number>;
  total_offers: number;
  accepted_offers: number;
  offer_acceptance_rate: number;
}

/* ── Dashboard View ──────────────────────────────────────── */

function DashboardView() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    recruitmentApi
      .getAnalyticsSummary()
      .then((data) => setAnalytics(data as AnalyticsSummary))
      .catch(() => setAnalytics(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <TableSkeleton />;
  if (!analytics)
    return (
      <EmptyState
        icon={<Briefcase className="h-12 w-12" aria-hidden="true" />}
        message="No data yet"
        description="Start by creating a job listing."
      />
    );

  return (
    <div className="space-y-6">
      {/* Metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <AppCard variant="standard">
          <div className="text-center py-2">
            <p className="text-2xl font-bold text-[var(--color-gray-900)]">
              {analytics.open_jobs}
            </p>
            <p className="text-sm text-[var(--color-gray-500)]">Open Jobs</p>
          </div>
        </AppCard>
        <AppCard variant="standard">
          <div className="text-center py-2">
            <p className="text-2xl font-bold text-[var(--color-gray-900)]">
              {analytics.total_candidates}
            </p>
            <p className="text-sm text-[var(--color-gray-500)]">
              Active Candidates
            </p>
          </div>
        </AppCard>
        <AppCard variant="standard">
          <div className="text-center py-2">
            <p className="text-2xl font-bold text-[var(--color-gray-900)]">
              {analytics.interviews_this_week}
            </p>
            <p className="text-sm text-[var(--color-gray-500)]">
              Interviews This Week
            </p>
          </div>
        </AppCard>
      </div>

      {/* Pipeline summary */}
      <AppCard
        variant="standard"
        header={
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Pipeline Overview
          </h3>
        }
      >
        <div className="grid grid-cols-5 gap-3 text-center">
          {["new", "screening", "interview", "offered", "hired"].map(
            (stage) => (
              <div key={stage} className="py-2">
                <p className="text-xl font-bold text-[var(--color-gray-900)]">
                  {analytics.pipeline[stage] || 0}
                </p>
                <p className="text-xs text-[var(--color-gray-500)] capitalize">
                  {stage}
                </p>
              </div>
            ),
          )}
        </div>
      </AppCard>

      {/* Source distribution */}
      <AppCard
        variant="standard"
        header={
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Candidate Sources
          </h3>
        }
      >
        <div className="space-y-2">
          {Object.entries(analytics.sources || {}).map(([source, count]) => (
            <div
              key={source}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-[var(--color-gray-600)] capitalize">
                {source.replace(/_/g, " ")}
              </span>
              <span className="font-medium text-[var(--color-gray-900)]">
                {count as number}
              </span>
            </div>
          ))}
        </div>
      </AppCard>

      {/* Offer stats */}
      {analytics.total_offers > 0 && (
        <AppCard
          variant="standard"
          header={
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Offers
            </h3>
          }
        >
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="font-medium">{analytics.total_offers}</span>{" "}
              total
            </div>
            <div>
              <span className="font-medium">{analytics.accepted_offers}</span>{" "}
              accepted
            </div>
            <div>
              <span className="font-medium">
                {analytics.offer_acceptance_rate}%
              </span>{" "}
              acceptance rate
            </div>
          </div>
        </AppCard>
      )}
    </div>
  );
}

/* ── Reject Candidate Modal ──────────────────────────────── */

/** T-R069 — canonical reason values must match the backend reject endpoint. */
const REJECTION_REASONS: Array<{ value: string; label: string }> = [
  { value: "not_qualified", label: "Not qualified" },
  { value: "position_filled", label: "Position filled" },
  { value: "candidate_withdrew", label: "Candidate withdrew" },
  { value: "failed_screening", label: "Failed screening" },
  { value: "other", label: "Other" },
];

function RejectCandidateModal({
  isOpen,
  candidateId,
  candidateName,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  candidateId: number;
  candidateName: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [sendEmail, setSendEmail] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    function h(e: KeyboardEvent) {
      if (e.key === "Escape" && !isSubmitting) onClose();
    }
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [isOpen, onClose, isSubmitting]);

  if (!isOpen) return null;

  async function handleSubmit() {
    if (!reason) {
      toast.error("Please select a rejection reason.");
      return;
    }
    setIsSubmitting(true);
    try {
      await recruitmentApi.rejectCandidate(candidateId, {
        reason,
        notes: notes.trim() || undefined,
        send_email: sendEmail,
      });
      toast.success(`${candidateName} has been rejected.`);
      onSuccess();
      onClose();
    } catch {
      toast.error("Failed to reject candidate.");
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
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-red-500" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Reject Candidate
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
          Reject{" "}
          <span className="font-medium text-[var(--color-gray-900)]">
            {candidateName}
          </span>{" "}
          from the pipeline.
        </p>

        <div className="space-y-4">
          <div>
            <label
              htmlFor="reject-reason"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Reason *
            </label>
            <select
              id="reject-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
            >
              <option value="">Select a reason</option>
              {REJECTION_REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label
              htmlFor="reject-notes"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Additional Notes
            </label>
            <textarea
              id="reject-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              placeholder="Optional notes..."
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-[var(--color-gray-600)]">
            <input
              type="checkbox"
              checked={sendEmail}
              onChange={(e) => setSendEmail(e.target.checked)}
              className="rounded border-[var(--color-gray-300)]"
            />
            Send rejection notification to candidate
          </label>
        </div>

        <div className="flex gap-3 pt-6">
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
            type="button"
            variant="primary"
            size="sm"
            onClick={handleSubmit}
            loading={isSubmitting}
            className="flex-1 !bg-red-600 hover:!bg-red-700"
          >
            Reject
          </AppButton>
        </div>
      </div>
    </div>
  );
}

/* ── TAFEP Scan Results Modal ─────────────────────────────── */

interface TafepFinding {
  matched_text: string;
  category: string;
  suggestion: string;
  field: string;
}

function TafepScanResultsModal({
  isOpen,
  findings,
  onClose,
}: {
  isOpen: boolean;
  findings: TafepFinding[];
  onClose: () => void;
}) {
  if (!isOpen || !findings.length) return null;

  const categoryColors: Record<string, string> = {
    age: "bg-amber-50 text-amber-700",
    gender: "bg-pink-50 text-pink-700",
    race_language: "bg-purple-50 text-purple-700",
    race: "bg-purple-50 text-purple-700",
    nationality: "bg-blue-50 text-blue-700",
    marital: "bg-orange-50 text-orange-700",
    family: "bg-orange-50 text-orange-700",
    religion: "bg-red-50 text-red-700",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              TAFEP Compliance Check
            </h2>
            <p className="text-sm text-red-600 mt-0.5">
              {findings.length} issue{findings.length > 1 ? "s" : ""} found
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-400)]" />
          </button>
        </div>
        <div className="space-y-3">
          {findings.map((f, i) => (
            <div
              key={i}
              className="p-3 rounded-lg border border-[var(--color-gray-200)] bg-[var(--color-gray-50)]"
            >
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${categoryColors[f.category] || "bg-gray-50 text-gray-700"}`}
                >
                  {f.category.replace(/_/g, " ")}
                </span>
                <span className="text-xs text-[var(--color-gray-400)]">
                  in {f.field}
                </span>
              </div>
              <p className="text-sm text-[var(--color-gray-900)]">
                Found:{" "}
                <strong className="text-red-600">
                  &quot;{f.matched_text}&quot;
                </strong>
              </p>
              <p className="text-sm text-[var(--color-gray-600)] mt-1">
                {f.suggestion}
              </p>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-3 border-t border-[var(--color-gray-200)]">
          <p className="text-xs text-[var(--color-gray-500)]">
            Based on TAFEP Tripartite Guidelines on Fair Employment Practices.
            Edit the job description to address these findings before
            publishing.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── Create Offer Modal ──────────────────────────────────── */

function CreateOfferModal({
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
  const [salary, setSalary] = useState("");
  const [startDate, setStartDate] = useState("");
  const [employmentType, setEmploymentType] = useState("full_time");
  const [probationMonths, setProbationMonths] = useState("3");
  const [noticePeriodDays, setNoticePeriodDays] = useState("30");
  const [benefitsSummary, setBenefitsSummary] = useState("");
  const [expiryDate, setExpiryDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().slice(0, 10);
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!salary || !startDate) {
      toast.error("Salary and start date are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await recruitmentApi.createOffer(candidateId, {
        salary: Number(salary),
        start_date: startDate,
        employment_type: employmentType,
        probation_months: Number(probationMonths),
        notice_period_days: Number(noticePeriodDays),
        benefits_summary: benefitsSummary.trim(),
        expiry_date: expiryDate,
      } as Partial<Offer>);
      toast.success(`Offer created for ${candidateName}`);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to create offer";
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
            <DollarSign className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Create Offer
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
              htmlFor="offer-salary"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Monthly Salary (SGD) *
            </label>
            <input
              id="offer-salary"
              type="number"
              value={salary}
              onChange={(e) => setSalary(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              placeholder="e.g. 5000"
              min="0"
              required
            />
          </div>
          <div>
            <label
              htmlFor="offer-start"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Start Date *
            </label>
            <input
              id="offer-start"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              required
            />
          </div>
          <div>
            <label
              htmlFor="offer-emp-type"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Employment Type
            </label>
            <select
              id="offer-emp-type"
              value={employmentType}
              onChange={(e) => setEmploymentType(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
            >
              <option value="full_time">Full-time</option>
              <option value="part_time">Part-time</option>
              <option value="contract">Contract</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="offer-probation"
                className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
              >
                Probation Period
              </label>
              <select
                id="offer-probation"
                value={probationMonths}
                onChange={(e) => setProbationMonths(e.target.value)}
                className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              >
                <option value="3">3 months</option>
                <option value="6">6 months</option>
              </select>
            </div>
            <div>
              <label
                htmlFor="offer-notice"
                className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
              >
                Notice Period
              </label>
              <select
                id="offer-notice"
                value={noticePeriodDays}
                onChange={(e) => setNoticePeriodDays(e.target.value)}
                className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              >
                <option value="30">1 month</option>
                <option value="60">2 months</option>
                <option value="90">3 months</option>
              </select>
            </div>
          </div>
          <div>
            <label
              htmlFor="offer-benefits"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Benefits Summary
            </label>
            <textarea
              id="offer-benefits"
              value={benefitsSummary}
              onChange={(e) => setBenefitsSummary(e.target.value)}
              rows={3}
              className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              placeholder="e.g. 14 days annual leave, medical insurance..."
            />
          </div>
          <div>
            <label
              htmlFor="offer-expiry"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Offer Expiry Date
            </label>
            <input
              id="offer-expiry"
              type="date"
              value={expiryDate}
              onChange={(e) => setExpiryDate(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
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
              Create Offer
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Submit Feedback Modal ───────────────────────────────── */

function SubmitFeedbackModal({
  isOpen,
  onClose,
  onSuccess,
  interviewId,
  candidateId,
  candidateName,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  interviewId: number;
  candidateId: number;
  candidateName: string;
}) {
  const [rating, setRating] = useState(0);
  const [recommendation, setRecommendation] = useState("");
  const [strengths, setStrengths] = useState("");
  const [weaknesses, setWeaknesses] = useState("");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Scorecard state (T-R036)
  const [scorecardTemplates, setScorecardTemplates] = useState<
    ScorecardTemplate[]
  >([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const selectedTemplate = scorecardTemplates.find(
    (t) => String(t.id) === selectedTemplateId,
  );
  const [criterionScores, setCriterionScores] = useState<
    Record<string, number>
  >({});

  // Close on escape
  useEffect(() => {
    if (!isOpen) return;
    function h(e: KeyboardEvent) {
      if (e.key === "Escape" && !isSubmitting) onClose();
    }
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [isOpen, onClose, isSubmitting]);

  // Load templates when modal opens — gracefully degrade on 404
  useEffect(() => {
    if (!isOpen) return;
    recruitmentApi
      .listScorecardTemplates()
      .then((res) => setScorecardTemplates(res.templates ?? []))
      .catch(() => setScorecardTemplates([]));
  }, [isOpen]);

  // Reset criterion scores when template changes
  useEffect(() => {
    setCriterionScores({});
  }, [selectedTemplateId]);

  if (!isOpen) return null;

  function setCriterionScore(key: string, score: number) {
    setCriterionScores((prev) => ({ ...prev, [key]: score }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!rating || !recommendation) {
      toast.error("Rating and recommendation are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await recruitmentApi.submitFeedback(interviewId, {
        rating,
        recommendation: recommendation as InterviewFeedback["recommendation"],
        strengths: strengths.trim(),
        weaknesses: weaknesses.trim(),
        notes: notes.trim(),
      });

      // If a scorecard template was selected with at least one rating, post it
      if (selectedTemplate) {
        const scores = selectedTemplate.criteria
          .map((crit, idx) => {
            const key = String(crit.id ?? idx);
            const ratingValue = criterionScores[key] ?? 0;
            if (ratingValue <= 0) return null;
            return {
              criterion_id: crit.id,
              criterion_name: crit.name,
              rating: ratingValue,
            };
          })
          .filter((s): s is NonNullable<typeof s> => s !== null);
        if (scores.length > 0) {
          try {
            await recruitmentApi.createScorecardEntry({
              candidate_id: candidateId,
              interview_id: interviewId,
              template_id: selectedTemplate.id,
              scores,
              notes: notes.trim(),
            });
          } catch {
            toast.error("Feedback saved, but scorecard could not be recorded.");
          }
        }
      }

      toast.success("Interview feedback submitted");
      setRating(0);
      setRecommendation("");
      setStrengths("");
      setWeaknesses("");
      setNotes("");
      setSelectedTemplateId("");
      setCriterionScores({});
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to submit feedback";
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
            <Star className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Interview Feedback
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
            <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-2">
              Overall Rating *
            </label>
            <div className="flex items-center gap-1">
              {Array.from({ length: 5 }, (_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setRating(i + 1)}
                  className="p-0.5 transition-colors"
                >
                  <Star
                    className={`h-6 w-6 ${
                      i < rating
                        ? "fill-amber-400 text-amber-400"
                        : "text-[var(--color-gray-300)]"
                    }`}
                  />
                </button>
              ))}
              {rating > 0 && (
                <span className="ml-2 text-sm text-[var(--color-gray-500)]">
                  {rating}/5
                </span>
              )}
            </div>
          </div>
          <div>
            <label
              htmlFor="fb-recommendation"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Recommendation *
            </label>
            <select
              id="fb-recommendation"
              value={recommendation}
              onChange={(e) => setRecommendation(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              required
            >
              <option value="">Select recommendation</option>
              <option value="strong_hire">Strong Hire</option>
              <option value="hire">Hire</option>
              <option value="no_hire">No Hire</option>
              <option value="strong_no_hire">Strong No Hire</option>
            </select>
          </div>

          {/* Scorecard (T-R036) */}
          {scorecardTemplates.length > 0 && (
            <div>
              <label
                htmlFor="fb-template"
                className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
              >
                Scorecard Template{" "}
                <span className="text-xs text-[var(--color-gray-400)] font-normal">
                  (optional)
                </span>
              </label>
              <select
                id="fb-template"
                value={selectedTemplateId}
                onChange={(e) => setSelectedTemplateId(e.target.value)}
                className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              >
                <option value="">No scorecard</option>
                {scorecardTemplates.map((t) => (
                  <option key={t.id} value={String(t.id)}>
                    {t.name}
                  </option>
                ))}
              </select>
              {selectedTemplate && (
                <div className="mt-3 space-y-2 rounded-lg border border-[var(--color-gray-200)] p-3 bg-[var(--color-gray-50)]">
                  {selectedTemplate.criteria.map((crit, idx) => {
                    const key = String(crit.id ?? idx);
                    const value = criterionScores[key] ?? 0;
                    return (
                      <div
                        key={key}
                        className="flex items-center justify-between gap-3"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-[var(--color-gray-900)]">
                            {crit.name}
                          </p>
                          {crit.description && (
                            <p className="text-xs text-[var(--color-gray-500)]">
                              {crit.description}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-0.5 flex-shrink-0">
                          {[1, 2, 3, 4, 5].map((s) => (
                            <button
                              key={s}
                              type="button"
                              onClick={() => setCriterionScore(key, s)}
                              aria-label={`${crit.name}: ${s} stars`}
                            >
                              <Star
                                className={`h-5 w-5 ${
                                  s <= value
                                    ? "fill-amber-400 text-amber-400"
                                    : "text-[var(--color-gray-300)]"
                                }`}
                              />
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          <div>
            <label
              htmlFor="fb-strengths"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Strengths
            </label>
            <textarea
              id="fb-strengths"
              value={strengths}
              onChange={(e) => setStrengths(e.target.value)}
              rows={2}
              className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              placeholder="Key strengths observed..."
            />
          </div>
          <div>
            <label
              htmlFor="fb-weaknesses"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Weaknesses
            </label>
            <textarea
              id="fb-weaknesses"
              value={weaknesses}
              onChange={(e) => setWeaknesses(e.target.value)}
              rows={2}
              className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              placeholder="Areas of concern..."
            />
          </div>
          <div>
            <label
              htmlFor="fb-notes"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Additional Notes
            </label>
            <textarea
              id="fb-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              placeholder="Any other observations..."
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
              Submit Feedback
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Interview Calendar (T-R043) ─────────────────────────── */

function InterviewCalendar({
  interviews,
  onSelectInterview,
}: {
  interviews: InterviewSchedule[];
  onSelectInterview?: (iv: InterviewSchedule) => void;
}) {
  const today = new Date();
  const [viewMonth, setViewMonth] = useState({
    year: today.getFullYear(),
    month: today.getMonth(), // 0-indexed
  });
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  // Group interviews by ISO date (yyyy-mm-dd)
  const byDate = useMemo(() => {
    const map = new Map<string, InterviewSchedule[]>();
    for (const iv of interviews) {
      if (!iv.scheduled_at) continue;
      const d = new Date(iv.scheduled_at);
      if (Number.isNaN(d.getTime())) continue;
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(iv);
    }
    return map;
  }, [interviews]);

  const firstDay = new Date(viewMonth.year, viewMonth.month, 1);
  const startWeekday = firstDay.getDay(); // 0 = Sun
  const daysInMonth = new Date(
    viewMonth.year,
    viewMonth.month + 1,
    0,
  ).getDate();

  // Build the grid: leading blanks + days
  const cells: Array<{ day: number | null; iso: string | null }> = [];
  for (let i = 0; i < startWeekday; i++) cells.push({ day: null, iso: null });
  for (let d = 1; d <= daysInMonth; d++) {
    const iso = `${viewMonth.year}-${String(viewMonth.month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push({ day: d, iso });
  }
  // Pad to a 6-row grid (42 cells)
  while (cells.length < 42) cells.push({ day: null, iso: null });

  const monthLabel = new Date(viewMonth.year, viewMonth.month).toLocaleString(
    "en-SG",
    { month: "long", year: "numeric" },
  );

  function goPrev() {
    const m = viewMonth.month - 1;
    if (m < 0) setViewMonth({ year: viewMonth.year - 1, month: 11 });
    else setViewMonth({ ...viewMonth, month: m });
    setSelectedDay(null);
  }
  function goNext() {
    const m = viewMonth.month + 1;
    if (m > 11) setViewMonth({ year: viewMonth.year + 1, month: 0 });
    else setViewMonth({ ...viewMonth, month: m });
    setSelectedDay(null);
  }
  function goToday() {
    setViewMonth({ year: today.getFullYear(), month: today.getMonth() });
    setSelectedDay(null);
  }

  const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const selectedInterviews = selectedDay ? byDate.get(selectedDay) || [] : [];

  return (
    <AppCard variant="standard">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-[var(--color-gray-900)]">
          {monthLabel}
        </h3>
        <div className="flex items-center gap-1.5">
          <AppButton variant="outlined" size="sm" onClick={goPrev}>
            <ChevronRight className="h-4 w-4 rotate-180" />
          </AppButton>
          <AppButton variant="outlined" size="sm" onClick={goToday}>
            Today
          </AppButton>
          <AppButton variant="outlined" size="sm" onClick={goNext}>
            <ChevronRight className="h-4 w-4" />
          </AppButton>
        </div>
      </div>

      {/* Weekday header */}
      <div className="grid grid-cols-7 gap-1 mb-1">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((w) => (
          <div
            key={w}
            className="text-[10px] font-semibold uppercase text-[var(--color-gray-500)] text-center py-1"
          >
            {w}
          </div>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-7 gap-1">
        {cells.map((cell, idx) => {
          if (!cell.iso || !cell.day) {
            return (
              <div
                key={idx}
                className="aspect-square rounded-md bg-transparent"
              />
            );
          }
          const dayInterviews = byDate.get(cell.iso) || [];
          const isToday = cell.iso === todayIso;
          const isSelected = cell.iso === selectedDay;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => setSelectedDay(cell.iso)}
              className={`aspect-square rounded-md p-1 text-left transition-colors border ${
                isSelected
                  ? "bg-[var(--color-primary)] text-white border-[var(--color-primary)]"
                  : isToday
                    ? "border-[var(--color-primary)] bg-[var(--color-surface-card)]"
                    : "border-transparent hover:bg-[var(--color-gray-50)]"
              }`}
            >
              <div className="text-xs font-medium">{cell.day}</div>
              {dayInterviews.length > 0 && (
                <div className="flex items-center gap-0.5 mt-0.5">
                  <span
                    className={`inline-block h-1 w-1 rounded-full ${
                      isSelected ? "bg-white" : "bg-[var(--color-primary)]"
                    }`}
                  />
                  <span
                    className={`text-[10px] ${
                      isSelected
                        ? "text-white/90"
                        : "text-[var(--color-gray-500)]"
                    }`}
                  >
                    {dayInterviews.length}
                  </span>
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Selected-day panel */}
      {selectedDay && (
        <div className="mt-4 border-t border-[var(--color-gray-200)] pt-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-gray-500)] mb-2">
            {new Date(selectedDay).toLocaleDateString("en-SG", {
              weekday: "long",
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </p>
          {selectedInterviews.length === 0 ? (
            <p className="text-sm text-[var(--color-gray-500)]">
              No interviews scheduled.
            </p>
          ) : (
            <div className="space-y-2">
              {selectedInterviews
                .slice()
                .sort((a, b) => (a.scheduled_at < b.scheduled_at ? -1 : 1))
                .map((iv) => {
                  const dt = new Date(iv.scheduled_at);
                  const time = dt.toLocaleTimeString("en-SG", {
                    hour: "2-digit",
                    minute: "2-digit",
                  });
                  return (
                    <button
                      key={iv.id}
                      type="button"
                      onClick={() => onSelectInterview?.(iv)}
                      className="w-full text-left rounded-lg border border-[var(--color-gray-200)] p-2 hover:border-[var(--color-primary)] transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-[var(--color-gray-900)]">
                          {iv.candidate_name || `Candidate #${iv.candidate_id}`}
                        </span>
                        <span className="text-xs text-[var(--color-gray-500)]">
                          {time}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 text-xs text-[var(--color-gray-500)]">
                        <span className="capitalize">{iv.interview_type}</span>
                        {iv.location && (
                          <>
                            <span>·</span>
                            <span>{iv.location}</span>
                          </>
                        )}
                      </div>
                    </button>
                  );
                })}
            </div>
          )}
        </div>
      )}
    </AppCard>
  );
}

/* ── Screening Questions Manager (T-R033) ───────────────── */

function ScreeningQuestionsModal({
  isOpen,
  jobId,
  jobTitle,
  onClose,
}: {
  isOpen: boolean;
  jobId: number | null;
  jobTitle: string;
  onClose: () => void;
}) {
  const [questions, setQuestions] = useState<ScreeningQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [newQ, setNewQ] = useState<{
    question_text: string;
    question_type: ScreeningQuestion["question_type"];
    is_required: boolean;
    is_knockout: boolean;
    knockout_value: string;
  }>({
    question_text: "",
    question_type: "text",
    is_required: false,
    is_knockout: false,
    knockout_value: "",
  });
  const [saving, setSaving] = useState(false);

  // ESC closes modal
  useEffect(() => {
    if (!isOpen) return;
    function h(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen || !jobId) return;
    setLoading(true);
    recruitmentApi
      .listJobQuestions(jobId)
      .then((res) =>
        setQuestions(
          [...(res.questions ?? [])].sort(
            (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0),
          ),
        ),
      )
      .catch(() => setQuestions([]))
      .finally(() => setLoading(false));
  }, [isOpen, jobId]);

  if (!isOpen || !jobId) return null;

  function handleDragStart(e: React.DragEvent<HTMLDivElement>, id: number) {
    setDraggingId(id);
    e.dataTransfer.effectAllowed = "move";
  }

  async function handleDrop(
    e: React.DragEvent<HTMLDivElement>,
    targetId: number,
  ) {
    e.preventDefault();
    if (draggingId == null || draggingId === targetId) return;

    const next = [...questions];
    const fromIdx = next.findIndex((q) => q.id === draggingId);
    const toIdx = next.findIndex((q) => q.id === targetId);
    if (fromIdx < 0 || toIdx < 0) return;

    const [moved] = next.splice(fromIdx, 1);
    next.splice(toIdx, 0, moved);

    // Re-number sort_order
    const reordered = next.map((q, i) => ({ ...q, sort_order: i }));
    setQuestions(reordered);
    setDraggingId(null);

    // Persist sort_order changes — fire-and-forget
    for (const q of reordered) {
      try {
        await recruitmentApi.updateJobQuestion(jobId!, q.id, {
          sort_order: q.sort_order,
        });
      } catch {
        /* swallow individual failures */
      }
    }
  }

  async function handleAdd() {
    if (!newQ.question_text.trim()) return;
    setSaving(true);
    try {
      const res = (await recruitmentApi.createJobQuestion(jobId!, {
        question_text: newQ.question_text.trim(),
        question_type: newQ.question_type,
        is_required: newQ.is_required,
        is_knockout: newQ.is_knockout,
        knockout_value: newQ.knockout_value || null,
        sort_order: questions.length,
      })) as { question: ScreeningQuestion };
      const q = (res as { question: ScreeningQuestion }).question || res;
      setQuestions([...questions, q as ScreeningQuestion]);
      setNewQ({
        question_text: "",
        question_type: "text",
        is_required: false,
        is_knockout: false,
        knockout_value: "",
      });
      toast.success("Question added");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to add question";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(qid: number) {
    try {
      await recruitmentApi.deleteJobQuestion(jobId!, qid);
      setQuestions(questions.filter((q) => q.id !== qid));
      toast.success("Question removed");
    } catch {
      toast.error("Failed to remove question");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-xl mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Screening questions
            </h2>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
              {jobTitle}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-[var(--color-gray-400)]" />
          </div>
        ) : (
          <>
            <p className="text-xs text-[var(--color-gray-500)] mb-2">
              Drag to reorder. Knockout questions automatically reject
              candidates who answer incorrectly.
            </p>
            <div className="space-y-2 mb-4">
              {questions.length === 0 && (
                <p className="text-sm text-[var(--color-gray-500)] text-center py-4 border border-dashed border-[var(--color-gray-200)] rounded-lg">
                  No screening questions yet
                </p>
              )}
              {questions.map((q) => (
                <div
                  key={q.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, q.id)}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = "move";
                  }}
                  onDrop={(e) => handleDrop(e, q.id)}
                  className={`flex items-start gap-2 p-3 rounded-lg border bg-[var(--color-surface-card)] cursor-grab active:cursor-grabbing transition-opacity ${
                    draggingId === q.id
                      ? "opacity-40 border-[var(--color-primary)]"
                      : "border-[var(--color-gray-200)]"
                  }`}
                >
                  <div className="flex flex-col gap-0.5 mt-1 text-[var(--color-gray-400)] select-none">
                    <span className="block w-1 h-1 rounded-full bg-current" />
                    <span className="block w-1 h-1 rounded-full bg-current" />
                    <span className="block w-1 h-1 rounded-full bg-current" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--color-gray-900)]">
                      {q.question_text}
                    </p>
                    <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                      <span className="text-[10px] uppercase font-medium text-[var(--color-gray-500)]">
                        {q.question_type.replace(/_/g, " ")}
                      </span>
                      {q.is_required && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700">
                          Required
                        </span>
                      )}
                      {q.is_knockout && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">
                          Knockout
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDelete(q.id)}
                    className="text-[var(--color-gray-400)] hover:text-red-600"
                    aria-label="Remove question"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            <div className="border-t border-[var(--color-gray-200)] pt-4 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-gray-500)]">
                Add a question
              </p>
              <input
                type="text"
                value={newQ.question_text}
                onChange={(e) =>
                  setNewQ({ ...newQ, question_text: e.target.value })
                }
                className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                placeholder="Question text"
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={newQ.question_type}
                  onChange={(e) =>
                    setNewQ({
                      ...newQ,
                      question_type: e.target
                        .value as ScreeningQuestion["question_type"],
                    })
                  }
                  className="rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                  aria-label="Question type"
                >
                  <option value="text">Text</option>
                  <option value="yes_no">Yes / No</option>
                  <option value="multiple_choice">Multiple choice</option>
                  <option value="number">Number</option>
                </select>
                {newQ.is_knockout && (
                  <input
                    type="text"
                    value={newQ.knockout_value}
                    onChange={(e) =>
                      setNewQ({ ...newQ, knockout_value: e.target.value })
                    }
                    className="rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                    placeholder="Required answer"
                  />
                )}
              </div>
              <div className="flex items-center gap-4 text-sm">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newQ.is_required}
                    onChange={(e) =>
                      setNewQ({ ...newQ, is_required: e.target.checked })
                    }
                  />
                  Required
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newQ.is_knockout}
                    onChange={(e) =>
                      setNewQ({ ...newQ, is_knockout: e.target.checked })
                    }
                  />
                  Knockout
                </label>
              </div>
              <AppButton
                type="button"
                variant="primary"
                size="sm"
                onClick={handleAdd}
                loading={saving}
                disabled={!newQ.question_text.trim()}
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-1" /> Add question
              </AppButton>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/* ── Hire Review Modal (T-R024) ──────────────────────────── */

interface HireReviewTarget {
  candidateId: number;
  candidate: Candidate;
  latestOffer?: Offer | null;
}

function HireReviewModal({
  isOpen,
  target,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  target: HireReviewTarget | null;
  onClose: () => void;
  onSuccess: (result: {
    employeeId: number;
    onboardingAssignmentId?: number;
  }) => void;
}) {
  const [step, setStep] = useState(1);
  const [department, setDepartment] = useState("");
  const [designation, setDesignation] = useState("");
  const [startDate, setStartDate] = useState(() =>
    new Date().toISOString().slice(0, 10),
  );
  const [templates, setTemplates] = useState<
    Array<{ id: number; name: string; is_default: boolean }>
  >([]);
  const [templateId, setTemplateId] = useState<string>("default");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{
    employeeId: number;
    onboardingAssignmentId?: number;
  } | null>(null);

  // Reset state when modal opens
  useEffect(() => {
    if (!isOpen) return;
    setStep(1);
    setResult(null);
    setSubmitting(false);
    setDepartment("");
    setDesignation(target?.candidate.job_title || "");
    setStartDate(new Date().toISOString().slice(0, 10));
    setTemplateId("default");
    // Try to load onboarding templates; gracefully degrade if endpoint unavailable
    recruitmentApi
      .listOnboardingTemplatesForHire()
      .then((res) => setTemplates(res.templates ?? []))
      .catch(() => setTemplates([]));
  }, [isOpen, target]);

  // Escape closes modal
  useEffect(() => {
    if (!isOpen) return;
    function handler(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) onClose();
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose, submitting]);

  if (!isOpen || !target) return null;

  const c = target.candidate;
  const offer = target.latestOffer;

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const res = (await recruitmentApi.hireCandidate(target!.candidateId, {
        start_date: startDate,
        department: department.trim(),
        designation: designation.trim(),
        onboarding_template_id:
          templateId === "default" || templateId === ""
            ? null
            : Number(templateId),
      })) as {
        message: string;
        employee_id: number;
        onboarding_assignment_id?: number;
      };
      const final = {
        employeeId: res.employee_id,
        onboardingAssignmentId: res.onboarding_assignment_id,
      };
      setResult(final);
      setStep(4);
      onSuccess(final);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to hire";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }

  const stepDots = [1, 2, 3];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={() => !submitting && onClose()}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-emerald-600" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Hire {c.name}
            </h2>
          </div>
          <button
            type="button"
            onClick={() => !submitting && onClose()}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
            disabled={submitting}
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>

        {/* Step indicator */}
        {step <= 3 && (
          <div className="flex items-center justify-center gap-2 mb-5">
            {stepDots.map((s) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    s < step
                      ? "bg-emerald-500"
                      : s === step
                        ? "bg-[var(--color-primary)]"
                        : "bg-[var(--color-gray-300)]"
                  }`}
                />
                {s < 3 && (
                  <div
                    className={`w-8 h-px ${s < step ? "bg-emerald-500" : "bg-[var(--color-gray-200)]"}`}
                  />
                )}
              </div>
            ))}
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-gray-600)]">
              Confirm the candidate&apos;s details before completing the hire.
            </p>
            <div className="rounded-lg border border-[var(--color-gray-200)] p-3 space-y-1.5 text-sm">
              <div>
                <span className="text-[var(--color-gray-500)]">Name:</span>{" "}
                <span className="font-medium">{c.name}</span>
              </div>
              <div>
                <span className="text-[var(--color-gray-500)]">Email:</span>{" "}
                <span className="font-medium">{c.email}</span>
              </div>
              {c.job_title && (
                <div>
                  <span className="text-[var(--color-gray-500)]">
                    Position:
                  </span>{" "}
                  <span className="font-medium">{c.job_title}</span>
                </div>
              )}
              {offer && (
                <>
                  <div>
                    <span className="text-[var(--color-gray-500)]">
                      Salary:
                    </span>{" "}
                    <span className="font-medium">
                      {offer.currency || "SGD"} {offer.salary?.toLocaleString()}
                      /{offer.salary_period || "monthly"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[var(--color-gray-500)]">
                      Start date:
                    </span>{" "}
                    <span className="font-medium">{offer.start_date}</span>
                  </div>
                </>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label
                  htmlFor="hire-department"
                  className="block text-xs font-medium text-[var(--color-gray-700)] mb-1"
                >
                  Department
                </label>
                <input
                  id="hire-department"
                  type="text"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[40px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                  placeholder="e.g. Engineering"
                />
              </div>
              <div>
                <label
                  htmlFor="hire-designation"
                  className="block text-xs font-medium text-[var(--color-gray-700)] mb-1"
                >
                  Designation
                </label>
                <input
                  id="hire-designation"
                  type="text"
                  value={designation}
                  onChange={(e) => setDesignation(e.target.value)}
                  className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[40px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                  placeholder="e.g. Software Engineer"
                />
              </div>
            </div>
            <div>
              <label
                htmlFor="hire-start"
                className="block text-xs font-medium text-[var(--color-gray-700)] mb-1"
              >
                Start date *
              </label>
              <input
                id="hire-start"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[40px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                required
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
                type="button"
                variant="primary"
                size="sm"
                onClick={() => setStep(2)}
                className="flex-1"
                disabled={!startDate}
              >
                Next
              </AppButton>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-gray-600)]">
              Choose an onboarding template for this hire.
            </p>
            <div className="space-y-2">
              <label className="flex items-start gap-2 p-3 rounded-lg border border-[var(--color-gray-200)] cursor-pointer hover:border-[var(--color-primary)]">
                <input
                  type="radio"
                  name="template"
                  value="default"
                  checked={templateId === "default"}
                  onChange={() => setTemplateId("default")}
                  className="mt-0.5"
                />
                <div>
                  <p className="text-sm font-medium text-[var(--color-gray-900)]">
                    Use default template
                  </p>
                  <p className="text-xs text-[var(--color-gray-500)]">
                    Apply your company&apos;s default onboarding workflow.
                  </p>
                </div>
              </label>
              {templates
                .filter((t) => !t.is_default)
                .map((t) => (
                  <label
                    key={t.id}
                    className="flex items-start gap-2 p-3 rounded-lg border border-[var(--color-gray-200)] cursor-pointer hover:border-[var(--color-primary)]"
                  >
                    <input
                      type="radio"
                      name="template"
                      value={String(t.id)}
                      checked={templateId === String(t.id)}
                      onChange={() => setTemplateId(String(t.id))}
                      className="mt-0.5"
                    />
                    <div>
                      <p className="text-sm font-medium text-[var(--color-gray-900)]">
                        {t.name}
                      </p>
                    </div>
                  </label>
                ))}
              <label className="flex items-start gap-2 p-3 rounded-lg border border-[var(--color-gray-200)] cursor-pointer hover:border-[var(--color-primary)]">
                <input
                  type="radio"
                  name="template"
                  value=""
                  checked={templateId === ""}
                  onChange={() => setTemplateId("")}
                  className="mt-0.5"
                />
                <div>
                  <p className="text-sm font-medium text-[var(--color-gray-900)]">
                    Skip onboarding template
                  </p>
                  <p className="text-xs text-[var(--color-gray-500)]">
                    Create the employee record only — no onboarding assigned.
                  </p>
                </div>
              </label>
            </div>
            <div className="flex gap-3 pt-2">
              <AppButton
                type="button"
                variant="outlined"
                size="sm"
                onClick={() => setStep(1)}
                className="flex-1"
              >
                Back
              </AppButton>
              <AppButton
                type="button"
                variant="primary"
                size="sm"
                onClick={() => setStep(3)}
                className="flex-1"
              >
                Next
              </AppButton>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-gray-600)]">
              Review and confirm. This will create an employee record and send
              the onboarding invitation.
            </p>
            <div className="rounded-lg border border-[var(--color-gray-200)] p-3 space-y-1 text-sm">
              <div>
                <span className="text-[var(--color-gray-500)]">Name:</span>{" "}
                {c.name}
              </div>
              <div>
                <span className="text-[var(--color-gray-500)]">Email:</span>{" "}
                {c.email}
              </div>
              <div>
                <span className="text-[var(--color-gray-500)]">
                  Department:
                </span>{" "}
                {department || "—"}
              </div>
              <div>
                <span className="text-[var(--color-gray-500)]">
                  Designation:
                </span>{" "}
                {designation || c.job_title || "—"}
              </div>
              <div>
                <span className="text-[var(--color-gray-500)]">
                  Start date:
                </span>{" "}
                {startDate}
              </div>
              <div>
                <span className="text-[var(--color-gray-500)]">
                  Onboarding:
                </span>{" "}
                {templateId === "default"
                  ? "Default template"
                  : templateId === ""
                    ? "None"
                    : templates.find((t) => String(t.id) === templateId)
                        ?.name || "Custom template"}
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <AppButton
                type="button"
                variant="outlined"
                size="sm"
                onClick={() => setStep(2)}
                className="flex-1"
                disabled={submitting}
              >
                Back
              </AppButton>
              <AppButton
                type="button"
                variant="primary"
                size="sm"
                onClick={handleSubmit}
                loading={submitting}
                className="flex-1"
              >
                Confirm hire
              </AppButton>
            </div>
          </div>
        )}

        {step === 4 && result && (
          <div className="space-y-4 text-center py-2">
            <div className="mx-auto w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
              <CheckCircle className="w-7 h-7 text-emerald-600" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-[var(--color-gray-900)]">
                {c.name} hired
              </h3>
              <p className="text-sm text-[var(--color-gray-600)] mt-1">
                Employee record created and invitation sent.
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <a
                href={`/employees/${result.employeeId}`}
                className="text-sm text-[var(--color-primary)] hover:underline inline-flex items-center justify-center gap-1"
              >
                <Users className="h-4 w-4" /> View employee profile
              </a>
              {result.onboardingAssignmentId && (
                <a
                  href={`/employees/${result.employeeId}?tab=onboarding`}
                  className="text-sm text-[var(--color-primary)] hover:underline inline-flex items-center justify-center gap-1"
                >
                  <CheckCircle className="h-4 w-4" /> View onboarding
                </a>
              )}
            </div>
            <AppButton
              type="button"
              variant="primary"
              size="sm"
              onClick={onClose}
              className="w-full"
            >
              Close
            </AppButton>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

function RecruitmentPageInner() {
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "hr_manager";

  const searchParams = useSearchParams();
  const router = useRouter();
  const tabParam = searchParams.get("tab") as Tab | null;
  const validTabs: Tab[] = ["dashboard", "jobs", "candidates", "interviews"];
  const initialTab =
    tabParam && validTabs.includes(tabParam) ? tabParam : "dashboard";
  const [tab, setTab] = useState<Tab>(initialTab);

  function handleTabChange(newTab: Tab) {
    setTab(newTab);
    const url =
      newTab === "dashboard" ? "/recruitment" : `/recruitment?tab=${newTab}`;
    router.replace(url, { scroll: false });
  }
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
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(
    null,
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [stageFilters, setStageFilters] = useState<Set<CandidateStage>>(
    new Set(),
  );

  // Debounce search query (300ms) — T-R014
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(t);
  }, [searchQuery]);
  const [rejectTarget, setRejectTarget] = useState<{
    id: number;
    name: string;
  } | null>(null);

  // TAFEP compliance scan state
  const [scanFindings, setScanFindings] = useState<TafepFinding[]>([]);
  const [showScanModal, setShowScanModal] = useState(false);
  const [scanningJobId, setScanningJobId] = useState<number | null>(null);

  // Offer creation state
  const [offerTarget, setOfferTarget] = useState<{
    id: number;
    name: string;
  } | null>(null);

  // Interview feedback state
  const [feedbackTarget, setFeedbackTarget] = useState<{
    interviewId: number;
    candidateId: number;
    candidateName: string;
  } | null>(null);

  // Hire review state (T-R024)
  const [hireTarget, setHireTarget] = useState<HireReviewTarget | null>(null);

  // Screening questions modal state (T-R033)
  const [questionsTarget, setQuestionsTarget] = useState<{
    jobId: number;
    title: string;
  } | null>(null);

  // Interviews view toggle (T-R043)
  const [interviewView, setInterviewView] = useState<"list" | "calendar">(
    "list",
  );

  const filteredCandidates = useMemo(() => {
    let results = candidates;
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase();
      results = results.filter(
        (c) =>
          c.name.toLowerCase().includes(q) || c.email.toLowerCase().includes(q),
      );
    }
    if (sourceFilter !== "all") {
      results = results.filter((c) => c.source === sourceFilter);
    }
    if (stageFilters.size > 0) {
      results = results.filter((c) => stageFilters.has(c.stage));
    }
    return results;
  }, [candidates, debouncedSearch, sourceFilter, stageFilters]);

  const hasActiveFilters =
    searchQuery !== "" || sourceFilter !== "all" || stageFilters.size > 0;

  function clearFilters() {
    setSearchQuery("");
    setDebouncedSearch("");
    setSourceFilter("all");
    setStageFilters(new Set());
  }

  function toggleStageFilter(stage: CandidateStage) {
    const next = new Set(stageFilters);
    if (next.has(stage)) next.delete(stage);
    else next.add(stage);
    setStageFilters(next);
  }

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
    // When moving to "offered", open the offer creation modal instead
    if (stage === "offered") {
      const candidate = candidates.find((c) => c.id === candidateId);
      if (candidate) {
        setOfferTarget({ id: candidate.id, name: candidate.name });
      }
      return;
    }
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
    const candidate = candidates.find((c) => c.id === candidateId);
    if (!candidate) return;

    // Best-effort fetch of latest offer for review-screen pre-fill (T-R024)
    let latestOffer: Offer | null = null;
    try {
      const res = await recruitmentApi.listOffers({
        candidate_id: String(candidateId),
      });
      const offers = res.offers || [];
      if (offers.length > 0) {
        latestOffer = [...offers].sort((a, b) =>
          (b as unknown as { id: number }).id >
          (a as unknown as { id: number }).id
            ? 1
            : -1,
        )[0];
      }
    } catch {
      latestOffer = null;
    }

    setHireTarget({ candidateId, candidate, latestOffer });
  }

  async function handleScanJob(jobId: number) {
    setScanningJobId(jobId);
    try {
      const useAi =
        typeof window !== "undefined" &&
        window.localStorage.getItem("recruitment.tafep.ai_check") === "1";
      const result = await recruitmentApi.scanJob(jobId, useAi);
      if (result.ai_unavailable) {
        toast("AI scan unavailable — falling back to rule-based check.", {
          icon: "⚠️",
        });
      }
      if (result.compliant || result.count === 0) {
        toast.success(
          useAi && !result.ai_unavailable
            ? "Job listing is TAFEP compliant (AI + rules)"
            : "Job listing is TAFEP compliant",
        );
      } else {
        setScanFindings(result.findings);
        setShowScanModal(true);
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to run compliance scan";
      toast.error(message);
    } finally {
      setScanningJobId(null);
    }
  }

  if (error && !isLoading) {
    return (
      <AdminGuard>
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
      </AdminGuard>
    );
  }

  return (
    <AdminGuard>
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
            active={tab === "dashboard"}
            label="Dashboard"
            onClick={() => handleTabChange("dashboard")}
          />
          <TabButton
            active={tab === "jobs"}
            label="Job Listings"
            onClick={() => handleTabChange("jobs")}
          />
          <TabButton
            active={tab === "candidates"}
            label="Candidates"
            onClick={() => handleTabChange("candidates")}
          />
          <TabButton
            active={tab === "interviews"}
            label="Interviews"
            onClick={() => handleTabChange("interviews")}
          />
        </div>

        {/* Dashboard Tab */}
        {tab === "dashboard" && <DashboardView />}

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
                            {job.title || "-"}
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
                            <div className="flex items-center justify-center gap-2 flex-wrap">
                              <AppButton
                                variant="outlined"
                                size="sm"
                                onClick={() =>
                                  setQuestionsTarget({
                                    jobId: job.id,
                                    title: job.title,
                                  })
                                }
                              >
                                Questions
                              </AppButton>
                              {job.status === "draft" && (
                                <>
                                  <AppButton
                                    variant="outlined"
                                    size="sm"
                                    onClick={() => handleScanJob(job.id)}
                                    loading={scanningJobId === job.id}
                                  >
                                    <ShieldCheck className="h-3.5 w-3.5 mr-1" />
                                    Check Compliance
                                  </AppButton>
                                  <AppButton
                                    variant="primary"
                                    size="sm"
                                    onClick={() => handlePublish(job.id)}
                                  >
                                    Publish
                                  </AppButton>
                                </>
                              )}
                            </div>
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
            {/* Filter bar (T-R014) */}
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative flex-1 min-w-[200px] max-w-sm">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-gray-400)]" />
                  <input
                    type="text"
                    placeholder="Search by name or email..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full rounded-[8px] border px-3 py-2 pl-9 text-sm min-h-[40px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] placeholder:text-[var(--color-gray-400)]"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-[var(--color-gray-400)]" />
                  <select
                    value={sourceFilter}
                    onChange={(e) => setSourceFilter(e.target.value)}
                    className="rounded-[8px] border px-3 py-2 text-sm min-h-[40px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                    aria-label="Filter by source"
                  >
                    <option value="all">All sources</option>
                    <option value="linkedin">LinkedIn</option>
                    <option value="indeed">Indeed</option>
                    <option value="jobstreet">JobStreet</option>
                    <option value="referral">Referral</option>
                    <option value="direct">Direct</option>
                    <option value="job_board">Job board</option>
                    <option value="agency">Agency</option>
                    <option value="career_fair">Career fair</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                {hasActiveFilters && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="text-xs text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] underline whitespace-nowrap"
                  >
                    Clear filters
                  </button>
                )}
                {isAdmin && (
                  <div className="ml-auto">
                    <AppButton
                      variant="primary"
                      size="sm"
                      onClick={() => setShowCandidateModal(true)}
                    >
                      <Plus className="h-4 w-4 mr-1" /> Add Candidate
                    </AppButton>
                  </div>
                )}
              </div>
              {/* Stage chips multi-select */}
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-[var(--color-gray-500)] mr-1">
                  Stage:
                </span>
                {STAGE_ORDER.map((stage) => {
                  const active = stageFilters.has(stage);
                  return (
                    <button
                      key={stage}
                      type="button"
                      onClick={() => toggleStageFilter(stage)}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                        active
                          ? "bg-[var(--color-primary)] text-white border-[var(--color-primary)]"
                          : "bg-[var(--color-surface-card)] text-[var(--color-gray-600)] border-[var(--color-gray-200)] hover:border-[var(--color-gray-400)]"
                      }`}
                    >
                      {STAGE_LABELS[stage] || stage}
                    </button>
                  );
                })}
              </div>
            </div>
            {isLoading ? (
              <AppCard variant="standard">
                <div className="-mx-5 -my-4">
                  <TableSkeleton />
                </div>
              </AppCard>
            ) : (
              <CandidatePipeline
                candidates={filteredCandidates}
                onMoveStage={handleMoveStage}
                onScheduleInterview={(c) =>
                  setInterviewTarget({ id: c.id, name: c.name })
                }
                onHire={handleHire}
                onSelectCandidate={setSelectedCandidate}
                onReject={(c) => setRejectTarget({ id: c.id, name: c.name })}
                onRefresh={fetchData}
              />
            )}
          </>
        )}

        {/* Interviews Tab */}
        {tab === "interviews" && (
          <>
            {/* View toggle (T-R043) */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-[var(--color-gray-500)]">
                View:
              </span>
              <div className="flex gap-1 p-1 rounded-lg bg-[var(--color-gray-100)]">
                <button
                  type="button"
                  onClick={() => setInterviewView("list")}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                    interviewView === "list"
                      ? "bg-[var(--color-primary)] text-white"
                      : "text-[var(--color-gray-600)]"
                  }`}
                >
                  List
                </button>
                <button
                  type="button"
                  onClick={() => setInterviewView("calendar")}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                    interviewView === "calendar"
                      ? "bg-[var(--color-primary)] text-white"
                      : "text-[var(--color-gray-600)]"
                  }`}
                >
                  <Calendar className="h-3 w-3 inline mr-1" />
                  Calendar
                </button>
              </div>
            </div>

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
            ) : interviewView === "calendar" ? (
              <InterviewCalendar
                interviews={interviews}
                onSelectInterview={(iv) => {
                  if (iv.status === "completed") {
                    setFeedbackTarget({
                      interviewId: iv.id,
                      candidateId: iv.candidate_id,
                      candidateName: iv.candidate_name || `#${iv.candidate_id}`,
                    });
                  }
                }}
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
                        <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                          Status
                        </th>
                        <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                          Actions
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
                          <td className="py-3 px-3 text-center">
                            <StatusBadge
                              status={iv.status}
                              styles={JOB_STATUS_STYLES}
                            />
                          </td>
                          <td className="py-3 px-5 text-center">
                            {iv.status === "completed" && (
                              <AppButton
                                variant="outlined"
                                size="sm"
                                onClick={() =>
                                  setFeedbackTarget({
                                    interviewId: iv.id,
                                    candidateId: iv.candidate_id,
                                    candidateName:
                                      iv.candidate_name ||
                                      `#${iv.candidate_id}`,
                                  })
                                }
                              >
                                <Star className="h-3.5 w-3.5 mr-1" />
                                Submit Feedback
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

        {selectedCandidate && (
          <CandidateProfilePanel
            candidate={selectedCandidate}
            onClose={() => setSelectedCandidate(null)}
            onMoveStage={(id, stage) => {
              handleMoveStage(id, stage);
              setSelectedCandidate(null);
            }}
            onScheduleInterview={(c) => {
              setInterviewTarget({ id: c.id, name: c.name });
              setSelectedCandidate(null);
            }}
            onReject={(c) => {
              setRejectTarget({ id: c.id, name: c.name });
              setSelectedCandidate(null);
            }}
          />
        )}

        <RejectCandidateModal
          isOpen={rejectTarget !== null}
          candidateId={rejectTarget?.id ?? 0}
          candidateName={rejectTarget?.name ?? ""}
          onClose={() => setRejectTarget(null)}
          onSuccess={fetchData}
        />

        <TafepScanResultsModal
          isOpen={showScanModal}
          findings={scanFindings}
          onClose={() => {
            setShowScanModal(false);
            setScanFindings([]);
          }}
        />

        <CreateOfferModal
          isOpen={offerTarget !== null}
          onClose={() => setOfferTarget(null)}
          onSuccess={fetchData}
          candidateId={offerTarget?.id ?? 0}
          candidateName={offerTarget?.name ?? ""}
        />

        <SubmitFeedbackModal
          isOpen={feedbackTarget !== null}
          onClose={() => setFeedbackTarget(null)}
          onSuccess={fetchData}
          interviewId={feedbackTarget?.interviewId ?? 0}
          candidateId={feedbackTarget?.candidateId ?? 0}
          candidateName={feedbackTarget?.candidateName ?? ""}
        />

        <HireReviewModal
          isOpen={hireTarget !== null}
          target={hireTarget}
          onClose={() => setHireTarget(null)}
          onSuccess={() => {
            toast.success("Candidate hired and invitation sent");
            fetchData();
          }}
        />

        <ScreeningQuestionsModal
          isOpen={questionsTarget !== null}
          jobId={questionsTarget?.jobId ?? null}
          jobTitle={questionsTarget?.title ?? ""}
          onClose={() => setQuestionsTarget(null)}
        />
      </div>
    </AdminGuard>
  );
}

export default function RecruitmentPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-5xl mx-auto space-y-6 pb-8">
          <TableSkeleton />
        </div>
      }
    >
      <RecruitmentPageInner />
    </Suspense>
  );
}
