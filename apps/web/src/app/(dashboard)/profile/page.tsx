"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Building2,
  Pencil,
  X,
  Check,
  Users,
  Mail,
  Clock,
  Plus,
} from "lucide-react";
import {
  AppCard,
  AppButton,
  AppInput,
  AlertBanner,
  LoadingState,
  ErrorState,
  toast,
} from "@/components/design-system";
import { useAuth } from "@/contexts/AuthContext";
import { profileApi } from "@/services/api/profile";
import type { CompanyProfile, CompanyProfileCreateRequest } from "@/types/api";

/* ── Types ────────────────────────────────────────────────── */

interface ProfileChangeEntry {
  field: string;
  oldValue: string;
  newValue: string;
  date: string;
}

type SectionKey = "details" | "workforce" | "contact";

/* ── Helpers ──────────────────────────────────────────────── */

function computeCompleteness(profile: CompanyProfile): number {
  const fields: (keyof CompanyProfile)[] = [
    "name",
    "uen",
    "sector",
    "headcount_local",
    "headcount_pr",
    "headcount_ep",
    "headcount_sp",
    "headcount_wp",
  ];
  let filled = 0;
  for (const f of fields) {
    const val = profile[f];
    if (val !== undefined && val !== null && val !== "" && val !== 0) {
      filled++;
    }
  }
  return Math.round((filled / fields.length) * 100);
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/* ── Circular Progress ────────────────────────────────────── */

function CircularProgress({ percent }: { percent: number }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  const color =
    percent === 100
      ? "var(--color-risk-green)"
      : percent >= 75
        ? "var(--color-primary)"
        : "var(--color-risk-amber)";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="100" height="100" viewBox="0 0 100 100" aria-hidden="true">
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke="var(--color-gray-200)"
          strokeWidth="8"
        />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 50 50)"
          className="transition-all duration-500"
        />
      </svg>
      <span
        className="absolute text-lg font-bold"
        style={{ color }}
        aria-label={`Profile ${percent}% complete`}
      >
        {percent}%
      </span>
    </div>
  );
}

/* ── Section Edit Wrapper ─────────────────────────────────── */

function SectionHeader({
  title,
  icon,
  editing,
  onEdit,
  onCancel,
  onSave,
  saving,
}: {
  title: string;
  icon: React.ReactNode;
  editing: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSave: () => void;
  saving: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        {icon}
        <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
          {title}
        </h2>
      </div>
      {editing ? (
        <div className="flex items-center gap-2">
          <AppButton
            variant="outlined"
            size="sm"
            onClick={onCancel}
            disabled={saving}
          >
            <X className="h-4 w-4" aria-hidden="true" />
            Cancel
          </AppButton>
          <AppButton size="sm" onClick={onSave} loading={saving}>
            <Check className="h-4 w-4" aria-hidden="true" />
            Save
          </AppButton>
        </div>
      ) : (
        <AppButton variant="text" size="sm" onClick={onEdit}>
          <Pencil className="h-4 w-4" aria-hidden="true" />
          Edit
        </AppButton>
      )}
    </div>
  );
}

/* ── Display Field ────────────────────────────────────────── */

function DisplayField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-[var(--color-gray-900)]">{value}</dd>
    </div>
  );
}

/* ── Sector Options (shared between create & edit) ────────── */

const SECTOR_OPTIONS = [
  { value: "Technology", label: "Technology" },
  { value: "Manufacturing", label: "Manufacturing" },
  { value: "Healthcare", label: "Healthcare" },
  { value: "Finance", label: "Finance" },
  { value: "F&B", label: "Food & Beverage" },
  { value: "Retail", label: "Retail" },
  { value: "Construction", label: "Construction" },
  { value: "Services", label: "Professional Services" },
  { value: "Other", label: "Other" },
];

/* ── Create Company Form ──────────────────────────────────── */

interface CreateFormData {
  name: string;
  uen: string;
  sector: string;
  headcount_local: number;
  headcount_pr: number;
  headcount_ep: number;
  headcount_sp: number;
  headcount_wp: number;
}

