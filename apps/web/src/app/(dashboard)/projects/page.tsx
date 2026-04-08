"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  AppCard,
  AppButton,
  AppInput,
  EmptyState,
  toast,
} from "@/components/design-system";
import { FolderKanban, Plus, ArrowRight, X } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { AdminGuard } from "@/components/auth/AdminGuard";
import { projectsApi, type Project } from "@/services/api/projects";

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

/* ── Status styles ────────────────────────────────────────── */

const STATUS_STYLES: Record<string, string> = {
  active: "bg-emerald-50 text-emerald-700 border-emerald-200",
  completed: "bg-blue-50 text-blue-700 border-blue-200",
  on_hold: "bg-amber-50 text-amber-700 border-amber-200",
  archived:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
};

function StatusBadge({ status }: { status: string }) {
  const label = (status || "active").replace(/_/g, " ");
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[status] || STATUS_STYLES.active}`}
    >
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
}

/* ── Skeleton ─────────────────────────────────────────────── */

function CardsSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-5"
        >
          <div className="h-5 w-40 bg-[var(--color-gray-200)] rounded mb-3" />
          <div className="h-3 w-24 bg-[var(--color-gray-200)] rounded mb-2" />
          <div className="h-3 w-32 bg-[var(--color-gray-200)] rounded" />
        </div>
      ))}
    </div>
  );
}

/* ── Create Project Modal ─────────────────────────────────── */

function CreateProjectModal({
  isOpen,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [clientName, setClientName] = useState("");
  const [budget, setBudget] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !code.trim()) return;
    setIsSubmitting(true);
    try {
      await projectsApi.createProject({
        name: name.trim(),
        code: code.trim(),
        client_name: clientName.trim(),
        budget: budget ? Number(budget) : 0,
        start_date: startDate,
        end_date: endDate,
      });
      toast.success("Project created");
      setName("");
      setCode("");
      setClientName("");
      setBudget("");
      setStartDate("");
      setEndDate("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to create project";
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
            <FolderKanban className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              New Project
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
          <div className="grid grid-cols-2 gap-3">
            <AppInput
              label="Project Name"
              value={name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setName(e.target.value)
              }
              required
            />
            <AppInput
              label="Code"
              value={code}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setCode(e.target.value)
              }
              placeholder="e.g. PRJ-001"
              required
            />
          </div>
          <AppInput
            label="Client"
            value={clientName}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setClientName(e.target.value)
            }
            placeholder="Client or department name"
          />
          <AppInput
            label="Budget"
            value={budget}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setBudget(e.target.value)
            }
            placeholder="0.00"
          />
          <div className="grid grid-cols-2 gap-3">
            <AppInput
              label="Start Date"
              variant="date"
              value={startDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setStartDate(e.target.value)
              }
            />
            <AppInput
              label="End Date"
              variant="date"
              value={endDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setEndDate(e.target.value)
              }
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
              Create Project
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function ProjectsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin =
    user?.role === "owner" ||
    user?.role === "hr_manager" ||
    user?.role === "consultant";

  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [search, setSearch] = useState("");

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await projectsApi.listProjects();
      // Normalize backend fields to frontend type (API returns budget_amount, is_archived)
      const normalized = (data.projects ?? []).map((p: any) => ({
        ...p,
        status: p.status || (p.is_archived ? "archived" : "active"),
        code: p.code || "",
        budget: p.budget ?? p.budget_amount ?? 0,
        actual_cost: p.actual_cost ?? 0,
        client_name: p.client_name || "",
      }));
      setProjects(normalized);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load projects.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filtered = projects.filter(
    (p) =>
      (p.name ?? "").toLowerCase().includes(search.toLowerCase()) ||
      (p.code ?? "").toLowerCase().includes(search.toLowerCase()),
  );

  if (error && !isLoading) {
    return (
      <AdminGuard>
        <div className="max-w-4xl mx-auto space-y-6 pb-8">
          <div className="flex items-center gap-3">
            <FolderKanban
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Projects
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
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <FolderKanban
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Projects
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Track project timelines, budgets, and team assignments
              </p>
            </div>
          </div>
          {isAdmin && (
            <AppButton
              variant="primary"
              size="sm"
              onClick={() => setShowModal(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              New Project
            </AppButton>
          )}
        </div>

        {/* Search */}
        <AppInput
          value={search}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            setSearch(e.target.value)
          }
          placeholder="Search projects by name or code..."
        />

        {/* Project cards */}
        {isLoading ? (
          <CardsSkeleton />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<FolderKanban className="h-12 w-12" aria-hidden="true" />}
            message={search ? "No matching projects" : "No projects yet"}
            description={
              search
                ? "Try a different search term."
                : "Create your first project to get started."
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map((project) => (
              <AppCard key={project.id} variant="standard">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-semibold text-[var(--color-gray-900)] truncate">
                        {project.name}
                      </h3>
                      <StatusBadge status={project.status} />
                    </div>
                    <p className="text-xs text-[var(--color-gray-500)]">
                      {project.code}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
                  {project.client_name && (
                    <div>
                      <p className="text-[var(--color-gray-500)]">Client</p>
                      <p className="font-medium text-[var(--color-gray-700)]">
                        {project.client_name}
                      </p>
                    </div>
                  )}
                  {(project.budget ?? 0) > 0 && (
                    <div>
                      <p className="text-[var(--color-gray-500)]">Budget</p>
                      <p className="font-medium text-[var(--color-gray-700)]">
                        {formatCurrency(project.budget)}
                      </p>
                    </div>
                  )}
                  {project.start_date && (
                    <div>
                      <p className="text-[var(--color-gray-500)]">Start</p>
                      <p className="font-medium text-[var(--color-gray-700)]">
                        {formatDate(project.start_date)}
                      </p>
                    </div>
                  )}
                  {project.assignment_count !== undefined && (
                    <div>
                      <p className="text-[var(--color-gray-500)]">Team</p>
                      <p className="font-medium text-[var(--color-gray-700)]">
                        {project.assignment_count} members
                      </p>
                    </div>
                  )}
                </div>

                <AppButton
                  variant="outlined"
                  size="sm"
                  onClick={() => router.push(`/projects/${project.id}`)}
                  className="w-full"
                >
                  View Details
                  <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </AppButton>
              </AppCard>
            ))}
          </div>
        )}

        <CreateProjectModal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          onSuccess={fetchData}
        />
      </div>
    </AdminGuard>
  );
}
