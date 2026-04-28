"use client";

/**
 * /onboarding/templates/[id] — Template Builder.
 *
 * Editable view of an onboarding template:
 *   - Template metadata (name, description, default flag)
 *   - Modules list (add / edit / delete / reorder via sort_order input)
 *     - phase: orientation | compliance | benefits | probation | custom
 *     - is_role_specific toggle + role_filter (JSON array of designations)
 *   - Steps within each module (add / edit / delete / reorder)
 *     - step_type: content | checklist | document_upload |
 *       policy_acknowledgment | form | approval
 *     - body_content textarea
 *
 * Owner / hr_manager only.
 */

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Plus,
  Pencil,
  Trash2,
  Save,
  X,
  ChevronDown,
  ChevronRight,
  Layers,
  ListChecks,
  Star,
  Loader2,
  AlertTriangle,
  FileText,
  ClipboardList,
  Upload,
  CheckCircle,
  FileSpreadsheet,
} from "lucide-react";

import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  AppButton,
  AppCard,
  AppInput,
  toast,
} from "@/components/design-system";
import {
  onboardingApi,
  type OnboardingTemplateDetail,
  type OnboardingModule,
  type OnboardingModuleWithSteps,
  type OnboardingStep,
} from "@/services/api/onboarding";

/* ── Constants ────────────────────────────────────────────── */

const PHASES = [
  { value: "orientation", label: "Orientation" },
  { value: "compliance", label: "Compliance" },
  { value: "benefits", label: "Benefits" },
  { value: "probation", label: "Probation" },
  { value: "custom", label: "Custom" },
];

const STEP_TYPES = [
  { value: "content", label: "Content (read-only)" },
  { value: "checklist", label: "Checklist" },
  { value: "document_upload", label: "Document upload" },
  { value: "policy_acknowledgment", label: "Policy acknowledgment" },
  { value: "form", label: "Form" },
  { value: "approval", label: "Manager approval" },
];

const STEP_TYPE_ICONS: Record<string, typeof FileText> = {
  content: FileText,
  checklist: ClipboardList,
  document_upload: Upload,
  policy_acknowledgment: CheckCircle,
  form: FileSpreadsheet,
  approval: CheckCircle,
};

const PHASE_BADGE_STYLES: Record<string, string> = {
  orientation: "bg-blue-50 text-blue-700 border-blue-200",
  compliance: "bg-amber-50 text-amber-700 border-amber-200",
  benefits: "bg-emerald-50 text-emerald-700 border-emerald-200",
  probation: "bg-purple-50 text-purple-700 border-purple-200",
  custom:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
};

/* ── Page ────────────────────────────────────────────────── */

export default function TemplateBuilderPage() {
  const params = useParams<{ id: string }>();
  const templateId = parseInt(params?.id ?? "", 10);

  if (!templateId || Number.isNaN(templateId)) {
    return (
      <AdminGuard>
        <div className="max-w-3xl mx-auto py-8 px-4 text-center">
          <AlertTriangle className="h-10 w-10 text-amber-500 mx-auto mb-3" />
          <p className="text-sm text-[var(--color-gray-600)]">
            Invalid template ID.
          </p>
        </div>
      </AdminGuard>
    );
  }

  return (
    <AdminGuard>
      <Builder templateId={templateId} />
    </AdminGuard>
  );
}

/* ── Builder root ────────────────────────────────────────── */

