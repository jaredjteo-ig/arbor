"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  Plus,
  ChevronDown,
  ChevronRight,
  Trash2,
  Copy,
  Star,
  GripVertical,
  Pencil,
  Archive,
  X,
  Upload,
  Layers,
  ListChecks,
} from "lucide-react";
import {
  onboardingApi,
  type OnboardingTemplate,
  type OnboardingModule,
  type OnboardingStep,
} from "@/services/api/onboarding";

/* ── Constants ───────────────────────────────────────────── */

const PHASES = [
  { value: "orientation", label: "Orientation" },
  { value: "compliance", label: "Compliance" },
  { value: "benefits", label: "Benefits" },
  { value: "probation", label: "Probation" },
  { value: "custom", label: "Custom" },
];

const STEP_TYPES = [
  { value: "content", label: "Content" },
  { value: "checklist", label: "Checklist" },
  { value: "document_upload", label: "Document Upload" },
  { value: "policy_acknowledgment", label: "Policy Acknowledgment" },
  { value: "form", label: "Form" },
  { value: "approval", label: "Approval" },
];

/* ── Phase badge ─────────────────────────────────────────── */

const PHASE_STYLES: Record<string, string> = {
  orientation: "bg-blue-50 text-blue-700 border-blue-200",
  compliance: "bg-amber-50 text-amber-700 border-amber-200",
  benefits: "bg-emerald-50 text-emerald-700 border-emerald-200",
  probation: "bg-purple-50 text-purple-700 border-purple-200",
  custom:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
};

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
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] text-[var(--color-gray-500)] bg-[var(--color-gray-50)] border border-[var(--color-gray-100)]">
      {type.replace(/_/g, " ")}
    </span>
  );
}

/* ── Module + steps in editor ────────────────────────────── */

interface ModuleWithSteps {
  module: OnboardingModule;
  steps: OnboardingStep[];
}

/* ── Step Editor Row ─────────────────────────────────────── */

