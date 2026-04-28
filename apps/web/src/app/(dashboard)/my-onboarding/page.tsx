"use client";

/**
 * My Onboarding (T201) — employee self-service onboarding view.
 *
 * - GET /onboarding/my-progress  → shows the active assignment, modules,
 *   step progress, completion percent, due date.
 * - Step renderers (T202) live in apps/web/src/components/onboarding/steps/
 *   and are dispatched per `step_type`.
 * - Progress bar (T204) — overall + module-level breakdown via tooltip.
 * - Pre-boarding (T205) — admin (HR/owner) viewing an upcoming hire can
 *   pass `?employee_id=N` and see the pre-boarding checklist above the
 *   regular progress view.
 * - Pulse check-ins and milestone timeline render below modules when
 *   the backend has data for the current employee.
 */

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslation } from "react-i18next";
import {
  AppCard,
  AppButton,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  ClipboardCheck,
  ChevronDown,
  ChevronRight,
  BookOpen,
  CheckSquare,
  Upload,
  FileText,
  UserCheck,
  Clock,
  CheckCircle2,
  PartyPopper,
  RefreshCw,
  Mail,
  Users,
  CalendarDays,
  Star,
  MessageSquare,
  ListChecks,
} from "lucide-react";
import {
  onboardingApi,
  type MyOnboardingProgress,
  type StepProgressWithStep,
  type AssignmentModuleSummary,
  type OnboardingMilestone,
  type PulseSurvey,
} from "@/services/api/onboarding";
import { useAuth } from "@/contexts/AuthContext";
import {
  ContentStep,
  ChecklistStep,
  DocumentUploadStep,
  PolicyAcknowledgmentStep,
  FormStep,
  ApprovalStep,
} from "@/components/onboarding/steps";
import { ProgressBar } from "@/components/onboarding/ProgressBar";
import { PreboardingChecklist } from "@/components/onboarding/PreboardingChecklist";

/* ── Phase badge styles ──────────────────────────────────── */

const PHASE_STYLES: Record<
  string,
  { bg: string; text: string; label: string }
> = {
  orientation: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    label: "Orientation",
  },
  compliance: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    label: "Compliance",
  },
  benefits: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    label: "Benefits",
  },
  probation: {
    bg: "bg-purple-50",
    text: "text-purple-700",
    label: "Probation",
  },
  custom: {
    bg: "bg-[var(--color-gray-100)]",
    text: "text-[var(--color-gray-700)]",
    label: "Custom",
  },
};

function PhaseBadge({ phase }: { phase: string }) {
  const style = PHASE_STYLES[phase] ?? PHASE_STYLES.custom;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  );
}

/* ── Step status badge ───────────────────────────────────── */

const STATUS_STYLES: Record<
  string,
  { bg: string; text: string; label: string }
> = {
  pending: {
    bg: "bg-[var(--color-gray-100)]",
    text: "text-[var(--color-gray-600)]",
    label: "Pending",
  },
  in_progress: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    label: "In Progress",
  },
  completed: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    label: "Completed",
  },
  skipped: {
    bg: "bg-[var(--color-gray-100)]",
    text: "text-[var(--color-gray-500)]",
    label: "Skipped",
  },
};

function StepStatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  );
}

/* ── Step type icon ──────────────────────────────────────── */

function StepIcon({ stepType }: { stepType: string }) {
  const iconClass = "h-4 w-4 shrink-0";
  switch (stepType) {
    case "content":
      return <BookOpen className={`${iconClass} text-blue-500`} />;
    case "checklist":
      return <CheckSquare className={`${iconClass} text-emerald-500`} />;
    case "document_upload":
      return <Upload className={`${iconClass} text-amber-500`} />;
    case "policy_acknowledgment":
      return <FileText className={`${iconClass} text-purple-500`} />;
    case "form":
      return <ListChecks className={`${iconClass} text-indigo-500`} />;
    case "approval":
      return (
        <UserCheck className={`${iconClass} text-[var(--color-gray-500)]`} />
      );
    default:
      return <Clock className={`${iconClass} text-[var(--color-gray-400)]`} />;
  }
}

