"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  AppCard,
  AppButton,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Star,
  Archive,
  Upload,
  Download,
  Layers,
  ListChecks,
  Clock,
  CheckCircle,
  FileText,
  ClipboardList,
  FileSpreadsheet,
  AlertTriangle,
} from "lucide-react";
import {
  onboardingApi,
  type OnboardingTemplate,
  type OnboardingModule,
  type OnboardingStep,
  type ImportResult,
} from "@/services/api/onboarding";

/* ── Constants ───────────────────────────────────────────── */

const PHASE_STYLES: Record<string, string> = {
  orientation: "bg-blue-50 text-blue-700 border-blue-200",
  compliance: "bg-amber-50 text-amber-700 border-amber-200",
  benefits: "bg-emerald-50 text-emerald-700 border-emerald-200",
  probation: "bg-purple-50 text-purple-700 border-purple-200",
  custom:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
};

const STEP_TYPE_ICONS: Record<string, typeof FileText> = {
  content: FileText,
  checklist: ClipboardList,
  document_upload: Upload,
  policy_acknowledgment: CheckCircle,
  form: FileSpreadsheet,
  approval: CheckCircle,
};

/* ── Phase badge ─────────────────────────────────────────── */

function PhaseBadge({ phase }: { phase: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${PHASE_STYLES[phase] || PHASE_STYLES.custom}`}
    >
      {phase.charAt(0).toUpperCase() + phase.slice(1)}
    </span>
  );
}

/* ── Step type badge ─────────────────────────────────────── */

function StepTypeBadge({ type }: { type: string }) {
  const Icon = STEP_TYPE_ICONS[type] || FileText;
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] text-[var(--color-gray-500)] bg-[var(--color-gray-50)] border border-[var(--color-gray-100)]">
      <Icon className="h-3 w-3" />
      {type.replace(/_/g, " ")}
    </span>
  );
}

/* ── Module + steps for detail view ──────────────────────── */

interface ModuleWithSteps {
  module: OnboardingModule;
  steps: OnboardingStep[];
}

/* ── Template Detail View (read-only) ───────────────────── */

function TemplateDetailView({
  template,
  onClose,
}: {
  template: OnboardingTemplate;
  onClose: () => void;
}) {
  const [modules, setModules] = useState<ModuleWithSteps[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedModules, setExpandedModules] = useState<Set<number>>(
    new Set(),
  );

  const fetchTemplate = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await onboardingApi.getTemplate(template.id);
      const mods = (data.modules || []).map((m) => ({
        module: m.module,
        steps: m.steps || [],
      }));
      setModules(mods);
      // Auto-expand all modules on load
      setExpandedModules(new Set(mods.map((m) => m.module.id)));
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load template details";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  }, [template.id]);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  function toggleModule(moduleId: number) {
    setExpandedModules((prev) => {
      const next = new Set(prev);
      if (next.has(moduleId)) {
        next.delete(moduleId);
      } else {
        next.add(moduleId);
      }
      return next;
    });
  }

  const totalSteps = modules.reduce((sum, m) => sum + m.steps.length, 0);
  const totalDuration = modules.reduce(
    (sum, m) => sum + (m.module.estimated_duration_minutes || 0),
    0,
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
            title="Back to templates"
          >
            <ChevronRight className="h-5 w-5 text-[var(--color-gray-500)] rotate-180" />
          </button>
          <div>
            <h3 className="text-lg font-semibold text-[var(--color-gray-900)]">
              {template.name}
            </h3>
            {template.description && (
              <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                {template.description}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-[var(--color-gray-500)]">
          <span className="flex items-center gap-1">
            <Layers className="h-3.5 w-3.5" />
            {modules.length} module{modules.length !== 1 ? "s" : ""}
          </span>
          <span className="flex items-center gap-1">
            <ListChecks className="h-3.5 w-3.5" />
            {totalSteps} step{totalSteps !== 1 ? "s" : ""}
          </span>
          {totalDuration > 0 && (
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {totalDuration} min
            </span>
          )}
        </div>
      </div>

      {/* Modules */}
      {isLoading ? (
        <div className="py-8 text-center">
          <span className="inline-block h-5 w-5 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : modules.length === 0 ? (
        <div className="py-8 text-center border-2 border-dashed border-[var(--color-gray-200)] rounded-[12px]">
          <Layers className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2" />
          <p className="text-sm text-[var(--color-gray-500)]">
            This template has no modules. Upload a new version to add content.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {modules.map((m) => {
            const isExpanded = expandedModules.has(m.module.id);
            return (
              <div
                key={m.module.id}
                className="border border-[var(--color-gray-200)] rounded-[12px] overflow-hidden"
              >
                {/* Module header */}
                <button
                  type="button"
                  onClick={() => toggleModule(m.module.id)}
                  className="w-full flex items-center gap-2 px-4 py-3 bg-[var(--color-gray-50)] hover:bg-[var(--color-gray-100)] transition-colors text-left"
                >
                  <div className="flex-shrink-0">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-[var(--color-gray-500)]" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-[var(--color-gray-500)]" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                        {m.module.name || "Untitled Module"}
                      </span>
                      <PhaseBadge phase={m.module.phase || "custom"} />
                      {m.module.is_mandatory && (
                        <span className="text-[10px] font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">
                          Required
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[var(--color-gray-500)]">
                      {m.steps.length} step{m.steps.length !== 1 ? "s" : ""}
                      {m.module.estimated_duration_minutes
                        ? ` / ${m.module.estimated_duration_minutes} min`
                        : ""}
                    </p>
                  </div>
                </button>

                {/* Steps (read-only) */}
                {isExpanded && (
                  <div className="px-4 py-3 border-t border-[var(--color-gray-200)] space-y-1.5">
                    {m.steps.length === 0 ? (
                      <p className="text-xs text-[var(--color-gray-500)] text-center py-2">
                        No steps in this module.
                      </p>
                    ) : (
                      m.steps.map((step, idx) => (
                        <div
                          key={step.id}
                          className="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-[var(--color-gray-50)]"
                        >
                          <span className="text-[10px] font-mono text-[var(--color-gray-400)] w-5 text-right flex-shrink-0">
                            {idx + 1}.
                          </span>
                          <span className="text-sm text-[var(--color-gray-800)] flex-1">
                            {step.title}
                          </span>
                          <StepTypeBadge type={step.step_type || "content"} />
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <p className="text-xs text-[var(--color-gray-400)] text-center">
        To edit this template, update the Excel file and re-upload a new
        version.
      </p>
    </div>
  );
}

/* ── Import Summary ─────────────────────────────────────── */

function ImportSummary({
  result,
  onDismiss,
}: {
  result: ImportResult;
  onDismiss: () => void;
}) {
  const hasErrors = result.errors.length > 0;
  const hasWarnings = result.warnings.length > 0;

  return (
    <div
      className={`rounded-[12px] border p-4 space-y-3 ${
        hasErrors
          ? "border-red-200 bg-red-50"
          : hasWarnings
            ? "border-amber-200 bg-amber-50"
            : "border-emerald-200 bg-emerald-50"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          {hasErrors ? (
            <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0" />
          ) : (
            <CheckCircle className="h-5 w-5 text-emerald-600 flex-shrink-0" />
          )}
          <div>
            <p
              className={`text-sm font-medium ${hasErrors ? "text-red-800" : "text-emerald-800"}`}
            >
              {hasErrors ? "Import completed with errors" : "Template imported"}
            </p>
            <p
              className={`text-xs mt-0.5 ${hasErrors ? "text-red-600" : "text-emerald-600"}`}
            >
              {result.modules_created} module
              {result.modules_created !== 1 ? "s" : ""}, {result.steps_created}{" "}
              step
              {result.steps_created !== 1 ? "s" : ""} created
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="text-xs text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] transition-colors"
        >
          Dismiss
        </button>
      </div>

      {hasWarnings && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-amber-700">Warnings:</p>
          <ul className="list-disc list-inside text-xs text-amber-600 space-y-0.5">
            {result.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {hasErrors && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-red-700">Errors:</p>
          <ul className="list-disc list-inside text-xs text-red-600 space-y-0.5">
            {result.errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   TemplateBuilder — main export (upload + list view)
   ═══════════════════════════════════════════════════════════ */

export function TemplateBuilder({
  refreshKey,
}: {
  /** Increment to trigger a template list re-fetch from the parent. */
  refreshKey?: number;
}) {
  const [templates, setTemplates] = useState<OnboardingTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingTemplate, setViewingTemplate] =
    useState<OnboardingTemplate | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  /* Upload state */
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchTemplates = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await onboardingApi.listTemplates();
      setTemplates(data.templates ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load templates.";
      setError(message);
      setTemplates([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  /* Re-fetch when parent signals via refreshKey change */
  useEffect(() => {
    if (refreshKey !== undefined && refreshKey > 0) {
      fetchTemplates();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  /* ── Upload handler ───────────────────────────────────── */

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    const file = files[0];

    if (!file.name.endsWith(".xlsx")) {
      toast.error("Please upload an .xlsx file (Excel format).");
      return;
    }

    setIsUploading(true);
    setImportResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const result = await onboardingApi.importTemplate(formData);
      setImportResult(result);

      if (result.errors.length > 0) {
        toast.error("Import completed with errors. See details below.");
      } else {
        toast.success(
          `Template imported: ${result.modules_created} modules, ${result.steps_created} steps.`,
        );
      }
      fetchTemplates();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to import template";
      toast.error(message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave() {
    setIsDragOver(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
    handleUpload(e.dataTransfer.files);
  }

  /* ── Template actions ─────────────────────────────────── */

  async function handleDuplicate(t: OnboardingTemplate) {
    setActionLoading(`dup-${t.id}`);
    try {
      const copy = await onboardingApi.duplicateTemplate(t.id);
      setTemplates((prev) => [...prev, copy]);
      toast.success(`Template duplicated as "${copy.name}".`);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to duplicate template";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleSetDefault(t: OnboardingTemplate) {
    setActionLoading(`default-${t.id}`);
    try {
      await onboardingApi.updateTemplate(t.id, { is_default: true });
      setTemplates((prev) =>
        prev.map((tpl) => ({
          ...tpl,
          is_default: tpl.id === t.id,
        })),
      );
      toast.success(`"${t.name}" is now the default template.`);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to update default";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleArchive(t: OnboardingTemplate) {
    setActionLoading(`archive-${t.id}`);
    try {
      await onboardingApi.updateTemplate(t.id, { is_active: false });
      setTemplates((prev) => prev.filter((tpl) => tpl.id !== t.id));
      toast.success(`"${t.name}" archived.`);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to archive template";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  /* ── Detail view ──────────────────────────────────────── */

  if (viewingTemplate) {
    return (
      <TemplateDetailView
        template={viewingTemplate}
        onClose={() => {
          setViewingTemplate(null);
          fetchTemplates();
        }}
      />
    );
  }

  /* ── Main view ────────────────────────────────────────── */

  return (
    <div className="space-y-4">
      {/* Section header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-800)]">
            Onboarding Templates
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Upload and manage onboarding templates from your LIA Excel file
          </p>
        </div>
        <a
          href="/templates/LIA_Onboarding_Template.xlsx"
          download="LIA_Onboarding_Template.xlsx"
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-[8px] text-sm font-medium text-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-colors border border-[var(--color-primary)]/20"
        >
          <Download className="h-4 w-4" />
          Download Template
        </a>
      </div>

      {/* Upload zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-[12px] p-8 text-center transition-colors cursor-pointer ${
          isDragOver
            ? "border-[var(--color-primary)] bg-[var(--color-primary-bg)]"
            : "border-[var(--color-gray-200)] hover:border-[var(--color-gray-300)] hover:bg-[var(--color-gray-50)]"
        }`}
      >
        {isUploading ? (
          <div className="flex flex-col items-center gap-2">
            <span className="inline-block h-6 w-6 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-[var(--color-gray-600)]">
              Importing template...
            </p>
          </div>
        ) : (
          <>
            <Upload className="h-8 w-8 text-[var(--color-gray-400)] mx-auto mb-2" />
            <p className="text-sm font-medium text-[var(--color-gray-700)]">
              Upload Onboarding Template
            </p>
            <p className="text-xs text-[var(--color-gray-500)] mt-1">
              Upload your completed LIA Onboarding Template (.xlsx)
            </p>
            <p className="text-xs text-[var(--color-gray-400)] mt-0.5">
              Drop file here, or click to browse
            </p>
          </>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(e) => handleUpload(e.target.files)}
        />
      </div>

      {/* Import result summary */}
      {importResult && (
        <ImportSummary
          result={importResult}
          onDismiss={() => setImportResult(null)}
        />
      )}

      {/* Template list */}
      {isLoading ? (
        <AppCard variant="standard">
          <div className="animate-pulse space-y-3">
            {Array.from({ length: 3 }, (_, i) => (
              <div key={i} className="flex items-center gap-4 py-3">
                <div className="h-4 w-40 bg-[var(--color-gray-200)] rounded" />
                <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
                <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded" />
                <div className="h-4 w-12 bg-[var(--color-gray-200)] rounded ml-auto" />
              </div>
            ))}
          </div>
        </AppCard>
      ) : error ? (
        <AppCard variant="standard">
          <div className="py-6 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={fetchTemplates}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      ) : templates.length === 0 ? (
        <div className="py-6 text-center border-2 border-dashed border-[var(--color-gray-200)] rounded-[12px]">
          <ListChecks className="h-10 w-10 text-[var(--color-gray-300)] mx-auto mb-3" />
          <p className="text-sm text-[var(--color-gray-600)] mb-1">
            No onboarding templates yet
          </p>
          <p className="text-xs text-[var(--color-gray-500)]">
            Download the template above, fill it out, then upload it here.
          </p>
        </div>
      ) : (
        <AppCard variant="standard">
          <div className="overflow-x-auto -mx-5 -my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)]">
                  <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                    Template Name
                  </th>
                  <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Version
                  </th>
                  <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Status
                  </th>
                  <th className="text-right py-3 px-5 font-medium text-[var(--color-gray-500)]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {templates.map((t) => (
                  <tr
                    key={t.id}
                    className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                  >
                    <td className="py-3 px-5">
                      <button
                        type="button"
                        onClick={() => setViewingTemplate(t)}
                        className="text-left group"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-[var(--color-gray-900)] group-hover:text-[var(--color-primary)] transition-colors">
                            {t.name}
                          </span>
                          {t.is_default && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-[var(--color-primary-bg)] text-[var(--color-primary)] border border-[var(--color-primary)]/20">
                              <Star className="h-3 w-3" />
                              Default
                            </span>
                          )}
                        </div>
                        {t.description && (
                          <p className="text-xs text-[var(--color-gray-500)] mt-0.5 truncate max-w-xs">
                            {t.description}
                          </p>
                        )}
                      </button>
                    </td>
                    <td className="py-3 px-3 text-center text-[var(--color-gray-600)]">
                      v{t.version}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                          t.is_active
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]"
                        }`}
                      >
                        {t.is_active ? "Active" : "Archived"}
                      </span>
                    </td>
                    <td className="py-3 px-5">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => setViewingTemplate(t)}
                          className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"
                          title="View details"
                        >
                          <Layers className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDuplicate(t)}
                          disabled={actionLoading === `dup-${t.id}`}
                          className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] disabled:opacity-50"
                          title="Duplicate template"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                        {!t.is_default && (
                          <button
                            type="button"
                            onClick={() => handleSetDefault(t)}
                            disabled={actionLoading === `default-${t.id}`}
                            className="p-1.5 rounded-lg hover:bg-amber-50 transition-colors text-[var(--color-gray-500)] hover:text-amber-600 disabled:opacity-50"
                            title="Set as default"
                          >
                            <Star className="h-4 w-4" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleArchive(t)}
                          disabled={actionLoading === `archive-${t.id}`}
                          className="p-1.5 rounded-lg hover:bg-red-50 transition-colors text-[var(--color-gray-500)] hover:text-red-600 disabled:opacity-50"
                          title="Archive template"
                        >
                          <Archive className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AppCard>
      )}
    </div>
  );
}