function StepEditorRow({
  step,
  templateId,
  moduleId,
  onUpdate,
  onDelete,
}: {
  step: OnboardingStep;
  templateId: number;
  moduleId: number;
  onUpdate: (updated: OnboardingStep) => void;
  onDelete: (stepId: number) => void;
}) {
  const [isEditing, setIsEditing] = useState(!step.title);
  const [title, setTitle] = useState(step.title);
  const [stepType, setStepType] = useState(step.step_type || "content");
  const [bodyContent, setBodyContent] = useState(step.body_content || "");
  const [checklistItems, setChecklistItems] = useState(
    step.checklist_items || "",
  );
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleSave() {
    if (!title.trim()) {
      toast.error("Step title is required.");
      return;
    }
    setIsSaving(true);
    try {
      const data: Partial<OnboardingStep> = {
        title: title.trim(),
        step_type: stepType,
        body_content: bodyContent,
        checklist_items: checklistItems,
      };
      const updated = await onboardingApi.updateStep(
        templateId,
        moduleId,
        step.id,
        data,
      );
      onUpdate(updated);
      setIsEditing(false);
      toast.success("Step saved.");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save step";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    setIsDeleting(true);
    try {
      await onboardingApi.deleteStep(templateId, moduleId, step.id);
      onDelete(step.id);
      toast.success("Step deleted.");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to delete step";
      toast.error(message);
    } finally {
      setIsDeleting(false);
    }
  }

  if (!isEditing) {
    return (
      <div className="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-[var(--color-gray-50)] group">
        <GripVertical className="h-3.5 w-3.5 text-[var(--color-gray-300)] flex-shrink-0" />
        <span className="text-sm text-[var(--color-gray-800)] flex-1">
          {step.title}
        </span>
        <StepTypeBadge type={step.step_type || "content"} />
        <button
          type="button"
          onClick={() => setIsEditing(true)}
          className="p-1 rounded hover:bg-[var(--color-gray-100)] opacity-0 group-hover:opacity-100 transition-opacity"
          title="Edit step"
        >
          <Pencil className="h-3.5 w-3.5 text-[var(--color-gray-500)]" />
        </button>
        <button
          type="button"
          onClick={handleDelete}
          disabled={isDeleting}
          className="p-1 rounded hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50"
          title="Delete step"
        >
          <Trash2 className="h-3.5 w-3.5 text-[var(--color-gray-500)] hover:text-red-600" />
        </button>
      </div>
    );
  }

  return (
    <div className="border border-[var(--color-gray-200)] rounded-lg p-3 space-y-3 bg-[var(--color-gray-50)]">
      <div className="grid grid-cols-2 gap-3">
        <AppInput
          label="Step title"
          value={title}
          onChange={(e) => setTitle((e.target as HTMLInputElement).value)}
          placeholder="e.g. Read employee handbook"
        />
        <AppInput
          variant="select"
          label="Step type"
          value={stepType}
          onChange={(e) => setStepType((e.target as HTMLSelectElement).value)}
          options={STEP_TYPES}
        />
      </div>

      {(stepType === "content" || stepType === "form") && (
        <AppInput
          variant="textarea"
          label="Body content"
          value={bodyContent}
          onChange={(e) =>
            setBodyContent((e.target as HTMLTextAreaElement).value)
          }
          placeholder="Instructions or content for this step..."
        />
      )}

      {stepType === "checklist" && (
        <AppInput
          variant="textarea"
          label="Checklist items (one per line)"
          value={checklistItems}
          onChange={(e) =>
            setChecklistItems((e.target as HTMLTextAreaElement).value)
          }
          placeholder={
            "Complete tax form\nSet up direct deposit\nReview safety guidelines"
          }
          helperText="Enter each checklist item on a separate line."
        />
      )}

      {stepType === "policy_acknowledgment" && (
        <AppInput
          variant="number"
          label="Policy ID (optional)"
          value={step.policy_id ?? ""}
          onChange={() => {}}
          placeholder="Enter the policy ID to link"
          helperText="Link to a specific company policy for acknowledgment."
          disabled
        />
      )}

      <div className="flex items-center gap-2 justify-end">
        <AppButton
          variant="outlined"
          size="sm"
          onClick={() => {
            if (step.title) {
              setIsEditing(false);
              setTitle(step.title);
              setStepType(step.step_type || "content");
              setBodyContent(step.body_content || "");
              setChecklistItems(step.checklist_items || "");
            } else {
              handleDelete();
            }
          }}
        >
          Cancel
        </AppButton>
        <AppButton
          variant="primary"
          size="sm"
          onClick={handleSave}
          loading={isSaving}
        >
          Save Step
        </AppButton>
      </div>
    </div>
  );
}

/* ── Module Editor ───────────────────────────────────────── */

function ModuleEditor({
  templateId,
  mod,
  steps,
  onModuleUpdate,
  onModuleDelete,
  onStepsChange,
}: {
  templateId: number;
  mod: OnboardingModule;
  steps: OnboardingStep[];
  onModuleUpdate: (updated: OnboardingModule) => void;
  onModuleDelete: (moduleId: number) => void;
  onStepsChange: (moduleId: number, steps: OnboardingStep[]) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditingModule, setIsEditingModule] = useState(false);
  const [name, setName] = useState(mod.name);
  const [phase, setPhase] = useState(mod.phase || "custom");
  const [duration, setDuration] = useState(
    String(mod.estimated_duration_minutes || 30),
  );
  const [isMandatory, setIsMandatory] = useState(mod.is_mandatory);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isAddingStep, setIsAddingStep] = useState(false);

  async function handleSaveModule() {
    if (!name.trim()) {
      toast.error("Module name is required.");
      return;
    }
    setIsSaving(true);
    try {
      const updated = await onboardingApi.updateModule(templateId, mod.id, {
        name: name.trim(),
        phase,
        estimated_duration_minutes: parseInt(duration, 10) || 30,
        is_mandatory: isMandatory,
      });
      onModuleUpdate(updated);
      setIsEditingModule(false);
      toast.success("Module saved.");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save module";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteModule() {
    setIsDeleting(true);
    try {
      await onboardingApi.deleteModule(templateId, mod.id);
      onModuleDelete(mod.id);
      toast.success("Module deleted.");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to delete module";
      toast.error(message);
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleAddStep() {
    setIsAddingStep(true);
    try {
      const newStep = await onboardingApi.addStep(templateId, mod.id, {
        title: "",
        step_type: "content",
        order: steps.length + 1,
      });
      onStepsChange(mod.id, [...steps, newStep]);
      setIsExpanded(true);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to add step";
      toast.error(message);
    } finally {
      setIsAddingStep(false);
    }
  }

  function handleStepUpdate(updated: OnboardingStep) {
    const newSteps = steps.map((s) => (s.id === updated.id ? updated : s));
    onStepsChange(mod.id, newSteps);
  }

  function handleStepDelete(stepId: number) {
    const newSteps = steps.filter((s) => s.id !== stepId);
    onStepsChange(mod.id, newSteps);
  }

  return (
    <div className="border border-[var(--color-gray-200)] rounded-[12px] overflow-hidden">
      {/* Module header */}
      <div className="flex items-center gap-2 px-4 py-3 bg-[var(--color-gray-50)]">
        <GripVertical className="h-4 w-4 text-[var(--color-gray-300)] flex-shrink-0 cursor-grab" />
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex-shrink-0"
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-[var(--color-gray-500)]" />
          ) : (
            <ChevronRight className="h-4 w-4 text-[var(--color-gray-500)]" />
          )}
        </button>

        <div
          className="flex-1 min-w-0 cursor-pointer"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[var(--color-gray-900)] truncate">
              {mod.name || "Untitled Module"}
            </span>
            <PhaseBadge phase={mod.phase || "custom"} />
            {mod.is_mandatory && (
              <span className="text-[10px] font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">
                Required
              </span>
            )}
          </div>
          <p className="text-xs text-[var(--color-gray-500)]">
            {steps.length} step{steps.length !== 1 ? "s" : ""}
            {" / "}
            {mod.estimated_duration_minutes || 0} min
          </p>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            type="button"
            onClick={() => setIsEditingModule(!isEditingModule)}
            className="p-1.5 rounded-lg hover:bg-[var(--color-gray-200)] transition-colors"
            title="Edit module"
          >
            <Pencil className="h-3.5 w-3.5 text-[var(--color-gray-500)]" />
          </button>
          <button
            type="button"
            onClick={handleDeleteModule}
            disabled={isDeleting}
            className="p-1.5 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
            title="Delete module"
          >
            <Trash2 className="h-3.5 w-3.5 text-[var(--color-gray-500)] hover:text-red-600" />
          </button>
        </div>
      </div>

      {/* Module edit form */}
      {isEditingModule && (
        <div className="px-4 py-3 border-t border-[var(--color-gray-200)] bg-white space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <AppInput
              label="Module name"
              value={name}
              onChange={(e) => setName((e.target as HTMLInputElement).value)}
              placeholder="e.g. Day 1 Orientation"
            />
            <AppInput
              variant="select"
              label="Phase"
              value={phase}
              onChange={(e) => setPhase((e.target as HTMLSelectElement).value)}
              options={PHASES}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <AppInput
              variant="number"
              label="Duration (minutes)"
              value={duration}
              onChange={(e) =>
                setDuration((e.target as HTMLInputElement).value)
              }
              placeholder="30"
            />
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--color-gray-700)]">
                Required
              </label>
              <label className="flex items-center gap-2 min-h-[44px]">
                <input
                  type="checkbox"
                  checked={isMandatory}
                  onChange={(e) => setIsMandatory(e.target.checked)}
                  className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
                />
                <span className="text-sm text-[var(--color-gray-600)]">
                  Mandatory for all employees
                </span>
              </label>
            </div>
          </div>
          <div className="flex items-center gap-2 justify-end">
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => {
                setIsEditingModule(false);
                setName(mod.name);
                setPhase(mod.phase || "custom");
                setDuration(String(mod.estimated_duration_minutes || 30));
                setIsMandatory(mod.is_mandatory);
              }}
            >
              Cancel
            </AppButton>
            <AppButton
              variant="primary"
              size="sm"
              onClick={handleSaveModule}
              loading={isSaving}
            >
              Save Module
            </AppButton>
          </div>
        </div>
      )}

      {/* Steps */}
      {isExpanded && (
        <div className="px-4 py-3 border-t border-[var(--color-gray-200)] space-y-2">
          {steps.length === 0 ? (
            <p className="text-xs text-[var(--color-gray-500)] text-center py-2">
              No steps yet. Add one to get started.
            </p>
          ) : (
            steps.map((step) => (
              <StepEditorRow
                key={step.id}
                step={step}
                templateId={templateId}
                moduleId={mod.id}
                onUpdate={handleStepUpdate}
                onDelete={handleStepDelete}
              />
            ))
          )}

          <AppButton
            variant="text"
            size="sm"
            onClick={handleAddStep}
            loading={isAddingStep}
            className="w-full"
          >
            <Plus className="h-3.5 w-3.5 mr-1" />
            Add Step
          </AppButton>
        </div>
      )}
    </div>
  );
}