/* ── Skeleton ────────────────────────────────────────────── */

function ModuleCardSkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse space-y-3">
        <div className="flex items-center gap-3">
          <div className="h-5 w-40 bg-[var(--color-gray-200)] rounded" />
          <div className="h-5 w-20 bg-[var(--color-gray-200)] rounded-full" />
        </div>
        <div className="h-3 w-28 bg-[var(--color-gray-100)] rounded" />
        <div className="h-2 w-full bg-[var(--color-gray-200)] rounded-full" />
      </div>
    </AppCard>
  );
}

/* ── Step Row ────────────────────────────────────────────── */

function StepRow({
  sp,
  onStepCompleted,
}: {
  sp: StepProgressWithStep;
  onStepCompleted: () => void;
}) {
  return (
    <div className="py-3 border-b border-[var(--color-gray-100)] last:border-0">
      <div className="flex items-center gap-2">
        <StepIcon stepType={sp.step_type} />
        <span className="text-sm font-medium text-[var(--color-gray-900)] flex-1">
          {sp.step_title}
        </span>
        <StepStatusBadge status={sp.status} />
      </div>
      {sp.step_description && (
        <p className="text-xs text-[var(--color-gray-500)] mt-1 ml-6">
          {sp.step_description}
        </p>
      )}

      <div className="ml-6">
        {sp.step_type === "content" && (
          <ContentStep sp={sp} onStepCompleted={onStepCompleted} />
        )}
        {sp.step_type === "checklist" && (
          <ChecklistStep sp={sp} onStepCompleted={onStepCompleted} />
        )}
        {sp.step_type === "document_upload" && (
          <DocumentUploadStep sp={sp} onStepCompleted={onStepCompleted} />
        )}
        {sp.step_type === "policy_acknowledgment" && (
          <PolicyAcknowledgmentStep sp={sp} onStepCompleted={onStepCompleted} />
        )}
        {sp.step_type === "form" && (
          <FormStep sp={sp} onStepCompleted={onStepCompleted} />
        )}
        {sp.step_type === "approval" && <ApprovalStep sp={sp} />}
      </div>
    </div>
  );
}

/* ── Module Card ─────────────────────────────────────────── */

function ModuleCard({
  mod,
  onStepCompleted,
}: {
  mod: AssignmentModuleSummary;
  onStepCompleted: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const steps = mod.steps ?? [];
  const totalSteps = steps.length;
  const completedSteps = steps.filter((s) => s.status === "completed").length;
  const progressPercent =
    totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
  const allComplete = completedSteps === totalSteps && totalSteps > 0;

  return (
    <AppCard variant="flat">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left flex items-center justify-between gap-3 min-h-[44px]"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {allComplete ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
            ) : expanded ? (
              <ChevronDown className="h-5 w-5 text-[var(--color-gray-400)] shrink-0" />
            ) : (
              <ChevronRight className="h-5 w-5 text-[var(--color-gray-400)] shrink-0" />
            )}
            <span className="text-base font-semibold text-[var(--color-gray-900)]">
              {mod.module_name ?? mod.name}
            </span>
            <PhaseBadge phase={mod.phase} />
          </div>
          <div className="flex items-center gap-4 mt-1 ml-7 text-xs text-[var(--color-gray-500)]">
            <span>
              {completedSteps} of {totalSteps} step{totalSteps !== 1 ? "s" : ""}{" "}
              completed
            </span>
          </div>
        </div>
        <div className="text-sm font-medium text-[var(--color-gray-600)] shrink-0">
          {progressPercent}%
        </div>
      </button>

      {/* Module progress bar */}
      <div className="mt-3 h-1.5 rounded-full bg-[var(--color-gray-100)] overflow-hidden">
        <div
          className="h-full rounded-full bg-[var(--color-primary)] transition-all"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Expanded steps */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-[var(--color-gray-200)]">
          {steps.map((sp) => (
            <StepRow key={sp.id} sp={sp} onStepCompleted={onStepCompleted} />
          ))}
        </div>
      )}
    </AppCard>
  );
}