function Builder({ templateId }: { templateId: number }) {
  const router = useRouter();
  const [template, setTemplate] = useState<OnboardingTemplateDetail | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingMeta, setEditingMeta] = useState(false);
  const [showAddModule, setShowAddModule] = useState(false);

  const fetchTemplate = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await onboardingApi.getTemplateAdmin(templateId);
      setTemplate(res.template);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load template.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [templateId]);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto py-8 px-4">
        <div className="animate-pulse space-y-4">
          <div className="h-7 w-64 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-80 bg-[var(--color-gray-200)] rounded" />
          <div className="h-32 bg-[var(--color-gray-100)] rounded-[12px]" />
          <div className="h-32 bg-[var(--color-gray-100)] rounded-[12px]" />
        </div>
      </div>
    );
  }

  if (error || !template) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4 text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500 mx-auto mb-3" />
        <p className="text-sm text-[var(--color-error)] mb-4">
          {error || "Template not found."}
        </p>
        <div className="flex gap-2 justify-center">
          <AppButton variant="outlined" size="sm" onClick={fetchTemplate}>
            Try again
          </AppButton>
          <AppButton
            variant="text"
            size="sm"
            onClick={() => router.push("/onboarding/admin")}
          >
            Back to templates
          </AppButton>
        </div>
      </div>
    );
  }

  const totalSteps = template.modules.reduce(
    (sum, m) => sum + (m.steps?.length ?? 0),
    0,
  );

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      {/* Header / breadcrumb */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <button
            type="button"
            onClick={() => router.push("/onboarding/admin")}
            className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors mt-1"
            title="Back to templates"
          >
            <ArrowLeft className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold text-[var(--color-gray-900)]">
                {template.name}
              </h1>
              {template.is_default && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--color-primary-bg)] text-[var(--color-primary)] border border-[var(--color-primary)]/20">
                  <Star className="h-3 w-3" />
                  Default
                </span>
              )}
              <span className="text-xs text-[var(--color-gray-500)]">
                v{template.version}
              </span>
            </div>
            {template.description && (
              <p className="mt-1 text-sm text-[var(--color-gray-500)] max-w-2xl">
                {template.description}
              </p>
            )}
            <div className="mt-2 flex items-center gap-3 text-xs text-[var(--color-gray-500)]">
              <span className="flex items-center gap-1">
                <Layers className="h-3.5 w-3.5" />
                {template.modules.length} module
                {template.modules.length !== 1 ? "s" : ""}
              </span>
              <span className="flex items-center gap-1">
                <ListChecks className="h-3.5 w-3.5" />
                {totalSteps} step{totalSteps !== 1 ? "s" : ""}
              </span>
            </div>
          </div>
        </div>
        <AppButton
          variant="outlined"
          size="sm"
          onClick={() => setEditingMeta(true)}
        >
          <Pencil className="h-4 w-4 mr-1" />
          Edit details
        </AppButton>
      </div>

      {/* Modules list */}
      <section className="space-y-3">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-base font-semibold text-[var(--color-gray-800)]">
            Modules
          </h2>
          <AppButton
            variant="primary"
            size="sm"
            onClick={() => setShowAddModule(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add module
          </AppButton>
        </div>

        {template.modules.length === 0 ? (
          <div className="border-2 border-dashed border-[var(--color-gray-200)] rounded-[12px] py-10 text-center">
            <Layers className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2" />
            <p className="text-sm text-[var(--color-gray-600)] mb-1">
              No modules yet
            </p>
            <p className="text-xs text-[var(--color-gray-500)]">
              Add your first module to start building this template.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {template.modules.map((mod) => (
              <ModuleCard key={mod.id} module={mod} onChanged={fetchTemplate} />
            ))}
          </div>
        )}
      </section>

      {/* Modals */}
      {editingMeta && (
        <EditTemplateModal
          template={template}
          onClose={() => setEditingMeta(false)}
          onSaved={() => {
            setEditingMeta(false);
            fetchTemplate();
          }}
        />
      )}
      {showAddModule && (
        <ModuleEditorModal
          mode="create"
          templateId={template.id}
          onClose={() => setShowAddModule(false)}
          onSaved={() => {
            setShowAddModule(false);
            fetchTemplate();
          }}
        />
      )}
    </div>
  );
}

/* ── Module card ─────────────────────────────────────────── */

