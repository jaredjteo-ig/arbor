"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AppCard,
  AppButton,
  AppInput,
  EmployeePicker,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  FolderKanban,
  ArrowLeft,
  Users,
  Clock,
  DollarSign,
  Plus,
  X,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  projectsApi,
  type Project,
  type ProjectAssignment,
  type TimesheetEntry,
  type ProjectCostSummary,
} from "@/services/api/projects";

/* ── Helpers ──────────────────────────────────────────────── */

function formatCurrency(amount: number): string {
  return `$${(amount ?? 0).toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(d: string): string {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("en-SG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/* ── Tab button ───────────────────────────────────────────── */

type Tab = "overview" | "assignments" | "timesheets" | "costs";

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
          <div className="h-4 w-28 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* ── Add Assignment Modal ─────────────────────────────────── */

function AddAssignmentModal({
  isOpen,
  onClose,
  onSuccess,
  projectId,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  projectId: number;
}) {
  const [employeeId, setEmployeeId] = useState<number | null>(null);
  const [role, setRole] = useState("");
  const [allocation, setAllocation] = useState("100");
  const [hourlyRate, setHourlyRate] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!employeeId) return;
    setIsSubmitting(true);
    try {
      await projectsApi.createAssignment(projectId, {
        employee_id: employeeId,
        role: role.trim(),
        allocation_pct: Number(allocation) || 100,
        hourly_rate: Number(hourlyRate) || 0,
      });
      toast.success("Team member assigned");
      setEmployeeId(null);
      setRole("");
      setAllocation("100");
      setHourlyRate("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to assign team member";
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
          <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
            Add Team Member
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <EmployeePicker
            label="Employee"
            value={employeeId}
            onChange={(id) => setEmployeeId(id)}
          />
          <AppInput
            label="Role"
            value={role}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setRole(e.target.value)
            }
            placeholder="e.g. Developer, Designer"
          />
          <div className="grid grid-cols-2 gap-3">
            <AppInput
              label="Allocation %"
              value={allocation}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setAllocation(e.target.value)
              }
              placeholder="100"
            />
            <AppInput
              label="Hourly Rate"
              value={hourlyRate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setHourlyRate(e.target.value)
              }
              placeholder="0.00"
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
              Assign
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "hr_manager";
  const projectId = Number(params.id);

  const [tab, setTab] = useState<Tab>("overview");
  const [project, setProject] = useState<Project | null>(null);
  const [assignments, setAssignments] = useState<ProjectAssignment[]>([]);
  const [timesheets, setTimesheets] = useState<TimesheetEntry[]>([]);
  const [costs, setCosts] = useState<ProjectCostSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAssignModal, setShowAssignModal] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [projRes, assignRes, tsRes] = await Promise.all([
        projectsApi.getProject(projectId),
        projectsApi.listAssignments(projectId),
        projectsApi.listTimesheets({ project_id: String(projectId) }),
      ]);
      setProject(projRes);
      setAssignments(assignRes.assignments ?? []);
      setTimesheets(tsRes.entries ?? []);

      try {
        const costRes = await projectsApi.getProjectCosts(projectId);
        setCosts(costRes);
      } catch {
        setCosts(null);
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load project details.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (error && !isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <AppButton
          variant="outlined"
          size="sm"
          onClick={() => router.push("/projects")}
        >
          <ArrowLeft className="h-4 w-4 mr-1" /> Back to Projects
        </AppButton>
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
      {/* Back button */}
      <AppButton
        variant="outlined"
        size="sm"
        onClick={() => router.push("/projects")}
      >
        <ArrowLeft className="h-4 w-4 mr-1" /> Back to Projects
      </AppButton>

      {/* Header */}
      <div className="flex items-center gap-3">
        <FolderKanban
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            {project?.name || "Loading..."}
          </h1>
          {project?.code && (
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              {project.code}
            </p>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-lg bg-[var(--color-gray-100)] w-fit">
        <TabButton
          active={tab === "overview"}
          label="Overview"
          onClick={() => setTab("overview")}
        />
        <TabButton
          active={tab === "assignments"}
          label="Assignments"
          onClick={() => setTab("assignments")}
        />
        <TabButton
          active={tab === "timesheets"}
          label="Timesheets"
          onClick={() => setTab("timesheets")}
        />
        <TabButton
          active={tab === "costs"}
          label="Costs"
          onClick={() => setTab("costs")}
        />
      </div>

      {/* Overview Tab */}
      {tab === "overview" && project && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <AppCard variant="flat">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-emerald-600" />
              <p className="text-xs text-[var(--color-gray-500)]">Budget</p>
            </div>
            <p className="text-xl font-bold text-[var(--color-gray-900)]">
              {formatCurrency(project.budget ?? 0)}
            </p>
          </AppCard>
          <AppCard variant="flat">
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-4 w-4 text-blue-600" />
              <p className="text-xs text-[var(--color-gray-500)]">
                Team Members
              </p>
            </div>
            <p className="text-xl font-bold text-[var(--color-gray-900)]">
              {assignments.length}
            </p>
          </AppCard>
          <AppCard variant="flat">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="h-4 w-4 text-amber-600" />
              <p className="text-xs text-[var(--color-gray-500)]">Timeline</p>
            </div>
            <p className="text-sm font-medium text-[var(--color-gray-900)]">
              {formatDate(project.start_date ?? "")} -{" "}
              {formatDate(project.end_date ?? "")}
            </p>
          </AppCard>
        </div>
      )}

      {/* Assignments Tab */}
      {tab === "assignments" && (
        <>
          {isAdmin && (
            <div className="flex justify-end">
              <AppButton
                variant="primary"
                size="sm"
                onClick={() => setShowAssignModal(true)}
              >
                <Plus className="h-4 w-4 mr-1" /> Add Member
              </AppButton>
            </div>
          )}
          {isLoading ? (
            <AppCard variant="standard">
              <div className="-mx-5 -my-4">
                <TableSkeleton />
              </div>
            </AppCard>
          ) : assignments.length === 0 ? (
            <EmptyState
              icon={<Users className="h-12 w-12" aria-hidden="true" />}
              message="No team members assigned"
              description="Add team members to start tracking time and costs."
            />
          ) : (
            <AppCard variant="standard">
              <div className="overflow-x-auto -mx-5 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--color-gray-200)]">
                      <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Employee
                      </th>
                      <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Role
                      </th>
                      <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Allocation
                      </th>
                      <th className="text-right py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Rate/hr
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {assignments.map((a) => (
                      <tr
                        key={a.id}
                        className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                      >
                        <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                          {a.employee_name || `#${a.employee_id}`}
                        </td>
                        <td className="py-3 px-3 text-[var(--color-gray-600)]">
                          {a.role || "-"}
                        </td>
                        <td className="py-3 px-3 text-center text-[var(--color-gray-700)]">
                          {a.allocation_pct ?? 100}%
                        </td>
                        <td className="py-3 px-5 text-right text-[var(--color-gray-700)]">
                          {(a.hourly_rate ?? 0) > 0
                            ? formatCurrency(a.hourly_rate)
                            : "-"}
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

      {/* Timesheets Tab */}
      {tab === "timesheets" && (
        <>
          {isLoading ? (
            <AppCard variant="standard">
              <div className="-mx-5 -my-4">
                <TableSkeleton />
              </div>
            </AppCard>
          ) : timesheets.length === 0 ? (
            <EmptyState
              icon={<Clock className="h-12 w-12" aria-hidden="true" />}
              message="No timesheet entries"
              description="Timesheet entries for this project will appear here."
            />
          ) : (
            <AppCard variant="standard">
              <div className="overflow-x-auto -mx-5 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--color-gray-200)]">
                      <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Employee
                      </th>
                      <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Date
                      </th>
                      <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Hours
                      </th>
                      <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Description
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {timesheets.map((ts) => (
                      <tr
                        key={ts.id}
                        className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                      >
                        <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                          {ts.employee_name || `#${ts.employee_id}`}
                        </td>
                        <td className="py-3 px-3 text-[var(--color-gray-600)]">
                          {formatDate(ts.entry_date ?? "")}
                        </td>
                        <td className="py-3 px-3 text-center text-[var(--color-gray-700)]">
                          {ts.hours ?? 0}h
                        </td>
                        <td className="py-3 px-5 text-[var(--color-gray-600)] truncate max-w-[200px]">
                          {ts.description || "-"}
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

      {/* Costs Tab */}
      {tab === "costs" && (
        <>
          {costs ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <AppCard variant="flat">
                <p className="text-xs text-[var(--color-gray-500)] mb-1">
                  Budget
                </p>
                <p className="text-lg font-bold text-[var(--color-gray-900)]">
                  {formatCurrency(costs.total_budget ?? 0)}
                </p>
              </AppCard>
              <AppCard variant="flat">
                <p className="text-xs text-[var(--color-gray-500)] mb-1">
                  Actual Cost
                </p>
                <p className="text-lg font-bold text-[var(--color-gray-900)]">
                  {formatCurrency(costs.total_actual ?? 0)}
                </p>
              </AppCard>
              <AppCard variant="flat">
                <p className="text-xs text-[var(--color-gray-500)] mb-1">
                  Timesheet Cost
                </p>
                <p className="text-lg font-bold text-[var(--color-gray-900)]">
                  {formatCurrency(costs.total_timesheet_cost ?? 0)}
                </p>
              </AppCard>
              <AppCard variant="flat">
                <p className="text-xs text-[var(--color-gray-500)] mb-1">
                  Variance
                </p>
                <p
                  className={`text-lg font-bold ${(costs.variance ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"}`}
                >
                  {(costs.variance ?? 0) >= 0 ? "+" : ""}
                  {formatCurrency(costs.variance ?? 0)}
                </p>
              </AppCard>
            </div>
          ) : (
            <EmptyState
              icon={<DollarSign className="h-12 w-12" aria-hidden="true" />}
              message="No cost data available"
              description="Cost information will appear once timesheets and expenses are recorded."
            />
          )}
        </>
      )}

      <AddAssignmentModal
        isOpen={showAssignModal}
        onClose={() => setShowAssignModal(false)}
        onSuccess={fetchData}
        projectId={projectId}
      />
    </div>
  );
}