/* ── Buddy Card ─────────────────────────────────────────── */

function BuddyCard({
  name,
  email,
  designation,
  department,
}: {
  name: string;
  email: string;
  designation?: string;
  department?: string;
}) {
  const subtitle = [designation, department].filter(Boolean).join(" - ");
  return (
    <AppCard variant="flat">
      <div className="flex items-start gap-4">
        <div className="flex items-center justify-center h-10 w-10 rounded-full bg-[var(--color-primary-bg)] shrink-0">
          <Users
            className="h-5 w-5 text-[var(--color-primary)]"
            aria-hidden="true"
          />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Your Onboarding Buddy
          </h3>
          <p className="text-base font-medium text-[var(--color-gray-900)] mt-1">
            {name}
          </p>
          {subtitle && (
            <p className="text-sm text-[var(--color-gray-500)]">{subtitle}</p>
          )}
          {email && (
            <a
              href={`mailto:${email}`}
              className="inline-flex items-center gap-1.5 text-sm text-[var(--color-primary)] hover:underline mt-2"
            >
              <Mail className="h-3.5 w-3.5" />
              {email}
            </a>
          )}
          <p className="text-xs text-[var(--color-gray-500)] mt-2">
            Your buddy is here to help you settle in. Don&apos;t hesitate to
            reach out!
          </p>
        </div>
      </div>
    </AppCard>
  );
}

/* ── Celebration ─────────────────────────────────────────── */

function CelebrationBanner() {
  return (
    <AppCard variant="flat">
      <div className="flex flex-col items-center text-center py-4">
        <PartyPopper
          className="h-10 w-10 text-amber-500 mb-3"
          aria-hidden="true"
        />
        <h2 className="text-lg font-bold text-[var(--color-gray-900)]">
          Onboarding Complete!
        </h2>
        <p className="text-sm text-[var(--color-gray-500)] mt-1 max-w-md">
          Congratulations! You have completed all your onboarding tasks. Welcome
          aboard!
        </p>
      </div>
    </AppCard>
  );
}

/* ── Milestone helpers ──────────────────────────────────── */

const MILESTONE_LABELS: Record<string, string> = {
  day_30: "30-Day Review",
  day_60: "60-Day Review",
  day_90: "90-Day Review",
};

function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null;
  try {
    const target = new Date(dateStr);
    const now = new Date();
    const diff = target.getTime() - now.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}

function formatCountdown(days: number | null): string {
  if (days === null) return "";
  if (days < 0)
    return `${Math.abs(days)} day${Math.abs(days) !== 1 ? "s" : ""} ago`;
  if (days === 0) return "Today";
  return `in ${days} day${days !== 1 ? "s" : ""}`;
}

/* ── Star Rating Input ───────────────────────────────────── */

function StarRating({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  const [hover, setHover] = useState(0);

  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          onMouseEnter={() => setHover(star)}
          onMouseLeave={() => setHover(0)}
          className="p-0.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] rounded"
          aria-label={`Rate ${star} out of 5`}
        >
          <Star
            className={`h-5 w-5 transition-colors ${
              star <= (hover || value)
                ? "fill-amber-400 text-amber-400"
                : "fill-none text-[var(--color-gray-300)]"
            }`}
          />
        </button>
      ))}
    </div>
  );
}

/* ── Pulse Check-In (employee view) ─────────────────────── */