const INITIAL_FORM: CreateFormData = {
  name: "",
  uen: "",
  sector: "",
  headcount_local: 0,
  headcount_pr: 0,
  headcount_ep: 0,
  headcount_sp: 0,
  headcount_wp: 0,
};

function CreateCompanyForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState<CreateFormData>(INITIAL_FORM);
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<keyof CreateFormData, string>>
  >({});

  const updateField = useCallback(
    (field: keyof CreateFormData, value: string | number) => {
      setForm((prev) => ({ ...prev, [field]: value }));
      setFieldErrors((prev) => {
        if (!prev[field]) return prev;
        const next = { ...prev };
        delete next[field];
        return next;
      });
      setFormError(null);
    },
    [],
  );

  const validate = useCallback((): boolean => {
    const errors: Partial<Record<keyof CreateFormData, string>> = {};

    if (!form.name.trim()) {
      errors.name = "Company name is required";
    } else if (form.name.trim().length < 2) {
      errors.name = "Company name must be at least 2 characters";
    }

    if (form.uen && !/^[0-9]{8,9}[A-Za-z]$/.test(form.uen.trim())) {
      errors.uen =
        "UEN should be 8-9 digits followed by a letter (e.g. 200312345A)";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }, [form.name, form.uen]);

  const handleSubmit = useCallback(async () => {
    if (!validate()) return;
    setCreating(true);
    setFormError(null);

    const payload: CompanyProfileCreateRequest = {
      name: form.name.trim(),
      ...(form.uen.trim() ? { uen: form.uen.trim().toUpperCase() } : {}),
      ...(form.sector ? { sector: form.sector } : {}),
      headcount_local: form.headcount_local,
      headcount_pr: form.headcount_pr,
      headcount_ep: form.headcount_ep,
      headcount_sp: form.headcount_sp,
      headcount_wp: form.headcount_wp,
    };

    try {
      const result = await profileApi.create(payload);
      if (result.created) {
        toast.success("Company profile created successfully");
        onCreated();
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    } catch (err) {
      setFormError(
        err instanceof Error
          ? err.message
          : "Failed to create company profile. Please try again.",
      );
    } finally {
      setCreating(false);
    }
  }, [form, validate, onCreated]);

  const totalEmployees =
    form.headcount_local +
    form.headcount_pr +
    form.headcount_ep +
    form.headcount_sp +
    form.headcount_wp;

  return (
    <div className="space-y-6">
      {formError && (
        <AlertBanner
          variant="error"
          title="Could not create profile"
          description={formError}
          dismissible
          onDismiss={() => setFormError(null)}
        />
      )}

      {/* Step 1: Company Details */}
      <AppCard
        variant="standard"
        header={
          <div className="flex items-center gap-2">
            <Building2
              className="h-4 w-4 text-[var(--color-gray-500)]"
              aria-hidden="true"
            />
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Company Details
            </h2>
          </div>
        }
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <AppInput
            label="Company Name"
            placeholder="Enter your company name"
            value={form.name}
            onChange={(e) =>
              updateField("name", (e.target as HTMLInputElement).value)
            }
            error={fieldErrors.name}
          />
          <AppInput
            label="UEN (Business Registration Number)"
            placeholder="e.g. 200312345A"
            value={form.uen}
            onChange={(e) =>
              updateField("uen", (e.target as HTMLInputElement).value)
            }
            error={fieldErrors.uen}
            helperText="Singapore Unique Entity Number (optional)"
          />
          <AppInput
            label="Industry / Sector"
            variant="select"
            options={SECTOR_OPTIONS}
            placeholder="Select your industry"
            value={form.sector}
            onChange={(e) =>
              updateField("sector", (e.target as HTMLSelectElement).value)
            }
          />
        </div>
      </AppCard>

      {/* Step 2: Workforce */}
      <AppCard
        variant="standard"
        header={
          <div className="flex items-center gap-2">
            <Users
              className="h-4 w-4 text-[var(--color-gray-500)]"
              aria-hidden="true"
            />
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Workforce Breakdown
            </h2>
            {totalEmployees > 0 && (
              <span className="ml-auto text-sm text-[var(--color-gray-500)]">
                Total: {totalEmployees}
              </span>
            )}
          </div>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-gray-500)]">
            Enter the number of employees by pass type. This helps us provide
            accurate compliance guidance for your workforce composition. You can
            update these numbers later.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Local Citizens"
              variant="number"
              value={String(form.headcount_local)}
              onChange={(e) =>
                updateField(
                  "headcount_local",
                  parseInt((e.target as HTMLInputElement).value) || 0,
                )
              }
              min={0}
            />
            <AppInput
              label="Permanent Residents"
              variant="number"
              value={String(form.headcount_pr)}
              onChange={(e) =>
                updateField(
                  "headcount_pr",
                  parseInt((e.target as HTMLInputElement).value) || 0,
                )
              }
              min={0}
            />
            <AppInput
              label="Employment Pass (EP)"
              variant="number"
              value={String(form.headcount_ep)}
              onChange={(e) =>
                updateField(
                  "headcount_ep",
                  parseInt((e.target as HTMLInputElement).value) || 0,
                )
              }
              min={0}
            />
            <AppInput
              label="S Pass (SP)"
              variant="number"
              value={String(form.headcount_sp)}
              onChange={(e) =>
                updateField(
                  "headcount_sp",
                  parseInt((e.target as HTMLInputElement).value) || 0,
                )
              }
              min={0}
            />
            <AppInput
              label="Work Permit (WP)"
              variant="number"
              value={String(form.headcount_wp)}
              onChange={(e) =>
                updateField(
                  "headcount_wp",
                  parseInt((e.target as HTMLInputElement).value) || 0,
                )
              }
              min={0}
            />
          </div>
          <p className="text-xs text-[var(--color-gray-400)]">
            Don&apos;t know exact numbers yet? You can enter 0 for now and
            update your workforce details later.
          </p>
        </div>
      </AppCard>

      {/* Submit */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <AppButton
          variant="primary"
          onClick={handleSubmit}
          loading={creating}
          className="w-full sm:w-auto"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Create Company Profile
        </AppButton>
        <p className="text-xs text-[var(--color-gray-400)]">
          You can edit all details after creating your profile.
        </p>
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();

  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const [editDraft, setEditDraft] = useState<Partial<CompanyProfile>>({});
  const [editingSection, setEditingSection] = useState<SectionKey | null>(null);
  const [saving, setSaving] = useState(false);
  const [changeHistory, setChangeHistory] = useState<ProfileChangeEntry[]>([]);
  const [complianceWarning, setComplianceWarning] = useState(false);

  const fetchProfile = useCallback(() => {
    if (!user?.company_id) {
      setLoading(false);
      setProfile(null);
      return;
    }
    setLoading(true);
    setFetchError(null);
    profileApi
      .get(user.company_id)
      .then((data) => {
        setProfile(data);
      })
      .catch((err) => {
        setFetchError(
          err instanceof Error ? err.message : "Failed to load company profile",
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }, [user?.company_id]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const completeness = profile ? computeCompleteness(profile) : 0;

  const startEdit = useCallback(
    (section: SectionKey) => {
      if (!profile) return;
      setEditDraft({ ...profile });
      setEditingSection(section);
      setComplianceWarning(false);
    },
    [profile],
  );

  const cancelEdit = useCallback(() => {
    setEditingSection(null);
    setEditDraft({});
    setComplianceWarning(false);
  }, []);

  const handleDraftChange = useCallback(
    (field: keyof CompanyProfile, value: string | number | boolean) => {
      setEditDraft((prev) => ({ ...prev, [field]: value }));
      if (
        field === "headcount_local" ||
        field === "headcount_pr" ||
        field === "headcount_ep" ||
        field === "headcount_sp" ||
        field === "headcount_wp"
      ) {
        setComplianceWarning(true);
      }
    },
    [],
  );

  const saveSection = useCallback(async () => {
    if (!profile || !user?.company_id) return;
    setSaving(true);

    const now = new Date().toISOString().split("T")[0];
    const newEntries: ProfileChangeEntry[] = [];

    const fieldsToCheck: { key: keyof CompanyProfile; label: string }[] =
      editingSection === "details"
        ? [
            { key: "name", label: "Company Name" },
            { key: "sector", label: "Sector" },
          ]
        : editingSection === "workforce"
          ? [
              { key: "headcount_local", label: "Local Headcount" },
              { key: "headcount_pr", label: "PR Headcount" },
              { key: "headcount_ep", label: "EP Headcount" },
              { key: "headcount_sp", label: "SP Headcount" },
              { key: "headcount_wp", label: "WP Headcount" },
            ]
          : [{ key: "uen", label: "UEN" }];

    // Build the update payload with only changed fields
    const updatePayload: Record<string, unknown> = {};
    for (const { key, label } of fieldsToCheck) {
      const oldVal = String(profile[key] ?? "");
      const newVal = String(editDraft[key] ?? profile[key] ?? "");
      if (oldVal !== newVal) {
        newEntries.push({
          field: label,
          oldValue: oldVal,
          newValue: newVal,
          date: now,
        });
        updatePayload[key] = editDraft[key];
      }
    }

    if (Object.keys(updatePayload).length === 0) {
      // No changes made
      setEditingSection(null);
      setEditDraft({});
      setComplianceWarning(false);
      setSaving(false);
      return;
    }

    try {
      await profileApi.update(user.company_id, updatePayload);

      // Refetch the full profile to get the updated data
      const updated = await profileApi.get(user.company_id);
      setProfile(updated);

      if (newEntries.length > 0) {
        setChangeHistory((prev) => [...newEntries, ...prev]);
      }
      setEditingSection(null);
      setEditDraft({});
      setComplianceWarning(false);
      toast.success("Profile updated successfully");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to update profile",
      );
    } finally {
      setSaving(false);
    }
  }, [editDraft, editingSection, profile, user?.company_id]);

  /* ── RBAC: only owner / hr_manager may view ── */
  if (user?.role !== "owner" && user?.role !== "hr_manager") {
    return (
      <div className="max-w-6xl mx-auto py-12 text-center">
        <p className="text-[var(--color-gray-500)]">
          Access Denied. You do not have permission to view this page.
        </p>
        <a
          href="/dashboard"
          className="inline-block mt-4 text-sm text-[var(--color-primary)] hover:underline"
        >
          Return to Dashboard
        </a>
      </div>
    );
  }

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <Building2
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Company Profile
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Manage your company details used to personalise HR advisory
              responses.
            </p>
          </div>
        </div>
        <LoadingState variant="card" count={4} />
      </div>
    );
  }

  /* ── Error state ── */
  if (fetchError) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <Building2
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Company Profile
            </h1>
          </div>
        </div>
        <ErrorState
          variant="server"
          title="Failed to load profile"
          description={fetchError}
          onRetry={fetchProfile}
        />
      </div>
    );
  }

  /* ── No company profile yet — show creation form ── */
  if (!profile) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <Building2
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Set Up Company Profile
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Create your company profile to get personalised HR advisory
              responses, compliance checks, and workforce analytics.
            </p>
          </div>
        </div>

        <AlertBanner
          variant="info"
          title="Why set up a company profile?"
          description="Your company details help us tailor advisory responses to Singapore employment regulations that apply to your specific workforce composition, industry, and business size."
        />

        <CreateCompanyForm
          onCreated={async () => {
            // Refresh the user session so company_id is updated
            await refreshUser();
            // Re-fetch the profile (fetchProfile depends on user.company_id,
            // which will be updated after refreshUser completes and re-renders)
            fetchProfile();
          }}
        />
      </div>
    );
  }

  const totalHeadcount =
    profile.headcount_local +
    profile.headcount_pr +
    profile.headcount_ep +
    profile.headcount_sp +
    profile.headcount_wp;

  const hasForeignWorkers =
    profile.headcount_ep + profile.headcount_sp + profile.headcount_wp > 0;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Building2
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Company Profile
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Manage your company details used to personalise HR advisory
            responses.
          </p>
        </div>
      </div>

      {/* Profile Completeness */}
      <AppCard variant="elevated">
        <div className="flex items-center gap-6">
          <CircularProgress percent={completeness} />
          <div>
            <p className="text-sm font-semibold text-[var(--color-gray-900)]">
              Profile Completeness
            </p>
            <p className="text-sm text-[var(--color-gray-500)] mt-1">
              {completeness === 100
                ? "Your company profile is complete. Advisory responses will be fully personalised."
                : "Complete your profile to get more accurate advisory responses tailored to your company."}
            </p>
          </div>
        </div>
      </AppCard>

      {/* Compliance Warning */}
      {complianceWarning && (
        <AlertBanner
          variant="warning"
          title="Compliance impact"
          description="Updating workforce numbers may change compliance requirements. A new compliance check is recommended after saving."
          dismissible
          onDismiss={() => setComplianceWarning(false)}
        />
      )}

      {/* Company Details Section */}
      <AppCard
        variant="standard"
        header={
          <SectionHeader
            title="Company Details"
            icon={
              <Building2
                className="h-4 w-4 text-[var(--color-gray-500)]"
                aria-hidden="true"
              />
            }
            editing={editingSection === "details"}
            onEdit={() => startEdit("details")}
            onCancel={cancelEdit}
            onSave={saveSection}
            saving={saving}
          />
        }
      >
        {editingSection === "details" ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Company Name"
              value={editDraft.name ?? ""}
              onChange={(e) =>
                handleDraftChange("name", (e.target as HTMLInputElement).value)
              }
            />
            <AppInput
              label="UEN"
              value={profile.uen ?? ""}
              disabled
              helperText="UEN cannot be changed after registration"
            />
            <AppInput
              label="Sector"
              variant="select"
              options={SECTOR_OPTIONS}
              value={editDraft.sector ?? ""}
              onChange={(e) =>
                handleDraftChange(
                  "sector",
                  (e.target as HTMLSelectElement).value,
                )
              }
            />
          </div>
        ) : (
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <DisplayField label="Company Name" value={profile.name} />
            <DisplayField label="UEN" value={profile.uen ?? "Not set"} />
            <DisplayField label="Sector" value={profile.sector ?? "Not set"} />
          </dl>
        )}
      </AppCard>

      {/* Workforce Section */}
      <AppCard
        variant="standard"
        header={
          <SectionHeader
            title="Workforce"
            icon={
              <Users
                className="h-4 w-4 text-[var(--color-gray-500)]"
                aria-hidden="true"
              />
            }
            editing={editingSection === "workforce"}
            onEdit={() => startEdit("workforce")}
            onCancel={cancelEdit}
            onSave={saveSection}
            saving={saving}
          />
        }
      >
        {editingSection === "workforce" ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <AppInput
                label="Local Citizens"
                variant="number"
                value={String(editDraft.headcount_local ?? 0)}
                onChange={(e) =>
                  handleDraftChange(
                    "headcount_local",
                    parseInt((e.target as HTMLInputElement).value) || 0,
                  )
                }
                min={0}
              />
              <AppInput
                label="Permanent Residents"
                variant="number"
                value={String(editDraft.headcount_pr ?? 0)}
                onChange={(e) =>
                  handleDraftChange(
                    "headcount_pr",
                    parseInt((e.target as HTMLInputElement).value) || 0,
                  )
                }
                min={0}
              />
              <AppInput
                label="Employment Pass (EP)"
                variant="number"
                value={String(editDraft.headcount_ep ?? 0)}
                onChange={(e) =>
                  handleDraftChange(
                    "headcount_ep",
                    parseInt((e.target as HTMLInputElement).value) || 0,
                  )
                }
                min={0}
              />
              <AppInput
                label="S Pass (SP)"
                variant="number"
                value={String(editDraft.headcount_sp ?? 0)}
                onChange={(e) =>
                  handleDraftChange(
                    "headcount_sp",
                    parseInt((e.target as HTMLInputElement).value) || 0,
                  )
                }
                min={0}
              />
              <AppInput
                label="Work Permit (WP)"
                variant="number"
                value={String(editDraft.headcount_wp ?? 0)}
                onChange={(e) =>
                  handleDraftChange(
                    "headcount_wp",
                    parseInt((e.target as HTMLInputElement).value) || 0,
                  )
                }
                min={0}
              />
            </div>
            <p className="text-xs text-[var(--color-gray-500)]">
              Total headcount and local ratio are computed automatically when
              you save.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <DisplayField
                label="Total Headcount"
                value={String(totalHeadcount)}
              />
              <DisplayField
                label="Local Citizens"
                value={String(profile.headcount_local)}
              />
              <DisplayField
                label="Permanent Residents"
                value={String(profile.headcount_pr)}
              />
              <DisplayField
                label="Employment Pass"
                value={String(profile.headcount_ep)}
              />
              <DisplayField
                label="S Pass"
                value={String(profile.headcount_sp)}
              />
              <DisplayField
                label="Work Permit"
                value={String(profile.headcount_wp)}
              />
            </dl>
            <div className="pt-2 border-t border-[var(--color-gray-100)]">
              <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
                Foreign Workers
              </p>
              <p className="text-xs text-[var(--color-gray-400)] mt-1">
                {hasForeignWorkers
                  ? `Yes - ${profile.headcount_ep + profile.headcount_sp + profile.headcount_wp} foreign workers across EP, SP, and WP categories.`
                  : "No foreign workers recorded. Update your workforce numbers if this has changed."}
              </p>
            </div>
          </div>
        )}
      </AppCard>

      {/* Contact Info Section - UEN edit */}
      <AppCard
        variant="standard"
        header={
          <SectionHeader
            title="Registration Details"
            icon={
              <Mail
                className="h-4 w-4 text-[var(--color-gray-500)]"
                aria-hidden="true"
              />
            }
            editing={editingSection === "contact"}
            onEdit={() => startEdit("contact")}
            onCancel={cancelEdit}
            onSave={saveSection}
            saving={saving}
          />
        }
      >
        {editingSection === "contact" ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="UEN"
              value={profile.uen ?? ""}
              disabled
              helperText="UEN cannot be changed after registration"
            />
          </div>
        ) : (
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <DisplayField label="UEN" value={profile.uen ?? "Not set"} />
            <DisplayField
              label="Status"
              value={profile.is_active ? "Active" : "Inactive"}
            />
          </dl>
        )}
      </AppCard>

      {/* Change History */}
      <AppCard
        variant="flat"
        header={
          <div className="flex items-center gap-2">
            <Clock
              className="h-4 w-4 text-[var(--color-gray-500)]"
              aria-hidden="true"
            />
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Change History
            </h2>
          </div>
        }
      >
        {changeHistory.length === 0 ? (
          <p className="text-sm text-[var(--color-gray-500)]">
            No changes recorded in this session.
          </p>
        ) : (
          <div className="space-y-3">
            {changeHistory.map((entry, i) => (
              <div
                key={`${entry.field}-${entry.date}-${i}`}
                className="flex items-start gap-3 py-2 border-b border-[var(--color-gray-100)] last:border-b-0"
              >
                <div
                  className="mt-1.5 h-2 w-2 rounded-full bg-[var(--color-primary)] shrink-0"
                  aria-hidden="true"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[var(--color-gray-900)]">
                    <span className="font-medium">{entry.field}</span> changed
                    from{" "}
                    <span className="text-[var(--color-gray-500)]">
                      {entry.oldValue}
                    </span>{" "}
                    to <span className="font-medium">{entry.newValue}</span>
                  </p>
                  <p className="text-xs text-[var(--color-gray-400)] mt-0.5">
                    {formatDate(entry.date)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </AppCard>
    </div>
  );
}
