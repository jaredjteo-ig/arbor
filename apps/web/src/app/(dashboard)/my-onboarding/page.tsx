"use client";

import { useState, useEffect, useCallback, useRef } from "react";
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
} from "lucide-react";
import {
  onboardingApi,
  type MyOnboardingProgress,
  type StepProgressWithStep,
  type AssignmentModuleSummary,
} from "@/services/api/onboarding";

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

/* ── Checklist items parsing ─────────────────────────────── */

interface ParsedChecklistItem {
  id: string;
  label: string;
  checked: boolean;
}

function parseChecklistItems(raw: string): ParsedChecklistItem[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed.map((item, idx) => ({
        id: item.id ?? String(idx),
        label: item.label ?? item.text ?? String(item),
        checked: !!item.checked,
      }));
    }
  } catch {
    // If not valid JSON, treat as newline-separated text
    return raw
      .split("\n")
      .filter((line) => line.trim())
      .map((line, idx) => ({
        id: String(idx),
        label: line.trim(),
        checked: false,
      }));
  }
  return [];
}

/* ── Content Step ────────────────────────────────────────── */

function ContentStepBody({
  sp,
  onStepCompleted,
}: {
  sp: StepProgressWithStep;
  onStepCompleted: () => void;
}) {
  const [showContent, setShowContent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const isCompleted = sp.status === "completed";

  async function handleMarkRead() {
    setSubmitting(true);
    try {
      await onboardingApi.completeStep(sp.id);
      toast.success("Step marked as read");
      onStepCompleted();
    } catch {
      toast.error("Failed to mark as read. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-2 space-y-2">
      {!showContent && !isCompleted && (
        <AppButton
          variant="outlined"
          size="sm"
          onClick={() => setShowContent(true)}
        >
          <BookOpen className="h-4 w-4 mr-1" />
          Read
        </AppButton>
      )}
      {(showContent || isCompleted) && sp.body_content && (
        <div className="rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-gray-50)] p-4 text-sm text-[var(--color-gray-700)] whitespace-pre-wrap">
          {sp.body_content}
        </div>
      )}
      {showContent && !isCompleted && (
        <AppButton
          variant="primary"
          size="sm"
          onClick={handleMarkRead}
          loading={submitting}
        >
          Mark as Read
        </AppButton>
      )}
    </div>
  );
}

/* ── Checklist Step ──────────────────────────────────────── */

function ChecklistStepBody({
  sp,
  onStepCompleted,
}: {
  sp: StepProgressWithStep;
  onStepCompleted: () => void;
}) {
  const [items, setItems] = useState<ParsedChecklistItem[]>(() =>
    parseChecklistItems(sp.checklist_items),
  );
  const [submitting, setSubmitting] = useState(false);
  const isCompleted = sp.status === "completed";

  function toggleItem(id: string) {
    if (isCompleted) return;
    setItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, checked: !item.checked } : item,
      ),
    );
  }

  const allChecked = items.length > 0 && items.every((item) => item.checked);

  async function handleComplete() {
    setSubmitting(true);
    try {
      await onboardingApi.completeStep(sp.id);
      toast.success("Checklist completed");
      onStepCompleted();
    } catch {
      toast.error("Failed to complete checklist. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-2 space-y-2">
      <div className="space-y-1.5">
        {items.map((item) => (
          <label
            key={item.id}
            className="flex items-center gap-2 text-sm cursor-pointer"
          >
            <input
              type="checkbox"
              checked={isCompleted || item.checked}
              disabled={isCompleted}
              onChange={() => toggleItem(item.id)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
            />
            <span
              className={
                isCompleted || item.checked
                  ? "text-[var(--color-gray-500)] line-through"
                  : "text-[var(--color-gray-700)]"
              }
            >
              {item.label}
            </span>
          </label>
        ))}
      </div>
      {!isCompleted && (
        <AppButton
          variant="primary"
          size="sm"
          onClick={handleComplete}
          disabled={!allChecked}
          loading={submitting}
        >
          Complete
        </AppButton>
      )}
    </div>
  );
}

/* ── Document Upload Step ────────────────────────────────── */

function DocumentUploadStepBody({
  sp,
  onStepCompleted,
}: {
  sp: StepProgressWithStep;
  onStepCompleted: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isCompleted = sp.status === "completed";

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await onboardingApi.uploadStepDocument(sp.id, formData);
      toast.success("Document uploaded");
      onStepCompleted();
    } catch {
      toast.error("Failed to upload document. Please try again.");
    } finally {
      setSubmitting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  return (
    <div className="mt-2 space-y-2">
      {isCompleted && sp.document_url ? (
        <div className="flex items-center gap-2 text-sm text-emerald-600">
          <CheckCircle2 className="h-4 w-4" />
          <span>
            Uploaded: {sp.document_url.split("/").pop() ?? "document"}
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleUpload}
            disabled={submitting}
            className="text-sm text-[var(--color-gray-600)] file:mr-3 file:rounded-[8px] file:border-0 file:bg-[var(--color-primary)] file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white file:cursor-pointer hover:file:bg-[var(--color-primary-light)] disabled:opacity-50"
          />
          {submitting && (
            <RefreshCw className="h-4 w-4 text-[var(--color-gray-400)] animate-spin" />
          )}
        </div>
      )}
    </div>
  );
}

/* ── Policy Acknowledgment Step ──────────────────────────── */

function PolicyAckStepBody({
  sp,
  onStepCompleted,
}: {
  sp: StepProgressWithStep;
  onStepCompleted: () => void;
}) {
  const [acknowledged, setAcknowledged] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const isCompleted = sp.status === "completed";

  async function handleAcknowledge() {
    setSubmitting(true);
    try {
      await onboardingApi.acknowledgeStep(sp.id);
      toast.success("Policy acknowledged");
      onStepCompleted();
    } catch {
      toast.error("Failed to acknowledge policy. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-2 space-y-2">
      {sp.policy_id && (
        <a
          href={`/policies/${sp.policy_id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm text-[var(--color-primary)] hover:underline"
        >
          <FileText className="h-3.5 w-3.5" />
          Read Policy
        </a>
      )}
      {isCompleted ? (
        <div className="flex items-center gap-2 text-sm text-emerald-600">
          <CheckCircle2 className="h-4 w-4" />
          <span>Acknowledged</span>
        </div>
      ) : (
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
            />
            <span className="text-[var(--color-gray-700)]">
              I acknowledge that I have read and understood this policy
            </span>
          </label>
          <AppButton
            variant="primary"
            size="sm"
            onClick={handleAcknowledge}
            disabled={!acknowledged}
            loading={submitting}
          >
            Submit Acknowledgment
          </AppButton>
        </div>
      )}
    </div>
  );
}

/* ── Approval Step ───────────────────────────────────────── */

function ApprovalStepBody({ sp }: { sp: StepProgressWithStep }) {
  const isCompleted = sp.status === "completed";

  return (
    <div className="mt-2">
      {isCompleted ? (
        <div className="flex items-center gap-2 text-sm text-emerald-600">
          <CheckCircle2 className="h-4 w-4" />
          <span>
            Approved
            {sp.completed_at
              ? ` on ${new Date(sp.completed_at).toLocaleDateString("en-SG", { day: "numeric", month: "short", year: "numeric" })}`
              : ""}
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm text-[var(--color-gray-500)]">
          <Clock className="h-4 w-4" />
          <span>Pending approval from HR</span>
        </div>
      )}
    </div>
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
          <ContentStepBody sp={sp} onStepCompleted={onStepCompleted} />
        )}
        {sp.step_type === "checklist" && (
          <ChecklistStepBody sp={sp} onStepCompleted={onStepCompleted} />
        )}
        {sp.step_type === "document_upload" && (
          <DocumentUploadStepBody sp={sp} onStepCompleted={onStepCompleted} />
        )}
        {sp.step_type === "policy_acknowledgment" && (
          <PolicyAckStepBody sp={sp} onStepCompleted={onStepCompleted} />
        )}
        {sp.step_type === "approval" && <ApprovalStepBody sp={sp} />}
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
              {mod.module_name}
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

/* ── Page ────────────────────────────────────────────────── */

export default function MyOnboardingPage() {
  const [data, setData] = useState<MyOnboardingProgress | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noAssignment, setNoAssignment] = useState(false);

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
            : "Unable to load your onboarding progress. Please try again.";
        setError(message);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

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
              My Onboarding
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              {assignment?.template_name ?? "Track your onboarding progress"}
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
            Refresh
          </AppButton>
        )}
      </div>

      {/* Overall progress bar */}
      {!isLoading && !noAssignment && !error && assignment && (
        <AppCard variant="flat">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[var(--color-gray-700)]">
              Overall Progress
            </span>
            <span className="text-sm font-bold text-[var(--color-gray-900)]">
              {Math.round(progressPercent)}%
            </span>
          </div>
          <div className="h-3 rounded-full bg-[var(--color-gray-100)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--color-primary)] transition-all"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <p className="text-xs text-[var(--color-gray-500)] mt-2">
            {completedSteps} of {totalSteps} step{totalSteps !== 1 ? "s" : ""}{" "}
            completed
          </p>
        </AppCard>
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
              Try again
            </AppButton>
          </div>
        </AppCard>
      ) : noAssignment ? (
        <EmptyState
          icon={<ClipboardCheck className="h-12 w-12" aria-hidden="true" />}
          message="No onboarding tasks assigned"
          description="If you've just joined, your HR team will set this up for you."
        />
      ) : (
        <div className="space-y-3">
          {modules.map((mod) => (
            <ModuleCard
              key={mod.module_id}
              mod={mod}
              onStepCompleted={fetchProgress}
            />
          ))}
        </div>
      )}
    </div>
  );
}
