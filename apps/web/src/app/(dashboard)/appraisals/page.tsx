"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  Award,
  Plus,
  Play,
  Send,
  FileCheck,
  X,
  ChevronDown,
  ChevronUp,
  Save,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  appraisalsApi,
  type AppraisalTemplate,
  type AppraisalPeriod,
  type Appraisal,
} from "@/services/api/appraisals";

/* ── Helpers ──────────────────────────────────────────────── */

function formatDate(d: string): string {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("en-SG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/* ── Status badges ────────────────────────────────────────── */

const STATUS_STYLES: Record<string, string> = {
  draft:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
  active: "bg-emerald-50 text-emerald-700 border-emerald-200",
  in_progress: "bg-blue-50 text-blue-700 border-blue-200",
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  submitted: "bg-blue-50 text-blue-700 border-blue-200",
  signed_off: "bg-emerald-50 text-emerald-700 border-emerald-200",
  pending: "bg-amber-50 text-amber-700 border-amber-200",
};

function StatusBadge({ status }: { status: string }) {
  const label = status.replace(/_/g, " ");
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[status] || STATUS_STYLES.draft}`}
    >
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
}

/* ── Skeletons ────────────────────────────────────────────── */

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

/* ── Tab button ───────────────────────────────────────────── */

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

/* ── Create Template Modal ────────────────────────────────── */

function CreateTemplateModal({
  isOpen,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [name, setName] = useState("");
  const [enableWeightage, setEnableWeightage] = useState(false);
  const [requireSignoff, setRequireSignoff] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    try {
      await appraisalsApi.createTemplate({
        name: name.trim(),
        enable_weightage: enableWeightage,
        require_employee_signoff: requireSignoff,
        sections: "[]",
      });
      toast.success("Appraisal template created");
      setName("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to create template";
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
            <Award className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              New Template
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
            label="Template Name"
            value={name}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setName(e.target.value)
            }
            placeholder="e.g. Annual Performance Review"
            required
          />
          <label className="flex items-center gap-2 text-sm text-[var(--color-gray-700)] cursor-pointer">
            <input
              type="checkbox"
              checked={enableWeightage}
              onChange={(e) => setEnableWeightage(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
            />
            Enable section weightage
          </label>
          <label className="flex items-center gap-2 text-sm text-[var(--color-gray-700)] cursor-pointer">
            <input
              type="checkbox"
              checked={requireSignoff}
              onChange={(e) => setRequireSignoff(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
            />
            Require employee sign-off
          </label>
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
              Create Template
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Create Period Modal ──────────────────────────────────── */

function CreatePeriodModal({
  isOpen,
  onClose,
  onSuccess,
  templates,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  templates: AppraisalTemplate[];
}) {
  const [name, setName] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !templateId || !startDate || !endDate) return;
    setIsSubmitting(true);
    try {
      await appraisalsApi.createPeriod({
        name: name.trim(),
        template_id: Number(templateId),
        start_date: startDate,
        end_date: endDate,
      });
      toast.success("Review period created");
      setName("");
      setTemplateId("");
      setStartDate("");
      setEndDate("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to create period";
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
            New Review Period
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
          <AppInput
            label="Period Name"
            value={name}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setName(e.target.value)
            }
            placeholder="e.g. 2026 Annual Review"
            required
          />
          <div>
            <label
              htmlFor="template-select"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Template
            </label>
            <select
              id="template-select"
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] focus:border-[var(--color-surface-input-focus)]"
              required
            >
              <option value="">Select template</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <AppInput
              label="Start Date"
              variant="date"
              value={startDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setStartDate(e.target.value)
              }
              required
            />
            <AppInput
              label="End Date"
              variant="date"
              value={endDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setEndDate(e.target.value)
              }
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
              type="submit"
              variant="primary"
              size="sm"
              loading={isSubmitting}
              className="flex-1"
            >
              Create Period
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

type Tab = "templates" | "periods" | "my-appraisals";

export default function AppraisalsPage() {
  const { user } = useAuth();
  const isAdmin =
    user?.role === "owner" ||
    user?.role === "hr_manager" ||
    user?.role === "consultant";

  const [tab, setTab] = useState<Tab>(isAdmin ? "templates" : "my-appraisals");
  const [templates, setTemplates] = useState<AppraisalTemplate[]>([]);
  const [periods, setPeriods] = useState<AppraisalPeriod[]>([]);
  const [appraisals, setAppraisals] = useState<Appraisal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [showPeriodModal, setShowPeriodModal] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedTemplateId, setExpandedTemplateId] = useState<number | null>(
    null,
  );
  const [editScores, setEditScores] = useState<Record<number, string>>({});
  const [editReviewerComments, setEditReviewerComments] = useState<
    Record<number, string>
  >({});
  const [editEmployeeComments, setEditEmployeeComments] = useState<
    Record<number, string>
  >({});
  const [isSaving, setIsSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [templatesRes, periodsRes, appraisalsRes] = await Promise.all([
        appraisalsApi.listTemplates(),
        appraisalsApi.listPeriods(),
        appraisalsApi.listAppraisals(),
      ]);
      setTemplates(templatesRes.templates ?? []);
      setPeriods(periodsRes.periods ?? []);
      setAppraisals(appraisalsRes.appraisals ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load appraisal data.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleLaunch(periodId: number) {
    try {
      await appraisalsApi.launchPeriod(periodId);
      toast.success(
        "Review period launched -- appraisals assigned to employees",
      );
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to launch period";
      toast.error(message);
    }
  }

  async function handleSubmit(appraisalId: number) {
    try {
      await appraisalsApi.submitAppraisal(appraisalId);
      toast.success("Appraisal submitted");
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to submit appraisal";
      toast.error(message);
    }
  }

  async function handleSignOff(appraisalId: number) {
    try {
      await appraisalsApi.signOffAppraisal(appraisalId);
      toast.success("Appraisal signed off");
      fetchData();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to sign off";
      toast.error(message);
    }
  }

  function toggleExpand(appraisal: Appraisal) {
    if (expandedId === appraisal.id) {
      setExpandedId(null);
    } else {
      setExpandedId(appraisal.id);
      // Initialize edit fields from current data
      setEditScores((prev) => ({
        ...prev,
        [appraisal.id]: String(appraisal.overall_score || ""),
      }));
      setEditReviewerComments((prev) => ({
        ...prev,
        [appraisal.id]: appraisal.reviewer_comments || "",
      }));
      setEditEmployeeComments((prev) => ({
        ...prev,
        [appraisal.id]: appraisal.employee_comments || "",
      }));
    }
  }

  async function handleSaveAppraisal(appraisalId: number) {
    setIsSaving(true);
    try {
      const score = Number(editScores[appraisalId]) || 0;
      await appraisalsApi.updateAppraisal(appraisalId, {
        overall_score: Math.min(5, Math.max(0, score)),
        reviewer_comments: editReviewerComments[appraisalId] || "",
        employee_comments: editEmployeeComments[appraisalId] || "",
      });
      toast.success("Appraisal saved");
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save appraisal";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  if (error && !isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <div className="flex items-center gap-3">
          <Award
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Appraisals
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
          <Award
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Appraisals
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              {isAdmin
                ? "Manage performance review templates and cycles"
                : "View and complete your performance reviews"}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-lg bg-[var(--color-gray-100)] w-fit">
        {isAdmin && (
          <>
            <TabButton
              active={tab === "templates"}
              label="Templates"
              onClick={() => setTab("templates")}
            />
            <TabButton
              active={tab === "periods"}
              label="Periods"
              onClick={() => setTab("periods")}
            />
          </>
        )}
        <TabButton
          active={tab === "my-appraisals"}
          label="My Appraisals"
          onClick={() => setTab("my-appraisals")}
        />
      </div>

      {/* Templates Tab */}
      {tab === "templates" && isAdmin && (
        <>
          <div className="flex justify-end">
            <AppButton
              variant="primary"
              size="sm"
              onClick={() => setShowTemplateModal(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              New Template
            </AppButton>
          </div>
          {isLoading ? (
            <AppCard variant="standard">
              <div className="-mx-5 -my-4">
                <TableSkeleton />
              </div>
            </AppCard>
          ) : templates.length === 0 ? (
            <EmptyState
              icon={<Award className="h-12 w-12" aria-hidden="true" />}
              message="No templates yet"
              description="Create your first appraisal template to get started."
            />
          ) : (
            <AppCard variant="standard">
              <div className="overflow-x-auto -mx-5 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--color-gray-200)]">
                      <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Name
                      </th>
                      <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Weightage
                      </th>
                      <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Sign-off
                      </th>
                      <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {templates.map((t) => (
                      <React.Fragment key={t.id}>
                        <tr
                          className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors cursor-pointer"
                          onClick={() =>
                            setExpandedTemplateId(
                              expandedTemplateId === t.id ? null : t.id,
                            )
                          }
                        >
                          <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                            <span className="flex items-center gap-2">
                              {expandedTemplateId === t.id ? (
                                <ChevronUp className="h-3.5 w-3.5 text-[var(--color-gray-400)]" />
                              ) : (
                                <ChevronDown className="h-3.5 w-3.5 text-[var(--color-gray-400)]" />
                              )}
                              {t.name}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-center text-[var(--color-gray-600)]">
                            {t.enable_weightage ? "Yes" : "No"}
                          </td>
                          <td className="py-3 px-3 text-center text-[var(--color-gray-600)]">
                            {t.require_employee_signoff
                              ? "Required"
                              : "Optional"}
                          </td>
                          <td className="py-3 px-5 text-center">
                            <StatusBadge
                              status={t.is_archived ? "draft" : "active"}
                            />
                          </td>
                        </tr>
                        {expandedTemplateId === t.id && (
                          <tr>
                            <td
                              colSpan={4}
                              className="px-5 py-4 bg-[var(--color-gray-50)]"
                            >
                              <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                  <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
                                    Template Details
                                  </h4>
                                  <span className="text-xs text-[var(--color-gray-500)]">
                                    Created {formatDate(t.created_at || "")}
                                  </span>
                                </div>
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                  <div>
                                    <p className="text-xs text-[var(--color-gray-500)] mb-1">
                                      Weightage
                                    </p>
                                    <p className="text-[var(--color-gray-800)]">
                                      {t.enable_weightage
                                        ? "Enabled — criteria have percentage weights"
                                        : "Disabled — equal weight for all criteria"}
                                    </p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-[var(--color-gray-500)] mb-1">
                                      Employee Sign-off
                                    </p>
                                    <p className="text-[var(--color-gray-800)]">
                                      {t.require_employee_signoff
                                        ? "Required — employee must acknowledge the review"
                                        : "Optional — review can be completed without employee sign-off"}
                                    </p>
                                  </div>
                                </div>
                                <div>
                                  <p className="text-xs text-[var(--color-gray-500)] mb-2">
                                    Suggested Criteria
                                  </p>
                                  <div className="flex flex-wrap gap-2">
                                    {[
                                      "Job Knowledge",
                                      "Quality of Work",
                                      "Productivity",
                                      "Communication",
                                      "Teamwork",
                                      "Initiative",
                                      "Reliability",
                                    ].map((c) => (
                                      <span
                                        key={c}
                                        className="px-2.5 py-1 rounded-full text-xs bg-[var(--color-primary-bg)] text-[var(--color-primary)] border border-[var(--color-primary)]/20"
                                      >
                                        {c}
                                      </span>
                                    ))}
                                  </div>
                                  <p className="text-xs text-[var(--color-gray-400)] mt-2">
                                    Criteria are assigned per appraisal period.
                                    These are commonly used suggestions.
                                  </p>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </AppCard>
          )}
        </>
      )}

      {/* Periods Tab */}
      {tab === "periods" && isAdmin && (
        <>
          <div className="flex justify-end">
            <AppButton
              variant="primary"
              size="sm"
              onClick={() => setShowPeriodModal(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              New Period
            </AppButton>
          </div>
          {isLoading ? (
            <AppCard variant="standard">
              <div className="-mx-5 -my-4">
                <TableSkeleton />
              </div>
            </AppCard>
          ) : periods.length === 0 ? (
            <EmptyState
              icon={<Award className="h-12 w-12" aria-hidden="true" />}
              message="No review periods"
              description="Create a review period and link it to a template."
            />
          ) : (
            <AppCard variant="standard">
              <div className="overflow-x-auto -mx-5 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--color-gray-200)]">
                      <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                        Period
                      </th>
                      <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                        Dates
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
                    {periods.map((p) => (
                      <tr
                        key={p.id}
                        className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                      >
                        <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                          {p.name}
                        </td>
                        <td className="py-3 px-3 text-[var(--color-gray-600)]">
                          {formatDate(p.start_date)} - {formatDate(p.end_date)}
                        </td>
                        <td className="py-3 px-3 text-center">
                          <StatusBadge status={p.status} />
                        </td>
                        <td className="py-3 px-5 text-center">
                          {p.status === "draft" && (
                            <AppButton
                              variant="primary"
                              size="sm"
                              onClick={() => handleLaunch(p.id)}
                            >
                              <Play className="h-3.5 w-3.5 mr-1" />
                              Launch
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

      {/* My Appraisals Tab */}
      {tab === "my-appraisals" && (
        <>
          {isLoading ? (
            <AppCard variant="standard">
              <div className="-mx-5 -my-4">
                <TableSkeleton />
              </div>
            </AppCard>
          ) : appraisals.length === 0 ? (
            <EmptyState
              icon={<Award className="h-12 w-12" aria-hidden="true" />}
              message="No appraisals assigned"
              description="You will see your performance reviews here once a review cycle is launched."
            />
          ) : (
            <div className="space-y-3">
              {appraisals.map((a) => {
                const isExpanded = expandedId === a.id;
                const isEditable =
                  a.status === "draft" ||
                  a.status === "pending" ||
                  a.status === "in_progress";
                return (
                  <AppCard key={a.id} variant="standard">
                    <button
                      type="button"
                      onClick={() => toggleExpand(a)}
                      className="w-full text-left"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="text-sm font-medium text-[var(--color-gray-900)]">
                              {a.employee_name || `Employee #${a.employee_id}`}
                            </p>
                            <StatusBadge status={a.status} />
                          </div>
                          {a.overall_score > 0 && (
                            <p className="text-xs text-[var(--color-gray-500)]">
                              Score: {a.overall_score.toFixed(1)}/5
                            </p>
                          )}
                        </div>
                        <div className="shrink-0">
                          {isExpanded ? (
                            <ChevronUp className="h-4 w-4 text-[var(--color-gray-400)]" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-[var(--color-gray-400)]" />
                          )}
                        </div>
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="mt-4 pt-4 border-t border-[var(--color-gray-100)] space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-1">
                            Overall Score (1-5)
                          </label>
                          <input
                            type="number"
                            min={1}
                            max={5}
                            step={0.5}
                            value={editScores[a.id] ?? ""}
                            onChange={(e) =>
                              setEditScores((prev) => ({
                                ...prev,
                                [a.id]: e.target.value,
                              }))
                            }
                            disabled={!isEditable}
                            className="w-24 rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] disabled:opacity-50"
                          />
                        </div>
                        {isAdmin && (
                          <div>
                            <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-1">
                              Reviewer Comments
                            </label>
                            <textarea
                              value={editReviewerComments[a.id] ?? ""}
                              onChange={(e) =>
                                setEditReviewerComments((prev) => ({
                                  ...prev,
                                  [a.id]: e.target.value,
                                }))
                              }
                              disabled={!isEditable}
                              rows={3}
                              className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] disabled:opacity-50"
                              placeholder="Enter reviewer feedback..."
                            />
                          </div>
                        )}
                        <div>
                          <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-1">
                            Employee Comments
                          </label>
                          <textarea
                            value={editEmployeeComments[a.id] ?? ""}
                            onChange={(e) =>
                              setEditEmployeeComments((prev) => ({
                                ...prev,
                                [a.id]: e.target.value,
                              }))
                            }
                            disabled={!isEditable}
                            rows={3}
                            className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] disabled:opacity-50"
                            placeholder="Enter your self-assessment..."
                          />
                        </div>
                        <div className="flex gap-2">
                          {isEditable && (
                            <AppButton
                              variant="outlined"
                              size="sm"
                              loading={isSaving}
                              onClick={() => handleSaveAppraisal(a.id)}
                            >
                              <Save className="h-3.5 w-3.5 mr-1" />
                              Save
                            </AppButton>
                          )}
                          {(a.status === "draft" ||
                            a.status === "pending" ||
                            a.status === "in_progress") && (
                            <AppButton
                              variant="primary"
                              size="sm"
                              onClick={() => handleSubmit(a.id)}
                            >
                              <Send className="h-3.5 w-3.5 mr-1" />
                              Submit
                            </AppButton>
                          )}
                          {a.status === "submitted" && (
                            <AppButton
                              variant="primary"
                              size="sm"
                              onClick={() => handleSignOff(a.id)}
                            >
                              <FileCheck className="h-3.5 w-3.5 mr-1" />
                              Sign Off
                            </AppButton>
                          )}
                        </div>
                      </div>
                    )}
                  </AppCard>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Modals */}
      <CreateTemplateModal
        isOpen={showTemplateModal}
        onClose={() => setShowTemplateModal(false)}
        onSuccess={fetchData}
      />
      <CreatePeriodModal
        isOpen={showPeriodModal}
        onClose={() => setShowPeriodModal(false)}
        onSuccess={fetchData}
        templates={templates}
      />
    </div>
  );
}
