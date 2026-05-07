"use client";

import { useState } from "react";
import { Loader2, Plus, Users } from "lucide-react";
import {
  engagementApi,
  parseFilterSpec,
  type EngagementCohortRow,
  type CohortFilterSpec,
  type CohortPreviewResponse,
} from "@/services/api/engagement";

interface CohortsTabProps {
  cohorts: EngagementCohortRow[];
  onChange: () => void;
}

type Preset = "all_active" | "by_department" | "new_joiners" | "ad_hoc";

export function CohortsTab({ cohorts, onChange }: CohortsTabProps) {
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div>
      <div className="flex justify-end mb-4">
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          New cohort
        </button>
      </div>

      {cohorts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] bg-white p-12 text-center text-sm text-[var(--color-gray-500)]">
          No saved cohorts yet. Create your first one — start with{" "}
          <em>All active staff</em> or <em>By department</em>.
        </div>
      ) : (
        <div className="grid gap-3">
          {cohorts.map((c) => {
            const spec = parseFilterSpec(c.filter_spec);
            return (
              <div
                key={c.id}
                className="rounded-lg border border-[var(--color-gray-200)] bg-white p-4 flex items-start gap-4"
              >
                <Users className="h-5 w-5 text-[var(--color-gray-400)] mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-[var(--color-gray-900)]">
                    {c.name}
                  </div>
                  {c.description && (
                    <div className="text-sm text-[var(--color-gray-500)] mt-0.5">
                      {c.description}
                    </div>
                  )}
                  <div className="text-xs text-[var(--color-gray-400)] mt-1">
                    {summariseFilterSpec(spec)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <p className="mt-6 text-xs text-[var(--color-gray-500)] italic">
        P1 supports presets (all active, by department, new joiners under 90
        days) plus an ad-hoc employee list. The full filter builder lands in v2.
      </p>

      {showCreate && (
        <CohortCreateModal
          onClose={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false);
            onChange();
          }}
        />
      )}
    </div>
  );
}

function summariseFilterSpec(spec: CohortFilterSpec): string {
  const parts: string[] = [];
  if (spec.all_active) parts.push("All active staff");
  if (spec.departments?.length)
    parts.push(`Departments: ${spec.departments.join(", ")}`);
  if (spec.tenure_max_days !== undefined && spec.tenure_max_days !== null)
    parts.push(`Tenure ≤ ${spec.tenure_max_days} days`);
  if (spec.ad_hoc_employee_ids?.length)
    parts.push(`+${spec.ad_hoc_employee_ids.length} ad-hoc`);
  return parts.length ? parts.join(" · ") : "—";
}

/* ── Create modal ─────────────────────────────────────────── */

function CohortCreateModal({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const [preset, setPreset] = useState<Preset>("all_active");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [departments, setDepartments] = useState<string>("");
  const [adHocIds, setAdHocIds] = useState<string>("");
  const [preview, setPreview] = useState<CohortPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function buildSpec(): CohortFilterSpec {
    const spec: CohortFilterSpec = {};
    if (preset === "all_active") spec.all_active = true;
    if (preset === "by_department") {
      const ds = departments
        .split(",")
        .map((d) => d.trim())
        .filter(Boolean);
      if (ds.length) spec.departments = ds;
    }
    if (preset === "new_joiners") spec.tenure_max_days = 90;
    if (adHocIds.trim()) {
      spec.ad_hoc_employee_ids = adHocIds
        .split(",")
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n) && n > 0);
    }
    return spec;
  }

  async function runPreview() {
    setPreviewLoading(true);
    setError(null);
    try {
      const r = await engagementApi.previewCohort({
        filter_spec: buildSpec(),
        anonymity_tier: "pseudonymous",
      });
      setPreview(r);
    } catch (err) {
      setError((err as Error).message || "Preview failed");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function save() {
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await engagementApi.createCohort({
        name: name.trim(),
        description: description.trim() || undefined,
        filter_spec: buildSpec(),
      });
      onSaved();
    } catch (err) {
      setError((err as Error).message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">New cohort</h2>

        <label className="block text-sm font-medium mb-1">Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Engineering only"
          className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 mb-3 text-sm"
        />

        <label className="block text-sm font-medium mb-1">
          Description (optional)
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 mb-4 text-sm"
        />

        <fieldset className="mb-4">
          <legend className="text-sm font-medium mb-2">Preset</legend>
          {(
            [
              { v: "all_active", label: "All active staff" },
              { v: "by_department", label: "By department" },
              { v: "new_joiners", label: "New joiners (under 90 days)" },
              { v: "ad_hoc", label: "Ad-hoc list only" },
            ] as const
          ).map(({ v, label }) => (
            <label
              key={v}
              className="flex items-center gap-2 mb-2 cursor-pointer"
            >
              <input
                type="radio"
                name="cohort-preset"
                value={v}
                checked={preset === v}
                onChange={() => setPreset(v as Preset)}
              />
              <span className="text-sm">{label}</span>
            </label>
          ))}
        </fieldset>

        {preset === "by_department" && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">
              Departments (comma-separated)
            </label>
            <input
              type="text"
              value={departments}
              onChange={(e) => setDepartments(e.target.value)}
              placeholder="Engineering, Sales"
              className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 text-sm"
            />
          </div>
        )}

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">
            Add specific employee IDs (optional, comma-separated)
          </label>
          <input
            type="text"
            value={adHocIds}
            onChange={(e) => setAdHocIds(e.target.value)}
            placeholder="123, 456, 789"
            className="w-full border border-[var(--color-gray-200)] rounded-md px-3 py-2 text-sm"
          />
        </div>

        <button
          onClick={runPreview}
          disabled={previewLoading}
          className="w-full text-sm py-2 rounded-md border border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)] mb-3 disabled:opacity-50"
        >
          {previewLoading ? "Previewing…" : "Preview matched employees"}
        </button>

        {preview && (
          <div className="rounded-md bg-[var(--color-gray-50)] p-3 text-sm mb-3">
            <div className="font-medium">{preview.matched_count} matched</div>
            {preview.sample_names.length > 0 && (
              <div className="text-xs text-[var(--color-gray-500)] mt-1">
                Sample: {preview.sample_names.slice(0, 5).join(", ")}
                {preview.sample_names.length > 5 ? "…" : ""}
              </div>
            )}
            {preview.warnings.map((w, i) => (
              <div
                key={i}
                className={`text-xs mt-2 ${w.kind === "anonymity_unsafe" ? "text-red-600" : "text-amber-600"}`}
              >
                ⚠ {w.message}
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-md bg-red-50 text-red-700 text-sm p-2 mb-3">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-md border border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving || !name.trim()}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-md bg-rose-600 hover:bg-rose-700 text-white disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Save cohort
          </button>
        </div>
      </div>
    </div>
  );
}
