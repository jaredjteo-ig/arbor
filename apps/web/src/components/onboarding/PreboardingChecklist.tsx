"use client";

/**
 * PreboardingChecklist (T205) — admin (HR/owner) view of pre-boarding tasks
 * for an upcoming hire. Renders above their assignment progress on the
 * onboarding-detail screen.
 *
 * - GET  /onboarding/preboarding/{employee_id}  — list with overdue flags
 * - PATCH /onboarding/preboarding/{task_id}      — mark done
 *
 * Hidden when the API returns no tasks. Errors are surfaced inline so HR
 * can retry without losing context.
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ListChecks,
  RefreshCw,
} from "lucide-react";
import { AppButton, AppCard, toast } from "@/components/design-system";
import { onboardingApi, type PreboardingTask } from "@/services/api/onboarding";

export interface PreboardingChecklistProps {
  /** Employee ID whose pre-boarding tasks should be displayed. */
  employeeId: number;
  /** Optional callback fired after a task is marked done. */
  onTaskCompleted?: () => void;
}

const OWNER_ROLE_LABELS: Record<string, string> = {
  hr: "HR",
  manager: "Manager",
  it: "IT",
  office_manager: "Office Manager",
};

function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  try {
    return new Date(value).toLocaleDateString("en-SG", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

export function PreboardingChecklist({
  employeeId,
  onTaskCompleted,
}: PreboardingChecklistProps) {
  const { t } = useTranslation();
  const [tasks, setTasks] = useState<PreboardingTask[]>([]);
  const [counts, setCounts] = useState({ total: 0, pending: 0, done: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingTaskId, setSavingTaskId] = useState<number | null>(null);

  const fetchTasks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await onboardingApi.getPreboarding(employeeId);
      setTasks(res.tasks ?? []);
      setCounts({
        total: res.total ?? 0,
        pending: res.pending ?? 0,
        done: res.done ?? 0,
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : t("onboarding.preboarding.load_error", {
              defaultValue: "Unable to load pre-boarding tasks.",
            });
      setError(message);
      setTasks([]);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId, t]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  async function markDone(taskId: number) {
    setSavingTaskId(taskId);
    try {
      await onboardingApi.completePreboardingTask(taskId);
      toast.success(
        t("onboarding.preboarding.completed", {
          defaultValue: "Task marked as done",
        }),
      );
      await fetchTasks();
      onTaskCompleted?.();
    } catch {
      toast.error(
        t("onboarding.preboarding.complete_failed", {
          defaultValue: "Failed to update task. Please try again.",
        }),
      );
    } finally {
      setSavingTaskId(null);
    }
  }

  // Hide entirely when there's nothing to show (no tasks & no error).
  if (!isLoading && !error && tasks.length === 0) {
    return null;
  }

  return (
    <AppCard variant="flat">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <ListChecks
            className="h-5 w-5 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
            {t("onboarding.preboarding.title", {
              defaultValue: "Pre-boarding Checklist",
            })}
          </h2>
        </div>
        <AppButton
          variant="text"
          size="sm"
          onClick={fetchTasks}
          disabled={isLoading}
          aria-label={t("common.refresh", { defaultValue: "Refresh" })}
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
        </AppButton>
      </div>

      {!isLoading && !error && counts.total > 0 && (
        <p className="text-xs text-[var(--color-gray-500)] mb-3">
          {t("onboarding.preboarding.summary", {
            defaultValue: "{{done}} of {{total}} tasks complete",
            done: counts.done,
            total: counts.total,
          })}
        </p>
      )}

      {error ? (
        <div className="py-4 text-center">
          <p className="text-sm text-[var(--color-error)] mb-2">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchTasks}>
            {t("common.retry", { defaultValue: "Retry" })}
          </AppButton>
        </div>
      ) : isLoading ? (
        <div className="space-y-2 animate-pulse">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="h-12 bg-[var(--color-gray-100)] rounded-[8px]"
            />
          ))}
        </div>
      ) : (
        <ul className="space-y-2">
          {tasks.map((task) => {
            const isDone = task.status === "done";
            const isOverdue = !!task.is_overdue && !isDone;
            const ownerLabel =
              OWNER_ROLE_LABELS[task.owner_role] ?? task.owner_role;
            const saving = savingTaskId === task.id;

            return (
              <li
                key={task.id}
                className={`rounded-[8px] border p-3 flex items-start justify-between gap-3 ${
                  isDone
                    ? "border-emerald-200 bg-emerald-50/40"
                    : isOverdue
                      ? "border-amber-200 bg-amber-50/40"
                      : "border-[var(--color-gray-200)] bg-[var(--color-surface-card)]"
                }`}
              >
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  {isDone ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
                  ) : isOverdue ? (
                    <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                  ) : (
                    <Clock className="h-4 w-4 text-[var(--color-gray-400)] mt-0.5 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm font-medium ${
                        isDone
                          ? "text-[var(--color-gray-500)] line-through"
                          : "text-[var(--color-gray-900)]"
                      }`}
                    >
                      {task.task_name}
                    </p>
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-xs text-[var(--color-gray-500)]">
                      <span>
                        {t("onboarding.preboarding.owner", {
                          defaultValue: "Owner",
                        })}
                        : {ownerLabel}
                      </span>
                      {task.deadline_date && (
                        <span
                          className={
                            isOverdue ? "text-amber-700 font-medium" : ""
                          }
                        >
                          {t("onboarding.preboarding.due", {
                            defaultValue: "Due",
                          })}
                          : {formatDate(task.deadline_date)}
                          {isOverdue
                            ? ` (${t("onboarding.preboarding.overdue", { defaultValue: "overdue" })})`
                            : ""}
                        </span>
                      )}
                    </div>
                    {task.notes && (
                      <p className="text-xs text-[var(--color-gray-600)] mt-1 italic">
                        {task.notes}
                      </p>
                    )}
                  </div>
                </div>
                {!isDone && (
                  <AppButton
                    variant="outlined"
                    size="sm"
                    onClick={() => markDone(task.id)}
                    loading={saving}
                    disabled={saving}
                  >
                    {t("onboarding.preboarding.mark_done", {
                      defaultValue: "Mark done",
                    })}
                  </AppButton>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </AppCard>
  );
}

export default PreboardingChecklist;
