"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  EmptyState,
  toast,
} from "@/components/design-system";
import { Timer, Plus, Send, X } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  projectsApi,
  type TimesheetEntry,
  type Project,
} from "@/services/api/projects";

/* ── Helpers ──────────────────────────────────────────────── */

function formatDate(d: string): string {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("en-SG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function getWeekDates(): string[] {
  const now = new Date();
  const dayOfWeek = now.getDay();
  const monday = new Date(now);
  monday.setDate(now.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
  const dates: string[] = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    dates.push(d.toISOString().split("T")[0]);
  }
  return dates;
}

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/* ── Status badge ─────────────────────────────────────────── */

const STATUS_STYLES: Record<string, string> = {
  draft:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
  submitted: "bg-blue-50 text-blue-700 border-blue-200",
  approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

function StatusBadge({ status }: { status: string }) {
  const s = status || "pending";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[s] || STATUS_STYLES.draft}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
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
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-12 bg-[var(--color-gray-200)] rounded" />
          <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* ── Add Entry Modal ──────────────────────────────────────── */

function AddEntryModal({
  isOpen,
  onClose,
  onSuccess,
  projects,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  projects: Project[];
}) {
  const [projectId, setProjectId] = useState("");
  const [entryDate, setEntryDate] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [hours, setHours] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !hours) return;
    setIsSubmitting(true);
    try {
      await projectsApi.createTimesheet({
        project_id: Number(projectId),
        entry_date: entryDate,
        hours: Number(hours),
        description: description.trim(),
      });
      toast.success("Time entry saved");
      setProjectId("");
      setHours("");
      setDescription("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save time entry";
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
            <Timer className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Log Time
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
          <div>
            <label
              htmlFor="ts-project"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Project
            </label>
            <select
              id="ts-project"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] focus:border-[var(--color-surface-input-focus)]"
              required
            >
              <option value="">Select project</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <AppInput
              label="Date"
              variant="date"
              value={entryDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setEntryDate(e.target.value)
              }
              required
            />
            <AppInput
              label="Hours"
              value={hours}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setHours(e.target.value)
              }
              placeholder="e.g. 4"
              required
            />
          </div>
          <AppInput
            variant="textarea"
            label="Description"
            value={description}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
              setDescription(e.target.value)
            }
            placeholder="What did you work on?"
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
              Save Entry
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function MyTimesheetsPage() {
  const { user } = useAuth();

  const [entries, setEntries] = useState<TimesheetEntry[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  const weekDates = getWeekDates();

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [tsRes, projRes] = await Promise.all([
        projectsApi.listMyTimesheets(),
        projectsApi.listProjects(),
      ]);
      setEntries(tsRes.entries ?? []);
      setProjects(projRes.projects ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load timesheet data.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleSubmitEntry(entryId: number) {
    try {
      await projectsApi.submitTimesheet(entryId);
      toast.success("Timesheet entry submitted for approval");
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to submit entry";
      toast.error(message);
    }
  }

  /* Weekly summary */
  const weeklyHours = weekDates.map((date) => {
    const dayEntries = entries.filter((e) => e.entry_date === date);
    return dayEntries.reduce((sum, e) => sum + e.hours, 0);
  });
  const totalWeekHours = weeklyHours.reduce((sum, h) => sum + h, 0);

  if (error && !isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <div className="flex items-center gap-3">
          <Timer
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            My Timesheets
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
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Timer
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              My Timesheets
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Log hours against your assigned projects
            </p>
          </div>
        </div>
        <AppButton
          variant="primary"
          size="sm"
          onClick={() => setShowModal(true)}
        >
          <Plus className="h-4 w-4 mr-1" />
          Log Time
        </AppButton>
      </div>

      {/* Weekly summary */}
      <AppCard variant="flat">
        <h2 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
          This Week
        </h2>
        <div className="grid grid-cols-4 sm:grid-cols-7 gap-2 text-center">
          {DAY_LABELS.map((day, i) => (
            <div key={day}>
              <p className="text-[10px] font-medium text-[var(--color-gray-500)] uppercase mb-1">
                {day}
              </p>
              <div
                className={`rounded-lg py-2 ${weeklyHours[i] > 0 ? "bg-[var(--color-primary)] bg-opacity-10" : "bg-[var(--color-gray-50)]"}`}
              >
                <p
                  className={`text-sm font-bold ${weeklyHours[i] > 0 ? "text-[var(--color-primary)]" : "text-[var(--color-gray-400)]"}`}
                >
                  {weeklyHours[i] > 0 ? `${weeklyHours[i]}h` : "-"}
                </p>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 pt-3 border-t border-[var(--color-gray-200)] flex justify-between items-center">
          <p className="text-xs text-[var(--color-gray-500)]">
            Total this week
          </p>
          <p className="text-sm font-bold text-[var(--color-gray-900)]">
            {totalWeekHours}h
          </p>
        </div>
      </AppCard>

      {/* Entries list */}
      <div>
        <h2 className="text-base font-semibold text-[var(--color-gray-900)] mb-3">
          Recent Entries
        </h2>
        {isLoading ? (
          <AppCard variant="standard">
            <div className="-mx-5 -my-4">
              <TableSkeleton />
            </div>
          </AppCard>
        ) : entries.length === 0 ? (
          <EmptyState
            icon={<Timer className="h-12 w-12" aria-hidden="true" />}
            message="No time entries yet"
            description="Start logging hours against your projects."
          />
        ) : (
          <AppCard variant="standard">
            <div className="overflow-x-auto -mx-5 -my-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--color-gray-200)]">
                    <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                      Project
                    </th>
                    <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                      Date
                    </th>
                    <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                      Hours
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
                  {entries.map((entry) => (
                    <tr
                      key={entry.id}
                      className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                    >
                      <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                        {entry.project_name || "—"}
                      </td>
                      <td className="py-3 px-3 text-[var(--color-gray-600)]">
                        {formatDate(entry.entry_date)}
                      </td>
                      <td className="py-3 px-3 text-center text-[var(--color-gray-700)]">
                        {entry.hours}h
                      </td>
                      <td className="py-3 px-3 text-center">
                        <StatusBadge status={entry.status} />
                      </td>
                      <td className="py-3 px-5 text-center">
                        {entry.status === "draft" && (
                          <AppButton
                            variant="primary"
                            size="sm"
                            onClick={() => handleSubmitEntry(entry.id)}
                          >
                            <Send className="h-3.5 w-3.5 mr-1" />
                            Submit
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
      </div>

      <AddEntryModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSuccess={fetchData}
        projects={projects}
      />
    </div>
  );
}