/* ── Template Editor ─────────────────────────────────────── */

function TemplateEditor({
  template,
  onClose,
  onSaved,
}: {
  template: OnboardingTemplate;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [templateName, setTemplateName] = useState(template.name);
  const [description, setDescription] = useState(template.description || "");
  const [modules, setModules] = useState<ModuleWithSteps[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingHeader, setIsSavingHeader] = useState(false);
  const [isAddingModule, setIsAddingModule] = useState(false);

  const fetchTemplate = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await onboardingApi.getTemplate(template.id);
      setModules(
        (data.modules || []).map((m) => ({
          module: m.module,
          steps: m.steps || [],
        })),
      );
      setTemplateName(data.template.name);
      setDescription(data.template.description || "");
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

  async function handleSaveHeader() {
    if (!templateName.trim()) {
      toast.error("Template name is required.");
      return;
    }
    setIsSavingHeader(true);
    try {
      await onboardingApi.updateTemplate(template.id, {
        name: templateName.trim(),
        description: description.trim(),
      });
      toast.success("Template details saved.");
      onSaved();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save template";
      toast.error(message);
    } finally {
      setIsSavingHeader(false);
    }
  }

  async function handleAddModule() {
    setIsAddingModule(true);
    try {
      const newModule = await onboardingApi.addModule(template.id, {
        name: "New Module",
        phase: "custom",
        order: modules.length + 1,
        estimated_duration_minutes: 30,
        is_mandatory: true,
      });
      setModules([...modules, { module: newModule, steps: [] }]);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to add module";
      toast.error(message);
    } finally {
      setIsAddingModule(false);
    }
  }

  function handleModuleUpdate(updated: OnboardingModule) {
    setModules(
      modules.map((m) =>
        m.module.id === updated.id ? { ...m, module: updated } : m,
      ),
    );
  }

  function handleModuleDelete(moduleId: number) {
    setModules(modules.filter((m) => m.module.id !== moduleId));
  }

  function handleStepsChange(moduleId: number, steps: OnboardingStep[]) {
    setModules(
      modules.map((m) => (m.module.id === moduleId ? { ...m, steps } : m)),
    );
  }

  const totalSteps = modules.reduce((sum, m) => sum + m.steps.length, 0);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
            title="Back to templates"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
          <h3 className="text-lg font-semibold text-[var(--color-gray-900)]">
            Edit Template
          </h3>
        </div>
        <div className="flex items-center gap-2 text-xs text-[var(--color-gray-500)]">
          <span>
            {modules.length} module{modules.length !== 1 ? "s" : ""}
          </span>
          <span className="text-[var(--color-gray-300)]">/</span>
          <span>
            {totalSteps} step{totalSteps !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Template name and description */}
      <AppCard variant="standard">
        <div className="space-y-3">
          <AppInput
            label="Template name"
            value={templateName}
            onChange={(e) =>
              setTemplateName((e.target as HTMLInputElement).value)
            }
            placeholder="e.g. Standard Employee Onboarding"
          />
          <AppInput
            variant="textarea"
            label="Description"
            value={description}
            onChange={(e) =>
              setDescription((e.target as HTMLTextAreaElement).value)
            }
            placeholder="Describe the purpose and scope of this onboarding template..."
          />
          <div className="flex justify-end">
            <AppButton
              variant="primary"
              size="sm"
              onClick={handleSaveHeader}
              loading={isSavingHeader}
            >
              Save Details
            </AppButton>
          </div>
        </div>
      </AppCard>

      {/* Modules */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-[var(--color-gray-700)]">
            Modules
          </h4>
          <AppButton
            variant="outlined"
            size="sm"
            onClick={handleAddModule}
            loading={isAddingModule}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Module
          </AppButton>
        </div>

        {isLoading ? (
          <div className="py-8 text-center">
            <span className="inline-block h-5 w-5 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : modules.length === 0 ? (
          <div className="py-8 text-center border-2 border-dashed border-[var(--color-gray-200)] rounded-[12px]">
            <Layers className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2" />
            <p className="text-sm text-[var(--color-gray-500)]">
              No modules yet. Add a module to start building this template.
            </p>
          </div>
        ) : (
          modules.map((m) => (
            <ModuleEditor
              key={m.module.id}
              templateId={template.id}
              mod={m.module}
              steps={m.steps}
              onModuleUpdate={handleModuleUpdate}
              onModuleDelete={handleModuleDelete}
              onStepsChange={handleStepsChange}
            />
          ))
        )}
      </div>
    </div>
  );
}

/* ── Create Template Modal ───────────────────────────────── */

function CreateTemplateModal({
  isOpen,
  onClose,
  onCreated,
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (template: OnboardingTemplate) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Template name is required.");
      return;
    }
    setIsSubmitting(true);
    try {
      const created = await onboardingApi.createTemplate({
        name: name.trim(),
        description: description.trim(),
      });
      toast.success("Template created. You can now add modules and steps.");
      setName("");
      setDescription("");
      onCreated(created);
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
            <ListChecks className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Create Template
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
            label="Template name"
            value={name}
            onChange={(e) => setName((e.target as HTMLInputElement).value)}
            placeholder="e.g. Standard Employee Onboarding"
          />
          <AppInput
            variant="textarea"
            label="Description (optional)"
            value={description}
            onChange={(e) =>
              setDescription((e.target as HTMLTextAreaElement).value)
            }
            placeholder="Describe the purpose of this template..."
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
              Create Template
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   TemplateBuilder — main export
   ═══════════════════════════════════════════════════════════ */

export function TemplateBuilder({
  onImportClick,
}: {
  onImportClick: () => void;
}) {
  const [templates, setTemplates] = useState<OnboardingTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTemplate, setEditingTemplate] =
    useState<OnboardingTemplate | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

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

  function handleCreated(template: OnboardingTemplate) {
    setShowCreateModal(false);
    setTemplates((prev) => [...prev, template]);
    setEditingTemplate(template);
  }

  // If we're editing a template, show the editor
  if (editingTemplate) {
    return (
      <TemplateEditor
        template={editingTemplate}
        onClose={() => {
          setEditingTemplate(null);
          fetchTemplates();
        }}
        onSaved={fetchTemplates}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Section header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-800)]">
            Onboarding Templates
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Create and manage onboarding templates for new employees
          </p>
        </div>
        <div className="flex items-center gap-2">
          <AppButton variant="outlined" size="sm" onClick={onImportClick}>
            <Upload className="h-4 w-4 mr-1" />
            Import
          </AppButton>
          <AppButton
            variant="primary"
            size="sm"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Create Template
          </AppButton>
        </div>
      </div>

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
        <div className="py-8 text-center border-2 border-dashed border-[var(--color-gray-200)] rounded-[12px]">
          <ListChecks className="h-10 w-10 text-[var(--color-gray-300)] mx-auto mb-3" />
          <p className="text-sm text-[var(--color-gray-600)] mb-1">
            No onboarding templates yet
          </p>
          <p className="text-xs text-[var(--color-gray-500)] mb-4">
            Create a template to define the onboarding journey for new hires.
          </p>
          <div className="flex items-center justify-center gap-2">
            <AppButton variant="outlined" size="sm" onClick={onImportClick}>
              <Upload className="h-4 w-4 mr-1" />
              Import from File
            </AppButton>
            <AppButton
              variant="primary"
              size="sm"
              onClick={() => setShowCreateModal(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              Create Template
            </AppButton>
          </div>
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
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-[var(--color-gray-900)]">
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
                          onClick={() => setEditingTemplate(t)}
                          className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"
                          title="Edit template"
                        >
                          <Pencil className="h-4 w-4" />
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

      {/* Create modal */}
      <CreateTemplateModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={handleCreated}
      />
    </div>
  );
}
