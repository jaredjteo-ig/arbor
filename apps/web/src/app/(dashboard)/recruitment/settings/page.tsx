"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Loader2,
  Plus,
  Trash2,
  Pencil,
  Bot,
  Mail,
  ShieldAlert,
} from "lucide-react";

import { AdminGuard } from "@/components/auth/AdminGuard";
import { toast } from "@/components/design-system";
import { recruitmentApi } from "@/services/api";
import type {
  ScorecardTemplate,
  ScorecardCriterion,
} from "@/services/api/recruitment";

type CriterionDraft = { name: string; weight: number };

const AI_TOGGLE_KEY = "recruitment.tafep.ai_check";

export default function RecruitmentSettingsPage() {
  return (
    <AdminGuard>
      <div className="max-w-4xl mx-auto py-8 px-4 space-y-10">
        <header>
          <h1 className="text-2xl font-semibold text-[var(--color-gray-900)]">
            Recruitment Settings
          </h1>
          <p className="mt-1 text-sm text-[var(--color-gray-500)]">
            Manage interview scorecards, run maintenance sweeps, and configure
            the TAFEP AI compliance scanner.
          </p>
        </header>
        <AiScanToggle />
        <ScorecardTemplates />
        <MaintenanceSweeps />
      </div>
    </AdminGuard>
  );
}

/* ── 1. AI scan toggle ──────────────────────────────────────── */

function AiScanToggle() {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const v = window.localStorage.getItem(AI_TOGGLE_KEY) === "1";
    setEnabled(v);
  }, []);

  const handleToggle = useCallback((next: boolean) => {
    setEnabled(next);
    if (next) {
      window.localStorage.setItem(AI_TOGGLE_KEY, "1");
      toast.success("AI compliance second-pass enabled for TAFEP scans");
    } else {
      window.localStorage.removeItem(AI_TOGGLE_KEY);
      toast.success("AI compliance second-pass disabled (rule-based only)");
    }
  }, []);

  return (
    <section className="bg-white border border-[var(--color-gray-200)] rounded-lg p-6">
      <div className="flex items-start gap-4">
        <div className="rounded-md bg-[var(--color-gray-100)] p-2">
          <Bot className="h-5 w-5 text-[var(--color-primary)]" />
        </div>
        <div className="flex-1">
          <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
            TAFEP AI compliance scanner
          </h2>
          <p className="mt-1 text-sm text-[var(--color-gray-500)]">
            When enabled, every job-listing scan runs an AI second-pass after
            the rule-based check to catch subtler discrimination phrases. Falls
            back to rules if the AI service is unavailable. Each scan costs
            approximately 1¢ in API tokens.
          </p>
          <label className="mt-4 inline-flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => handleToggle(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)]"
            />
            <span className="text-sm font-medium text-[var(--color-gray-900)]">
              Enable AI second-pass on TAFEP scans
            </span>
          </label>
        </div>
      </div>
    </section>
  );
}

/* ── 2. Scorecard templates ─────────────────────────────────── */