function PulseCheckIn() {
  const [surveys, setSurveys] = useState<PulseSurvey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [scores, setScores] = useState<Record<number, number>>({});
  const [comments, setComments] = useState<Record<number, string>>({});

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await onboardingApi.getMySurveys();
        if (!cancelled) setSurveys(res.surveys ?? []);
      } catch {
        /* Non-critical — degrade gracefully */
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) return null;
  if (surveys.length === 0 && !submitted) return null;

  if (submitted) {
    return (
      <AppCard variant="flat">
        <div className="py-6 text-center">
          <CheckCircle2
            className="h-10 w-10 text-emerald-500 mx-auto mb-3"
            aria-hidden="true"
          />
          <h3 className="text-base font-semibold text-[var(--color-gray-900)] mb-1">
            Thank you for your feedback!
          </h3>
          <p className="text-sm text-[var(--color-gray-500)]">
            Your responses help us improve the onboarding experience.
          </p>
        </div>
      </AppCard>
    );
  }

  const survey = surveys[0];
  const questions = survey.questions ?? [];
  const typeLabel =
    survey.survey_type === "day_60" ? "Day 60 Check-in" : "Day 30 Check-in";

  const allRated = questions.every(
    (q) => scores[q.number] !== undefined && scores[q.number] > 0,
  );

  async function handleSubmit() {
    if (!allRated) return;
    setIsSubmitting(true);
    try {
      const responses = questions.map((q) => ({
        question_number: q.number,
        score: scores[q.number],
        comment: comments[q.number] ?? "",
      }));
      await onboardingApi.respondToSurvey(survey.id, responses);
      setSubmitted(true);
      toast.success("Pulse check-in submitted successfully.");
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to submit your check-in. Please try again.";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppCard variant="flat">
      <div className="flex items-center gap-2 mb-4">
        <MessageSquare
          className="h-5 w-5 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
          {typeLabel}
        </h2>
      </div>
      <p className="text-sm text-[var(--color-gray-500)] mb-5">
        We&apos;d love to hear how your onboarding is going. Please rate each
        statement below.
      </p>

      <div className="space-y-5">
        {questions.map((q) => (
          <div key={q.number}>
            <div className="flex items-start justify-between gap-4 mb-1.5">
              <label className="text-sm text-[var(--color-gray-700)] flex-1">
                {q.number}. {q.text}
              </label>
              <StarRating
                value={scores[q.number] ?? 0}
                onChange={(v) =>
                  setScores((prev) => ({ ...prev, [q.number]: v }))
                }
              />
            </div>
            <textarea
              value={comments[q.number] ?? ""}
              onChange={(e) =>
                setComments((prev) => ({
                  ...prev,
                  [q.number]: e.target.value,
                }))
              }
              placeholder="Optional comment..."
              rows={2}
              className="
                w-full rounded-[8px] border px-3 py-2 text-sm
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                placeholder:text-[var(--color-gray-400)]
                transition-colors resize-none
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                focus:border-[var(--color-surface-input-focus)]
              "
            />
          </div>
        ))}
      </div>

      <div className="mt-5 flex justify-end">
        <AppButton
          variant="primary"
          size="sm"
          onClick={handleSubmit}
          disabled={!allRated || isSubmitting}
        >
          {isSubmitting ? "Submitting..." : "Submit Check-in"}
        </AppButton>
      </div>
    </AppCard>
  );
}

/* ── Milestone Timeline (employee view) ────────────────── */