function ModuleCard({
  module,
  onChanged,
}: {
  module: OnboardingModuleWithSteps;
  onChanged: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [showAddStep, setShowAddStep] = useState(false);
  const [editingStep, setEditingStep] = useState<OnboardingStep | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (
      !window.confirm(
        `Delete module "${module.name}"? This will also delete all ${module.steps?.length ?? 0} step(s) inside it.`,
      )
    ) {
      return;
    }
    setDeleting(true);
    try {
      await onboardingApi.deleteModuleAdmin(module.id);
      toast.success("Module deleted.");
      onChanged();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to delete module";
      toast.error(message);
    } finally {
      setDeleting(false);
    }
  }

  const phase = module.phase || "custom";

  return (
    <AppCard variant="standard">
      <div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setExpanded((x) => !x)}
            className="p-1 rounded hover:bg-[var(--color-gray-100)] transition-colors"
            aria-label={expanded ? "Collapse module" : "Expand module"}
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4 text-[var(--color-gray-500)]" />
            ) : (
              <ChevronRight className="h-4 w-4 text-[var(--color-gray-500)]" />
            )}
          </button>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-[var(--color-gray-900)]">
                {module.name || "Untitled module"}
              </span>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${PHASE_BADGE_STYLES[phase] || PHASE_BADGE_STYLES.custom}`}
              >
                {PHASES.find((p) => p.value === phase)?.label ?? phase}
              </span>
              {module.is_role_specific && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-50 text-purple-700 border border-purple-200">
                  Role-specific
                </span>
              )}
              {!module.is_mandatory && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border border-[var(--color-gray-200)]">
                  Optional
                </span>
              )}
            </div>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
              {module.steps?.length ?? 0} step
              {(module.steps?.length ?? 0) !== 1 ? "s" : ""}
              {module.estimated_duration_minutes
                ? ` · ~${module.estimated_duration_minutes} min`
                : ""}
              {typeof module.sort_order === "number"
                ? ` · order ${module.sort_order}`
                : ""}
            </p>
            {module.description && (
              <p className="text-xs text-[var(--color-gray-500)] mt-1">
                {module.description}
              </p>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"
              title="Edit module"
            >
              <Pencil className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="p-1.5 rounded-lg hover:bg-red-50 transition-colors text-[var(--color-gray-500)] hover:text-red-600 disabled:opacity-50"
              title="Delete module"
            >
              {deleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        {expanded && (
          <div className="mt-3 pl-6 space-y-2">
            {(module.steps?.length ?? 0) === 0 ? (
              <p className="text-xs text-[var(--color-gray-500)] py-2">
                No steps in this module yet.
              </p>
            ) : (
              (module.steps ?? []).map((step, idx) => {
                const Icon = STEP_TYPE_ICONS[step.step_type] || FileText;
                return (
                  <div
                    key={step.id}
                    className="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-[var(--color-gray-50)] border border-transparent hover:border-[var(--color-gray-200)] transition-colors"
                  >
                    <span className="text-[10px] font-mono text-[var(--color-gray-400)] w-6 text-right flex-shrink-0">
                      {idx + 1}.
                    </span>
                    <Icon className="h-3.5 w-3.5 text-[var(--color-gray-500)] flex-shrink-0" />
                    <span className="text-sm text-[var(--color-gray-800)] flex-1 truncate">
                      {step.title}
                    </span>
                    <span className="text-[10px] text-[var(--color-gray-500)]">
                      {STEP_TYPES.find((t) => t.value === step.step_type)
                        ?.label ?? step.step_type}
                    </span>
                    <button
                      type="button"
                      onClick={() => setEditingStep(step)}
                      className="p-1 rounded hover:bg-[var(--color-gray-100)] transition-colors text-[var(--color-gray-500)]"
                      title="Edit step"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })
            )}
            <button
              type="button"
              onClick={() => setShowAddStep(true)}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium text-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              Add step
            </button>
          </div>
        )}
      </div>

      {editing && (
        <ModuleEditorModal
          mode="edit"
          templateId={module.template_id}
          module={module}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            onChanged();
          }}
        />
      )}
      {showAddStep && (
        <StepEditorModal
          mode="create"
          moduleId={module.id}
          onClose={() => setShowAddStep(false)}
          onSaved={() => {
            setShowAddStep(false);
            onChanged();
          }}
        />
      )}
      {editingStep && (
        <StepEditorModal
          mode="edit"
          moduleId={module.id}
          step={editingStep}
          onClose={() => setEditingStep(null)}
          onSaved={() => {
            setEditingStep(null);
            onChanged();
          }}
        />
      )}
    </AppCard>
  );
}

/* ── Edit-template metadata modal ────────────────────────── */

function EditTemplateModal({
  template,
  onClose,
  onSaved,
}: {
  template: OnboardingTemplateDetail;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(template.name);
  const [description, setDescription] = useState(template.description ?? "");
  const [isDefault, setIsDefault] = useState(template.is_default);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Template name is required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await onboardingApi.updateTemplateAdmin(template.id, {
        name: name.trim(),
        description: description.trim(),
        is_default: isDefault,
      });
      toast.success("Template updated.");
      onSaved();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to update template";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ModalShell title="Edit template" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <AppInput
          label="Name"
          value={name}
          onChange={(e) =>
            setName((e.target as HTMLInputElement | HTMLTextAreaElement).value)
          }
          required
        />
        <AppInput
          variant="textarea"
          label="Description"
          value={description}
          onChange={(e) =>
            setDescription(
              (e.target as HTMLInputElement | HTMLTextAreaElement).value,
            )
          }
          rows={3}
        />
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
            className="h-4 w-4 rounded border-[var(--color-gray-300)]"
          />
          <span className="text-sm text-[var(--color-gray-700)]">
            Default template — auto-assign to new hires
          </span>
        </label>
        <ModalFooter
          onClose={onClose}
          isSubmitting={isSubmitting}
          submitLabel="Save changes"
        />
      </form>
    </ModalShell>
  );
}

/* ── Add / edit module modal ─────────────────────────────── */

function ModuleEditorModal({
  mode,
  templateId,
  module,
  onClose,
  onSaved,
}: {
  mode: "create" | "edit";
  templateId: number;
  module?: OnboardingModule;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(module?.name ?? "");
  const [description, setDescription] = useState(module?.description ?? "");
  const [phase, setPhase] = useState(module?.phase ?? "custom");
  const [sortOrder, setSortOrder] = useState<number>(
    typeof module?.sort_order === "number"
      ? module.sort_order
      : typeof module?.order === "number"
        ? module.order
        : 0,
  );
  const [duration, setDuration] = useState<number>(
    module?.estimated_duration_minutes ?? 0,
  );
  const [isMandatory, setIsMandatory] = useState(module?.is_mandatory ?? true);
  const [isRoleSpecific, setIsRoleSpecific] = useState(
    module?.is_role_specific ?? false,
  );
  const [roleFilter, setRoleFilter] = useState(module?.role_filter ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Module name is required.");
      return;
    }
    if (isRoleSpecific && roleFilter.trim()) {
      // Validate role_filter is parseable as JSON array — backend stores it as JSON.
      try {
        const parsed = JSON.parse(roleFilter);
        if (!Array.isArray(parsed)) throw new Error("not an array");
      } catch {
        toast.error(
          'Role filter must be a JSON array, e.g. ["Engineer", "Designer"].',
        );
        return;
      }
    }
    setIsSubmitting(true);
    try {
      const payload: Partial<OnboardingModule> = {
        name: name.trim(),
        description: description.trim(),
        phase,
        sort_order: sortOrder,
        estimated_duration_minutes: duration,
        is_mandatory: isMandatory,
        is_role_specific: isRoleSpecific,
        role_filter: isRoleSpecific ? roleFilter.trim() : "",
      };
      if (mode === "create") {
        await onboardingApi.addModuleAdmin(templateId, payload);
        toast.success("Module added.");
      } else if (module) {
        await onboardingApi.updateModuleAdmin(module.id, payload);
        toast.success("Module updated.");
      }
      onSaved();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save module";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ModalShell
      title={mode === "create" ? "Add module" : "Edit module"}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <AppInput
          label="Module name"
          value={name}
          onChange={(e) =>
            setName((e.target as HTMLInputElement | HTMLTextAreaElement).value)
          }
          placeholder="e.g. Day-1 orientation"
          required
          autoFocus
        />
        <AppInput
          variant="textarea"
          label="Description"
          value={description}
          onChange={(e) =>
            setDescription(
              (e.target as HTMLInputElement | HTMLTextAreaElement).value,
            )
          }
          placeholder="What does this module cover?"
          rows={2}
        />
        <div className="grid grid-cols-2 gap-3">
          <AppInput
            variant="select"
            label="Phase"
            value={phase}
            onChange={(e) => setPhase((e.target as HTMLSelectElement).value)}
            options={PHASES}
          />
          <AppInput
            variant="number"
            label="Sort order"
            value={sortOrder}
            onChange={(e) =>
              setSortOrder(
                parseInt((e.target as HTMLInputElement).value || "0", 10),
              )
            }
            min={0}
            helperText="Lower numbers appear first"
          />
        </div>
        <AppInput
          variant="number"
          label="Estimated duration (minutes)"
          value={duration}
          onChange={(e) =>
            setDuration(
              parseInt((e.target as HTMLInputElement).value || "0", 10),
            )
          }
          min={0}
        />
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={isMandatory}
            onChange={(e) => setIsMandatory(e.target.checked)}
            className="h-4 w-4 rounded border-[var(--color-gray-300)]"
          />
          <span className="text-sm text-[var(--color-gray-700)]">
            Mandatory — required for completion
          </span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={isRoleSpecific}
            onChange={(e) => setIsRoleSpecific(e.target.checked)}
            className="h-4 w-4 rounded border-[var(--color-gray-300)]"
          />
          <span className="text-sm text-[var(--color-gray-700)]">
            Role-specific — only assign to certain designations
          </span>
        </label>
        {isRoleSpecific && (
          <AppInput
            label="Role filter (JSON array)"
            value={roleFilter}
            onChange={(e) =>
              setRoleFilter(
                (e.target as HTMLInputElement | HTMLTextAreaElement).value,
              )
            }
            placeholder='["Engineer", "Designer"]'
            helperText="Match employees whose designation appears in this list. Leave empty to apply to all roles."
          />
        )}
        <ModalFooter
          onClose={onClose}
          isSubmitting={isSubmitting}
          submitLabel={mode === "create" ? "Add module" : "Save changes"}
        />
      </form>
    </ModalShell>
  );
}

/* ── Add / edit step modal ───────────────────────────────── */

function StepEditorModal({
  mode,
  moduleId,
  step,
  onClose,
  onSaved,
}: {
  mode: "create" | "edit";
  moduleId: number;
  step?: OnboardingStep;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(step?.title ?? "");
  const [description, setDescription] = useState(step?.description ?? "");
  const [stepType, setStepType] = useState(step?.step_type ?? "content");
  const [bodyContent, setBodyContent] = useState(step?.body_content ?? "");
  const [sortOrder, setSortOrder] = useState<number>(
    typeof step?.sort_order === "number"
      ? step.sort_order
      : typeof step?.order === "number"
        ? step.order
        : 0,
  );
  const [requiresCompletion, setRequiresCompletion] = useState(
    step?.requires_completion ?? true,
  );
  const [requiresPrev, setRequiresPrev] = useState(
    step?.requires_previous_completion ?? false,
  );
  const [policyId, setPolicyId] = useState<string>(
    step?.policy_id ? String(step.policy_id) : "",
  );
  const [deleting, setDeleting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      toast.error("Step title is required.");
      return;
    }
    if (stepType === "policy_acknowledgment" && !policyId.trim()) {
      toast.error("Policy ID is required for policy-acknowledgment steps.");
      return;
    }
    setIsSubmitting(true);
    try {
      const payload: Partial<OnboardingStep> = {
        title: title.trim(),
        description: description.trim(),
        step_type: stepType,
        body_content: bodyContent,
        sort_order: sortOrder,
        requires_completion: requiresCompletion,
        requires_previous_completion: requiresPrev,
        policy_id: policyId.trim() ? parseInt(policyId.trim(), 10) : null,
      };
      if (mode === "create") {
        await onboardingApi.addStepAdmin(moduleId, payload);
        toast.success("Step added.");
      } else if (step) {
        await onboardingApi.updateStepAdmin(step.id, payload);
        toast.success("Step updated.");
      }
      onSaved();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save step";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!step) return;
    if (!window.confirm(`Delete step "${step.title}"?`)) return;
    setDeleting(true);
    try {
      await onboardingApi.deleteStepAdmin(step.id);
      toast.success("Step deleted.");
      onSaved();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to delete step";
      toast.error(message);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <ModalShell
      title={mode === "create" ? "Add step" : "Edit step"}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <AppInput
          label="Step title"
          value={title}
          onChange={(e) =>
            setTitle((e.target as HTMLInputElement | HTMLTextAreaElement).value)
          }
          placeholder="e.g. Read the welcome handbook"
          required
          autoFocus
        />
        <AppInput
          variant="textarea"
          label="Description (optional)"
          value={description}
          onChange={(e) =>
            setDescription(
              (e.target as HTMLInputElement | HTMLTextAreaElement).value,
            )
          }
          rows={2}
        />
        <div className="grid grid-cols-2 gap-3">
          <AppInput
            variant="select"
            label="Step type"
            value={stepType}
            onChange={(e) => setStepType((e.target as HTMLSelectElement).value)}
            options={STEP_TYPES}
          />
          <AppInput
            variant="number"
            label="Sort order"
            value={sortOrder}
            onChange={(e) =>
              setSortOrder(
                parseInt((e.target as HTMLInputElement).value || "0", 10),
              )
            }
            min={0}
          />
        </div>
        <AppInput
          variant="textarea"
          label="Body content"
          value={bodyContent}
          onChange={(e) =>
            setBodyContent(
              (e.target as HTMLInputElement | HTMLTextAreaElement).value,
            )
          }
          placeholder="Markdown or HTML content shown to the employee"
          rows={5}
          helperText={
            stepType === "checklist"
              ? "For checklists, you may also pass JSON-encoded items via the API."
              : undefined
          }
        />
        {stepType === "policy_acknowledgment" && (
          <AppInput
            variant="number"
            label="Policy ID"
            value={policyId ? parseInt(policyId, 10) : 0}
            onChange={(e) => setPolicyId((e.target as HTMLInputElement).value)}
            helperText="ID of the CompanyPolicy the employee must acknowledge."
          />
        )}
        <div className="space-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={requiresCompletion}
              onChange={(e) => setRequiresCompletion(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)]"
            />
            <span className="text-sm text-[var(--color-gray-700)]">
              Required to complete this step
            </span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={requiresPrev}
              onChange={(e) => setRequiresPrev(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)]"
            />
            <span className="text-sm text-[var(--color-gray-700)]">
              Block until previous step is complete (sequential)
            </span>
          </label>
        </div>
        <div className="flex gap-3 pt-2">
          {mode === "edit" && (
            <AppButton
              type="button"
              variant="danger"
              size="sm"
              onClick={handleDelete}
              loading={deleting}
              disabled={isSubmitting}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Delete
            </AppButton>
          )}
          <div className="flex-1" />
          <AppButton
            type="button"
            variant="outlined"
            size="sm"
            onClick={onClose}
            disabled={isSubmitting || deleting}
          >
            Cancel
          </AppButton>
          <AppButton
            type="submit"
            variant="primary"
            size="sm"
            loading={isSubmitting}
            disabled={deleting}
          >
            <Save className="h-4 w-4 mr-1" />
            {mode === "create" ? "Add step" : "Save changes"}
          </AppButton>
        </div>
      </form>
    </ModalShell>
  );
}

/* ── Modal shell + footer helpers ────────────────────────── */

function ModalShell({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function ModalFooter({
  onClose,
  isSubmitting,
  submitLabel,
}: {
  onClose: () => void;
  isSubmitting: boolean;
  submitLabel: string;
}) {
  return (
    <div className="flex gap-3 pt-2">
      <AppButton
        type="button"
        variant="outlined"
        size="sm"
        onClick={onClose}
        className="flex-1"
        disabled={isSubmitting}
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
        <Save className="h-4 w-4 mr-1" />
        {submitLabel}
      </AppButton>
    </div>
  );
}