function ScorecardTemplates() {
  const [templates, setTemplates] = useState<ScorecardTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<ScorecardTemplate | null>(null);
  const [creating, setCreating] = useState(false);

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const res = await recruitmentApi.listScorecardTemplates();
      setTemplates(res.templates ?? []);
    } catch (err) {
      console.warn("Failed to load scorecard templates:", err);
      toast.error("Could not load scorecard templates");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const handleDelete = useCallback(
    async (id: number) => {
      if (
        !window.confirm(
          "Delete this scorecard template? This cannot be undone.",
        )
      ) {
        return;
      }
      try {
        await recruitmentApi.deleteScorecardTemplate(id);
        toast.success("Template deleted");
        loadTemplates();
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Delete failed";
        toast.error(message);
      }
    },
    [loadTemplates],
  );

  return (
    <section className="bg-white border border-[var(--color-gray-200)] rounded-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
            Interview scorecard templates
          </h2>
          <p className="mt-1 text-sm text-[var(--color-gray-500)]">
            Define structured evaluation criteria. Interviewers select a
            template when recording feedback. Criterion weights must sum to 1.0.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setCreating(true);
          }}
          className="inline-flex items-center gap-2 rounded-md bg-[var(--color-primary)] px-3 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          New template
        </button>
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-[var(--color-gray-500)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading templates…
          </div>
        ) : templates.length === 0 ? (
          <p className="text-sm text-[var(--color-gray-500)] py-6 text-center">
            No scorecard templates yet. Create one to enable structured
            interview feedback.
          </p>
        ) : (
          <ul className="divide-y divide-[var(--color-gray-200)]">
            {templates.map((tpl) => (
              <li
                key={tpl.id}
                className="py-4 flex items-start justify-between gap-4"
              >
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-[var(--color-gray-900)]">
                    {tpl.name}
                  </h3>
                  {tpl.description ? (
                    <p className="mt-1 text-xs text-[var(--color-gray-500)]">
                      {tpl.description}
                    </p>
                  ) : null}
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {tpl.criteria.map((c: ScorecardCriterion, idx: number) => (
                      <li
                        key={idx}
                        className="text-xs px-2 py-1 rounded bg-[var(--color-gray-100)] text-[var(--color-gray-700)]"
                      >
                        {c.name}{" "}
                        <span className="text-[var(--color-gray-500)]">
                          {Math.round((c.weight ?? 0) * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setCreating(false);
                      setEditing(tpl);
                    }}
                    className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-[var(--color-gray-700)] hover:bg-[var(--color-gray-100)]"
                  >
                    <Pencil className="h-3.5 w-3.5" /> Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(tpl.id)}
                    className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {(creating || editing) && (
        <ScorecardTemplateEditor
          template={editing}
          onSaved={() => {
            setCreating(false);
            setEditing(null);
            loadTemplates();
          }}
          onCancel={() => {
            setCreating(false);
            setEditing(null);
          }}
        />
      )}
    </section>
  );
}

function ScorecardTemplateEditor({
  template,
  onSaved,
  onCancel,
}: {
  template: ScorecardTemplate | null;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(template?.name ?? "");
  const [description, setDescription] = useState(template?.description ?? "");
  const [criteria, setCriteria] = useState<CriterionDraft[]>(
    template
      ? template.criteria.map((c: ScorecardCriterion) => ({
          name: c.name,
          weight: c.weight ?? 0,
        }))
      : [
          { name: "Technical skills", weight: 0.4 },
          { name: "Communication", weight: 0.3 },
          { name: "Cultural fit", weight: 0.3 },
        ],
  );
  const [saving, setSaving] = useState(false);

  const totalWeight = criteria.reduce((sum, c) => sum + (c.weight || 0), 0);
  const weightOk = Math.abs(totalWeight - 1.0) < 0.001;
  const namesOk = criteria.every((c) => c.name.trim().length > 0);
  const canSave =
    !saving &&
    name.trim().length > 0 &&
    criteria.length > 0 &&
    weightOk &&
    namesOk;

  const handleSubmit = async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || undefined,
        criteria: criteria.map((c) => ({
          name: c.name.trim(),
          weight: c.weight,
        })),
      };
      if (template) {
        await recruitmentApi.updateScorecardTemplate(template.id, payload);
        toast.success("Template updated");
      } else {
        await recruitmentApi.createScorecardTemplate(payload);
        toast.success("Template created");
      }
      onSaved();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Save failed";
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-6 border-t border-[var(--color-gray-200)] pt-6">
      <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
        {template ? `Edit "${template.name}"` : "New template"}
      </h3>

      <div className="mt-4 space-y-4">
        <div>
          <label className="block text-xs font-medium text-[var(--color-gray-700)] mb-1">
            Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Engineering Interview"
            className="w-full rounded border border-[var(--color-gray-300)] px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-[var(--color-gray-700)] mb-1">
            Description (optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full rounded border border-[var(--color-gray-300)] px-3 py-2 text-sm"
          />
        </div>
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-[var(--color-gray-700)]">
              Criteria & weights
            </label>
            <span
              className={`text-xs ${weightOk ? "text-green-600" : "text-red-600"}`}
            >
              Total: {(totalWeight * 100).toFixed(0)}%
              {!weightOk && " (must equal 100%)"}
            </span>
          </div>
          <ul className="space-y-2">
            {criteria.map((c, idx) => (
              <li key={idx} className="flex items-center gap-2">
                <input
                  type="text"
                  value={c.name}
                  onChange={(e) =>
                    setCriteria((prev) =>
                      prev.map((p, i) =>
                        i === idx ? { ...p, name: e.target.value } : p,
                      ),
                    )
                  }
                  placeholder="Criterion name"
                  className="flex-1 rounded border border-[var(--color-gray-300)] px-2 py-1.5 text-sm"
                />
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={c.weight}
                  onChange={(e) =>
                    setCriteria((prev) =>
                      prev.map((p, i) =>
                        i === idx
                          ? { ...p, weight: Number(e.target.value) || 0 }
                          : p,
                      ),
                    )
                  }
                  className="w-20 rounded border border-[var(--color-gray-300)] px-2 py-1.5 text-sm"
                />
                <button
                  type="button"
                  onClick={() =>
                    setCriteria((prev) => prev.filter((_, i) => i !== idx))
                  }
                  className="text-red-600 hover:bg-red-50 rounded p-1"
                  aria-label="Remove criterion"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() =>
              setCriteria((prev) => [...prev, { name: "", weight: 0 }])
            }
            className="mt-2 inline-flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline"
          >
            <Plus className="h-3.5 w-3.5" />
            Add criterion
          </button>
        </div>
        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-2 text-sm text-[var(--color-gray-700)] hover:bg-[var(--color-gray-100)] rounded"
            disabled={saving}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSave}
            className="inline-flex items-center gap-2 px-3 py-2 rounded bg-[var(--color-primary)] text-white text-sm font-medium disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {template ? "Save changes" : "Create template"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── 3. Maintenance sweeps ──────────────────────────────────── */

function MaintenanceSweeps() {
  const [retentionRunning, setRetentionRunning] = useState(false);
  const [reminderRunning, setReminderRunning] = useState(false);
  const [retentionResult, setRetentionResult] = useState<string | null>(null);
  const [reminderResult, setReminderResult] = useState<string | null>(null);

  const handleRetentionSweep = async () => {
    if (
      !window.confirm(
        "Run the PDPA data-retention sweep now?\n\nThis will email candidates whose applications are over 700 days old, warning that their data will be purged in 30 days. Safe to re-run — already-warned candidates are skipped.",
      )
    ) {
      return;
    }
    setRetentionRunning(true);
    setRetentionResult(null);
    try {
      const res = await recruitmentApi.runDataRetentionSweep();
      setRetentionResult(res.message);
      toast.success(res.message);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Sweep failed";
      toast.error(message);
      setRetentionResult(`Failed: ${message}`);
    } finally {
      setRetentionRunning(false);
    }
  };

  const handleReminderSweep = async () => {
    if (
      !window.confirm(
        "Send reminder emails to interviewers with overdue feedback?\n\nThis hits everyone whose interview was completed >48h ago without feedback. Safe to re-run.",
      )
    ) {
      return;
    }
    setReminderRunning(true);
    setReminderResult(null);
    try {
      const res = await recruitmentApi.runOverdueReminderSweep();
      setReminderResult(res.message);
      toast.success(res.message);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Sweep failed";
      toast.error(message);
      setReminderResult(`Failed: ${message}`);
    } finally {
      setReminderRunning(false);
    }
  };

  return (
    <section className="bg-white border border-[var(--color-gray-200)] rounded-lg p-6">
      <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
        Maintenance sweeps
      </h2>
      <p className="mt-1 text-sm text-[var(--color-gray-500)]">
        These should normally run on a daily cron. Click to trigger ad-hoc. Both
        are idempotent — safe to re-run.
      </p>

      <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="border border-[var(--color-gray-200)] rounded p-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-amber-600" />
            <h3 className="text-sm font-medium text-[var(--color-gray-900)]">
              PDPA data retention
            </h3>
          </div>
          <p className="mt-2 text-xs text-[var(--color-gray-500)]">
            Warns candidates whose data is approaching the 730-day PDPA
            retention limit. Stamps the warning date so we don't double-notify.
          </p>
          <button
            type="button"
            onClick={handleRetentionSweep}
            disabled={retentionRunning}
            className="mt-3 inline-flex items-center gap-2 px-3 py-2 rounded border border-[var(--color-gray-300)] text-sm font-medium hover:bg-[var(--color-gray-50)] disabled:opacity-50"
          >
            {retentionRunning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : null}
            Run retention sweep
          </button>
          {retentionResult ? (
            <p className="mt-2 text-xs text-[var(--color-gray-700)]">
              {retentionResult}
            </p>
          ) : null}
        </div>

        <div className="border border-[var(--color-gray-200)] rounded p-4">
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-[var(--color-primary)]" />
            <h3 className="text-sm font-medium text-[var(--color-gray-900)]">
              Overdue feedback reminders
            </h3>
          </div>
          <p className="mt-2 text-xs text-[var(--color-gray-500)]">
            Emails interviewers who have completed interviews from more than 48
            hours ago without submitting feedback.
          </p>
          <button
            type="button"
            onClick={handleReminderSweep}
            disabled={reminderRunning}
            className="mt-3 inline-flex items-center gap-2 px-3 py-2 rounded border border-[var(--color-gray-300)] text-sm font-medium hover:bg-[var(--color-gray-50)] disabled:opacity-50"
          >
            {reminderRunning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : null}
            Send reminders now
          </button>
          {reminderResult ? (
            <p className="mt-2 text-xs text-[var(--color-gray-700)]">
              {reminderResult}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