function MilestoneTimeline() {
  const [milestones, setMilestones] = useState<OnboardingMilestone[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await onboardingApi.getMyMilestones();
        if (!cancelled) setMilestones(res.milestones ?? []);
      } catch {
        /* Non-critical — degrade gracefully */
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) {
    return (
      <AppCard variant="flat">
        <div className="animate-pulse space-y-3">
          <div className="h-5 w-40 bg-[var(--color-gray-200)] rounded" />
          <div className="h-16 bg-[var(--color-gray-100)] rounded" />
        </div>
      </AppCard>
    );
  }

  if (milestones.length === 0) return null;

  return (
    <AppCard variant="flat">
      <div className="flex items-center gap-2 mb-4">
        <CalendarDays
          className="h-5 w-5 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
          Upcoming Reviews
        </h2>
      </div>
      <div className="relative">
        {/* Vertical connector line */}
        <div className="absolute left-[15px] top-4 bottom-4 w-0.5 bg-[var(--color-gray-200)]" />
        <div className="space-y-4">
          {milestones.map((m) => {
            const days = daysUntil(m.scheduled_date);
            const isCompleted = m.status === "completed";
            const isPast = days !== null && days < 0 && !isCompleted;

            return (
              <div key={m.id} className="flex items-start gap-3 relative">
                {/* Timeline dot */}
                <div
                  className={`w-[30px] h-[30px] rounded-full flex items-center justify-center shrink-0 z-10 ${
                    isCompleted
                      ? "bg-emerald-500"
                      : isPast
                        ? "bg-amber-400"
                        : "bg-[var(--color-gray-200)]"
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4 text-white" />
                  ) : (
                    <CalendarDays
                      className={`h-4 w-4 ${isPast ? "text-white" : "text-[var(--color-gray-500)]"}`}
                    />
                  )}
                </div>
                {/* Content */}
                <div className="flex-1 min-w-0 pb-1">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span
                      className={`text-sm font-medium ${
                        isCompleted
                          ? "text-emerald-700"
                          : "text-[var(--color-gray-900)]"
                      }`}
                    >
                      {MILESTONE_LABELS[m.milestone_type] ?? m.milestone_type}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        isCompleted
                          ? "bg-emerald-50 text-emerald-700"
                          : isPast
                            ? "bg-amber-50 text-amber-700"
                            : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)]"
                      }`}
                    >
                      {isCompleted
                        ? "Completed"
                        : isPast
                          ? "Overdue"
                          : "Upcoming"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-0.5 text-xs text-[var(--color-gray-500)]">
                    {m.scheduled_date && (
                      <span>
                        {new Date(m.scheduled_date).toLocaleDateString(
                          "en-SG",
                          {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          },
                        )}
                      </span>
                    )}
                    {days !== null && !isCompleted && (
                      <span
                        className={isPast ? "text-amber-600 font-medium" : ""}
                      >
                        {formatCountdown(days)}
                      </span>
                    )}
                    {isCompleted && m.completed_at && (
                      <span className="text-emerald-600">
                        Completed{" "}
                        {new Date(m.completed_at).toLocaleDateString("en-SG", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </span>
                    )}
                  </div>
                  {m.notes && (
                    <p className="text-xs text-[var(--color-gray-500)] mt-1 italic">
                      {m.notes}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AppCard>
  );
}

/* ── Page ────────────────────────────────────────────────── */

function formatDueDate(value: string | null): string | null {
  if (!value) return null;
  try {
    return new Date(value).toLocaleDateString("en-SG", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return null;
  }
}

export default function MyOnboardingPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const searchParams = useSearchParams();

  const [data, setData] = useState<MyOnboardingProgress | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noAssignment, setNoAssignment] = useState(false);

  // T205 admin override: HR/owner can pass ?employee_id=N to view someone's
  // pre-boarding checklist alongside this page. The pre-boarding endpoint
  // requires HR/owner role server-side, so unauthorised users get a 403 from
  // the API and the section just shows an inline error.
  const queryEmployeeId = searchParams?.get("employee_id");
  const isAdminRole = user?.role === "owner" || user?.role === "hr_manager";
  const adminEmployeeId =
    isAdminRole && queryEmployeeId ? Number(queryEmployeeId) : null;
  const adminViewing =
    adminEmployeeId !== null && !Number.isNaN(adminEmployeeId);

  const fetchProgress = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setNoAssignment(false);
    try {
      const result = await onboardingApi.getMyProgress();
      if (!result.assignment) {
        setNoAssignment(true);
        setData(null);
      } else {
        setData(result);
      }
    } catch (err: unknown) {
      if (
        err &&
        typeof err === "object" &&
        "status" in err &&
        (err as { status: number }).status === 404
      ) {
        setNoAssignment(true);
      } else {
        const message =
          err instanceof Error
            ? err.message
            : t("onboarding.my.load_error", {
                defaultValue:
                  "Unable to load your onboarding progress. Please try again.",
              });
        setError(message);
      }
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);

  const assignment = data?.assignment ?? null;
  const modules = assignment?.modules ?? [];
  const progressPercent = assignment?.completion_percentage ?? 0;
  const totalSteps = modules.reduce(
    (acc, m) => acc + (m.steps ?? []).length,
    0,
  );
  const completedSteps = modules.reduce(
    (acc, m) =>
      acc + (m.steps ?? []).filter((s) => s.status === "completed").length,
    0,
  );
  const isComplete =
    assignment?.status === "completed" || progressPercent >= 100;
  const dueDateLabel = formatDueDate(assignment?.due_date ?? null);

  // Build module breakdown for ProgressBar tooltip.
  const moduleBreakdown = modules.map((m) => {
    const steps = m.steps ?? [];
    return {
      name: m.module_name ?? m.name ?? "Module",
      completed: steps.filter((s) => s.status === "completed").length,
      total: steps.length,
    };
  });

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <ClipboardCheck
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              {t("onboarding.my.page_title", { defaultValue: "My Onboarding" })}
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              {assignment?.template_name ??
                t("onboarding.my.page_description", {
                  defaultValue: "Track your onboarding progress",
                })}
              {dueDateLabel && (
                <span className="ml-2 text-[var(--color-gray-400)]">
                  ·{" "}
                  {t("onboarding.my.due_by", {
                    defaultValue: "Due by {{date}}",
                    date: dueDateLabel,
                  })}
                </span>
              )}
            </p>
          </div>
        </div>
        {!isLoading && !noAssignment && (
          <AppButton
            variant="text"
            size="sm"
            onClick={fetchProgress}
            disabled={isLoading}
          >
            <RefreshCw
              className={`h-4 w-4 mr-1 ${isLoading ? "animate-spin" : ""}`}
            />
            {t("common.refresh", { defaultValue: "Refresh" })}
          </AppButton>
        )}
      </div>

      {/* T205: Pre-boarding checklist (admin viewing an upcoming hire) */}
      {adminViewing && <PreboardingChecklist employeeId={adminEmployeeId!} />}

      {/* Overall progress bar (T204) */}
      {!isLoading && !noAssignment && !error && assignment && (
        <AppCard variant="flat">
          <ProgressBar
            percent={progressPercent}
            modules={moduleBreakdown}
            label={t("onboarding.progress.overall", {
              defaultValue: "Overall Progress",
            })}
          />
          <p className="text-xs text-[var(--color-gray-500)] mt-2">
            {t("onboarding.progress.steps_count", {
              defaultValue: "{{done}} of {{total}} steps completed",
              done: completedSteps,
              total: totalSteps,
            })}
          </p>
        </AppCard>
      )}

      {/* Onboarding buddy */}
      {!isLoading && !noAssignment && !error && assignment?.buddy_name && (
        <BuddyCard
          name={assignment.buddy_name}
          email={assignment.buddy_email ?? ""}
          designation={assignment.buddy_designation}
          department={assignment.buddy_department}
        />
      )}

      {/* Celebration */}
      {!isLoading && isComplete && <CelebrationBanner />}

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <ModuleCardSkeleton key={n} />
          ))}
        </div>
      ) : error ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={fetchProgress}>
              {t("common.retry", { defaultValue: "Try again" })}
            </AppButton>
          </div>
        </AppCard>
      ) : noAssignment ? (
        <EmptyState
          icon={<ClipboardCheck className="h-12 w-12" aria-hidden="true" />}
          message={t("onboarding.my.empty_title", {
            defaultValue: "No onboarding tasks assigned",
          })}
          description={t("onboarding.my.empty_description", {
            defaultValue:
              "If you've just joined, your HR team will set this up for you.",
          })}
        />
      ) : (
        <div className="space-y-3">
          {modules.map((mod) => (
            <ModuleCard
              key={mod.module_id ?? mod.id}
              mod={mod}
              onStepCompleted={fetchProgress}
            />
          ))}
        </div>
      )}

      {/* Pulse check-in — shown when a pending survey exists */}
      {!isLoading && !noAssignment && !error && assignment && <PulseCheckIn />}

      {/* Milestone timeline — shown below modules when assignment is active */}
      {!isLoading && !noAssignment && !error && assignment && (
        <MilestoneTimeline />
      )}
    </div>
  );
}
