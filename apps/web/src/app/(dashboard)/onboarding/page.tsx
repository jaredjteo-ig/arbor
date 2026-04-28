"use client";

/**
 * /onboarding — Admin Onboarding Templates list.
 *
 * Lists all onboarding templates for the current company with per-row
 * actions: Edit (links to /onboarding/templates/[id]), Set default,
 * Archive, Duplicate. Includes a Create-template modal and an Assign
 * Template entry point that opens the existing AssignTemplateModal.
 *
 * The "set default" action ensures only one template per company is
 * marked default — the backend already enforces this on update.
 *
 * Owner / hr_manager only (AdminGuard).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ClipboardList,
  Plus,
  Pencil,
  Star,
  Archive,
  Copy,
  Loader2,
  Layers,
  ListChecks,
} from "lucide-react";

import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  AppButton,
  AppCard,
  AppInput,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  onboardingApi,
  type OnboardingTemplate,
} from "@/services/api/onboarding";

export default function OnboardingTemplatesPage() {
  return (
    <AdminGuard>
      <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-gray-900)]">
              Onboarding Templates
            </h1>
            <p className="mt-1 text-sm text-[var(--color-gray-500)]">
              Build reusable onboarding paths for new hires. The default
              template is auto-assigned when an employee accepts their
              invitation.
            </p>
          </div>
        </header>
        <TemplateList />
      </div>
    </AdminGuard>
  );
}

/* ── Template list section ───────────────────────────────── */

function TemplateList() {
  const router = useRouter();
  const [templates, setTemplates] = useState<OnboardingTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

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

  const sortedTemplates = useMemo(() => {
    return [...templates].sort((a, b) => {
      // Default first, then alpha
      if (a.is_default !== b.is_default) return a.is_default ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
  }, [templates]);

  async function handleSetDefault(t: OnboardingTemplate) {
    setActionLoading(`default-${t.id}`);
    try {
      await onboardingApi.updateTemplateAdmin(t.id, { is_default: true });
      setTemplates((prev) =>
        prev.map((tpl) => ({ ...tpl, is_default: tpl.id === t.id })),
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
    if (
      !window.confirm(
        `Archive "${t.name}"? It will no longer appear in the assignment picker but existing assignments will be preserved.`,
      )
    ) {
      return;
    }
    setActionLoading(`archive-${t.id}`);
    try {
      await onboardingApi.deleteTemplate(t.id);
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

  async function handleDuplicate(t: OnboardingTemplate) {
    setActionLoading(`dup-${t.id}`);
    try {
      const copy = await onboardingApi.duplicateTemplate(t.id);
      // Backend may return either the bare template or a {template} envelope —
      // tolerate both shapes.
      const created =
        (copy as unknown as { template?: OnboardingTemplate }).template ??
        (copy as OnboardingTemplate);
      setTemplates((prev) => [...prev, created]);
      toast.success(`Duplicated as "${created.name}".`);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to duplicate";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  function handleCreated(t: OnboardingTemplate) {
    setTemplates((prev) => [...prev, t]);
    setShowCreate(false);
    // Jump straight into the builder so the user can start adding modules.
    router.push(`/onboarding/templates/${t.id}`);
  }

  return (
    <>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-base font-semibold text-[var(--color-gray-800)]">
          {templates.length} template{templates.length !== 1 ? "s" : ""}
        </h2>
        <AppButton
          variant="primary"
          size="sm"
          onClick={() => setShowCreate(true)}
        >
          <Plus className="h-4 w-4 mr-1" />
          Create template
        </AppButton>
      </div>

      {isLoading ? (
        <AppCard variant="standard">
          <div className="animate-pulse space-y-3 py-2">
            {Array.from({ length: 3 }, (_, i) => (
              <div key={i} className="flex items-center gap-4 py-3">
                <div className="h-4 w-44 bg-[var(--color-gray-200)] rounded" />
                <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
                <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded ml-auto" />
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
        <EmptyState
          icon={<ClipboardList className="h-10 w-10" aria-hidden="true" />}
          message="No onboarding templates yet"
          description="Create your first template to start standardising new-hire onboarding."
          action={
            <AppButton
              variant="primary"
              size="sm"
              onClick={() => setShowCreate(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              Create template
            </AppButton>
          }
        />
      ) : (
        <AppCard variant="standard">
          <div className="overflow-x-auto -mx-5 -my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)]">
                  <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                    Template
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
                {sortedTemplates.map((t) => (
                  <tr
                    key={t.id}
                    className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                  >
                    <td className="py-3 px-5">
                      <button
                        type="button"
                        onClick={() =>
                          router.push(`/onboarding/templates/${t.id}`)
                        }
                        className="text-left"
                      >
                        <div className="flex items-center gap-2">
                          <Layers className="h-4 w-4 text-[var(--color-gray-400)]" />
                          <span className="font-medium text-[var(--color-gray-900)] hover:text-[var(--color-primary)] transition-colors">
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
                          <p className="text-xs text-[var(--color-gray-500)] mt-0.5 truncate max-w-md">
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
                          onClick={() =>
                            router.push(`/onboarding/templates/${t.id}`)
                          }
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

      <p className="text-xs text-[var(--color-gray-400)] flex items-center gap-1.5">
        <ListChecks className="h-3.5 w-3.5" />
        Tip: mark one template as default and it will be auto-assigned to every
        new employee on registration.
      </p>

      {showCreate && (
        <CreateTemplateModal
          onCreated={handleCreated}
          onClose={() => setShowCreate(false)}
        />
      )}
    </>
  );
}

/* ── Create-template modal ───────────────────────────────── */

function CreateTemplateModal({
  onCreated,
  onClose,
}: {
  onCreated: (t: OnboardingTemplate) => void;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      toast.error("Please enter a template name.");
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await onboardingApi.createTemplateAdmin({
        name: trimmedName,
        description: description.trim(),
        is_default: isDefault,
      });
      toast.success("Template created.");
      onCreated(res.template);
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
        <h2 className="text-lg font-semibold text-[var(--color-gray-900)] mb-4">
          Create onboarding template
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <AppInput
            label="Name"
            value={name}
            onChange={(e) =>
              setName(
                (e.target as HTMLInputElement | HTMLTextAreaElement).value,
              )
            }
            placeholder="e.g. Standard new-hire onboarding"
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
            placeholder="When should this template be used?"
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
              Set as default — auto-assign to every new hire
            </span>
          </label>
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
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Creating…
                </>
              ) : (
                "Create"
              )}
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}
