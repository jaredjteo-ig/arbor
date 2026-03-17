"use client";

import { useState, useEffect, useCallback, useRef, use } from "react";
import Link from "next/link";
import {
  AppCard,
  AppButton,
  AppInput,
  toast,
} from "@/components/design-system";
import {
  ArrowLeft,
  User,
  DollarSign,
  Phone,
  FileText,
  Clock,
  Eye,
  EyeOff,
  Plus,
  X,
  Upload,
  Trash2,
  Shield,
  Building2,
  MapPin,
  Briefcase,
  CheckCircle2,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  employeesApi,
  type EmployeeDetail,
  type SalaryComponent,
  type EmergencyContact,
  type EmploymentEvent,
  type EmployeeDocument,
} from "@/services/api/employees";

/* ── Constants ──────────────────────────────────────────────── */

type TabKey = "profile" | "salary" | "contacts" | "documents" | "history";

const TABS: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: "profile", label: "Profile", icon: User },
  { key: "salary", label: "Salary", icon: DollarSign },
  { key: "contacts", label: "Emergency Contacts", icon: Phone },
  { key: "documents", label: "Documents", icon: FileText },
  { key: "history", label: "History", icon: Clock },
];

const CONFIRMATION_STYLES: Record<string, string> = {
  confirmed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  on_probation: "bg-amber-50 text-amber-700 border-amber-200",
  extended: "bg-orange-50 text-orange-700 border-orange-200",
};

/* ── Helper: profile completeness ──────────────────────────── */

const PROFILE_FIELDS: (keyof EmployeeDetail)[] = [
  "name",
  "email",
  "department",
  "designation",
  "employment_type",
  "start_date",
  "nationality",
  "date_of_birth",
  "gender",
  "nric_fin",
  "bank_name",
  "bank_account_number",
  "residential_address",
  "postal_code",
  "reporting_manager_id",
];

function computeCompleteness(emp: EmployeeDetail): number {
  let filled = 0;
  for (const key of PROFILE_FIELDS) {
    const val = emp[key];
    if (val !== null && val !== undefined && val !== "") filled++;
  }
  return Math.round((filled / PROFILE_FIELDS.length) * 100);
}

/* ── Helper: mask sensitive value ──────────────────────────── */

function maskValue(value: string | null | undefined, last4?: string): string {
  if (!value && !last4) return "-";
  if (last4) return `****${last4}`;
  if (!value) return "-";
  if (value.length <= 4) return value;
  return "*".repeat(value.length - 4) + value.slice(-4);
}

/* ── Skeleton loaders ──────────────────────────────────────── */

function ProfileSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="space-y-3">
          <div className="h-5 w-40 bg-[var(--color-gray-200)] rounded" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Array.from({ length: 4 }, (_, j) => (
              <div key={j} className="space-y-1.5">
                <div className="h-3.5 w-24 bg-[var(--color-gray-200)] rounded" />
                <div className="h-[44px] w-full bg-[var(--color-gray-100)] rounded-[8px]" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-3">
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-4 border border-[var(--color-gray-100)] rounded-[8px]"
        >
          <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* ── Confirmation badge ─────────────────────────────────────── */

function ConfirmationBadge({ status }: { status: string }) {
  const label = status
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${CONFIRMATION_STYLES[status] || "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]"}`}
    >
      {label}
    </span>
  );
}

/* ── Profile Tab ────────────────────────────────────────────── */

function ProfileTab({
  employee,
  isAdmin,
  onSave,
  isSaving,
}: {
  employee: EmployeeDetail;
  isAdmin: boolean;
  onSave: (data: Partial<EmployeeDetail>) => Promise<void>;
  isSaving: boolean;
}) {
  const [form, setForm] = useState<Partial<EmployeeDetail>>({});
  const [revealNric, setRevealNric] = useState(false);
  const [revealBank, setRevealBank] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    setForm({});
    setHasChanges(false);
  }, [employee]);

  function updateField(key: keyof EmployeeDetail, value: string | number) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  }

  function getVal(key: keyof EmployeeDetail): string {
    if (key in form) return String(form[key] ?? "");
    const val = employee[key];
    if (val === null || val === undefined) return "";
    return String(val);
  }

  async function handleSave() {
    if (!hasChanges) return;
    await onSave(form);
    setHasChanges(false);
  }

  const completeness = computeCompleteness({
    ...employee,
    ...form,
  } as EmployeeDetail);

  return (
    <div className="space-y-6">
      {/* Completeness bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
          <div
            className="h-full bg-[var(--color-primary)] rounded-full transition-all"
            style={{ width: `${completeness}%` }}
          />
        </div>
        <span className="text-xs font-medium text-[var(--color-gray-600)] whitespace-nowrap">
          {completeness}% complete
        </span>
      </div>

      {/* Personal Details */}
      <SectionCard title="Personal Details" icon={<User className="h-4 w-4" />}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <AppInput
            label="Full Name"
            value={getVal("name")}
            onChange={(e) => updateField("name", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Email"
            value={getVal("email")}
            onChange={(e) => updateField("email", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Date of Birth"
            value={getVal("date_of_birth")}
            onChange={(e) => updateField("date_of_birth", e.target.value)}
            placeholder="YYYY-MM-DD"
            disabled={!isAdmin}
          />
          <AppInput
            label="Gender"
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "male", label: "Male" },
              { value: "female", label: "Female" },
            ]}
            value={getVal("gender")}
            onChange={(e) => updateField("gender", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Marital Status"
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "single", label: "Single" },
              { value: "married", label: "Married" },
              { value: "divorced", label: "Divorced" },
              { value: "widowed", label: "Widowed" },
            ]}
            value={getVal("marital_status")}
            onChange={(e) => updateField("marital_status", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Race"
            value={getVal("race")}
            onChange={(e) => updateField("race", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Nationality"
            value={getVal("nationality")}
            onChange={(e) => updateField("nationality", e.target.value)}
            disabled={!isAdmin}
          />
        </div>
      </SectionCard>

      {/* Identity & Immigration */}
      <SectionCard
        title="Identity & Immigration"
        icon={<Shield className="h-4 w-4" />}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--color-gray-700)]">
              NRIC / FIN
            </label>
            <div className="flex items-center gap-2">
              <div className="flex-1 rounded-[8px] border px-3 py-2 text-base min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] flex items-center">
                {revealNric
                  ? getVal("nric_fin") || "-"
                  : maskValue(employee.nric_fin, employee.nric_fin_last4)}
              </div>
              <button
                type="button"
                onClick={() => setRevealNric(!revealNric)}
                className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                title={revealNric ? "Hide" : "Reveal"}
              >
                {revealNric ? (
                  <EyeOff className="h-4 w-4 text-[var(--color-gray-500)]" />
                ) : (
                  <Eye className="h-4 w-4 text-[var(--color-gray-500)]" />
                )}
              </button>
            </div>
          </div>
          <AppInput
            label="Pass Type"
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "citizen", label: "Citizen" },
              { value: "pr", label: "Permanent Resident" },
              { value: "ep", label: "Employment Pass" },
              { value: "sp", label: "S Pass" },
              { value: "wp", label: "Work Permit" },
              { value: "dp", label: "Dependant Pass" },
              { value: "ltvp", label: "LTVP" },
            ]}
            value={getVal("pass_type")}
            onChange={(e) => updateField("pass_type", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Work Pass Number"
            value={getVal("work_pass_number")}
            onChange={(e) => updateField("work_pass_number", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Work Pass Expiry"
            value={getVal("work_pass_expiry")}
            onChange={(e) => updateField("work_pass_expiry", e.target.value)}
            placeholder="YYYY-MM-DD"
            disabled={!isAdmin}
          />
          <AppInput
            label="Immigration Status"
            value={getVal("immigration_status")}
            onChange={(e) => updateField("immigration_status", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Immigration Effective Date"
            value={getVal("immigration_effective_date")}
            onChange={(e) =>
              updateField("immigration_effective_date", e.target.value)
            }
            placeholder="YYYY-MM-DD"
            disabled={!isAdmin}
          />
        </div>
      </SectionCard>

      {/* Banking */}
      <SectionCard
        title="Banking Details"
        icon={<Building2 className="h-4 w-4" />}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <AppInput
            label="Bank Name"
            value={getVal("bank_name")}
            onChange={(e) => updateField("bank_name", e.target.value)}
            disabled={!isAdmin}
          />
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--color-gray-700)]">
              Bank Account Number
            </label>
            <div className="flex items-center gap-2">
              <div className="flex-1 rounded-[8px] border px-3 py-2 text-base min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] flex items-center">
                {revealBank
                  ? getVal("bank_account_number") || "-"
                  : maskValue(
                      employee.bank_account_number,
                      employee.bank_account_last4,
                    )}
              </div>
              <button
                type="button"
                onClick={() => setRevealBank(!revealBank)}
                className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                title={revealBank ? "Hide" : "Reveal"}
              >
                {revealBank ? (
                  <EyeOff className="h-4 w-4 text-[var(--color-gray-500)]" />
                ) : (
                  <Eye className="h-4 w-4 text-[var(--color-gray-500)]" />
                )}
              </button>
            </div>
          </div>
          <AppInput
            label="Bank Code"
            value={getVal("bank_code")}
            onChange={(e) => updateField("bank_code", e.target.value)}
            disabled={!isAdmin}
          />
        </div>
      </SectionCard>

      {/* Address */}
      <SectionCard title="Address" icon={<MapPin className="h-4 w-4" />}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <AppInput
              label="Residential Address"
              value={getVal("residential_address")}
              onChange={(e) =>
                updateField("residential_address", e.target.value)
              }
              disabled={!isAdmin}
            />
          </div>
          <AppInput
            label="Postal Code"
            value={getVal("postal_code")}
            onChange={(e) => updateField("postal_code", e.target.value)}
            disabled={!isAdmin}
          />
        </div>
      </SectionCard>

      {/* Employment */}
      <SectionCard title="Employment" icon={<Briefcase className="h-4 w-4" />}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <AppInput
            label="Employee ID (Internal)"
            value={getVal("employee_id_internal")}
            onChange={(e) =>
              updateField("employee_id_internal", e.target.value)
            }
            disabled={!isAdmin}
          />
          <AppInput
            label="Department"
            value={getVal("department")}
            onChange={(e) => updateField("department", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Designation"
            value={getVal("designation")}
            onChange={(e) => updateField("designation", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Employment Type"
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "full_time", label: "Full Time" },
              { value: "part_time", label: "Part Time" },
              { value: "contract", label: "Contract" },
              { value: "intern", label: "Intern" },
            ]}
            value={getVal("employment_type")}
            onChange={(e) => updateField("employment_type", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Start Date"
            value={getVal("start_date")}
            onChange={(e) => updateField("start_date", e.target.value)}
            placeholder="YYYY-MM-DD"
            disabled={!isAdmin}
          />
          <AppInput
            label="End Date"
            value={getVal("end_date")}
            onChange={(e) => updateField("end_date", e.target.value)}
            placeholder="YYYY-MM-DD"
            disabled={!isAdmin}
          />
          <AppInput
            label="Monthly Salary"
            variant="number"
            value={getVal("salary_monthly")}
            onChange={(e) =>
              updateField("salary_monthly", parseFloat(e.target.value) || 0)
            }
            disabled={!isAdmin}
          />
          <AppInput
            label="Notice Period (days)"
            variant="number"
            value={getVal("notice_period_days")}
            onChange={(e) =>
              updateField(
                "notice_period_days",
                parseInt(e.target.value, 10) || 0,
              )
            }
            disabled={!isAdmin}
          />
        </div>
      </SectionCard>

      {/* Probation */}
      <SectionCard
        title="Probation"
        icon={<CheckCircle2 className="h-4 w-4" />}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <AppInput
            label="Probation Months"
            variant="number"
            value={getVal("probation_months")}
            onChange={(e) =>
              updateField("probation_months", parseInt(e.target.value, 10) || 0)
            }
            disabled={!isAdmin}
          />
          <AppInput
            label="Probation End Date"
            value={getVal("probation_end_date")}
            onChange={(e) => updateField("probation_end_date", e.target.value)}
            placeholder="YYYY-MM-DD"
            disabled={!isAdmin}
          />
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--color-gray-700)]">
              Confirmation Status
            </label>
            <div className="min-h-[44px] flex items-center">
              <ConfirmationBadge
                status={getVal("confirmation_status") || "on_probation"}
              />
            </div>
          </div>
        </div>
      </SectionCard>

      {/* Save button (admin only) */}
      {isAdmin && (
        <div className="flex justify-end gap-3 pt-2">
          <AppButton
            variant="primary"
            size="md"
            onClick={handleSave}
            loading={isSaving}
            disabled={!hasChanges}
          >
            Save Changes
          </AppButton>
        </div>
      )}
    </div>
  );
}

/* ── Section Card ───────────────────────────────────────────── */

function SectionCard({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <AppCard variant="standard">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-[var(--color-primary)]">{icon}</span>
        <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
          {title}
        </h3>
      </div>
      {children}
    </AppCard>
  );
}

/* ── Salary Tab ─────────────────────────────────────────────── */

function SalaryTab({
  employeeId,
  baseSalary,
  isAdmin,
}: {
  employeeId: number;
  baseSalary: number;
  isAdmin: boolean;
}) {
  const [components, setComponents] = useState<SalaryComponent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newComponent, setNewComponent] = useState({
    component_type: "allowance",
    name: "",
    amount: 0,
    frequency: "monthly",
    is_taxable: true,
    is_cpf_applicable: true,
    effective_from: "",
    effective_to: "",
    is_active: true,
  });

  const fetchComponents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await employeesApi.listSalaryComponents(employeeId);
      setComponents(data.components ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load salary components.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchComponents();
  }, [fetchComponents]);

  async function handleAddComponent(e: React.FormEvent) {
    e.preventDefault();
    if (!newComponent.name.trim()) return;

    setIsSubmitting(true);
    try {
      await employeesApi.createSalaryComponent(
        employeeId,
        newComponent as Omit<SalaryComponent, "id">,
      );
      toast.success("Salary component added");
      setShowAddForm(false);
      setNewComponent({
        component_type: "allowance",
        name: "",
        amount: 0,
        frequency: "monthly",
        is_taxable: true,
        is_cpf_applicable: true,
        effective_from: "",
        effective_to: "",
        is_active: true,
      });
      fetchComponents();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to add component";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeactivate(componentId: number) {
    try {
      await employeesApi.updateSalaryComponent(employeeId, componentId, {
        is_active: false,
      });
      toast.success("Component deactivated");
      fetchComponents();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to deactivate component";
      toast.error(message);
    }
  }

  if (isLoading) return <ListSkeleton />;
  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchComponents}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  const totalMonthly =
    baseSalary +
    components
      .filter((c) => c.is_active && c.frequency === "monthly")
      .reduce((sum, c) => sum + c.amount, 0);

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <AppCard variant="flat">
          <p className="text-xs text-[var(--color-gray-500)] mb-1">
            Base Monthly Salary
          </p>
          <p className="text-xl font-bold text-[var(--color-gray-900)]">
            ${baseSalary.toLocaleString()}
          </p>
        </AppCard>
        <AppCard variant="flat">
          <p className="text-xs text-[var(--color-gray-500)] mb-1">
            Total Monthly (incl. allowances)
          </p>
          <p className="text-xl font-bold text-[var(--color-primary)]">
            ${totalMonthly.toLocaleString()}
          </p>
        </AppCard>
      </div>

      {/* Components list */}
      <AppCard
        variant="standard"
        header={
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Salary Components
            </h3>
            {isAdmin && (
              <AppButton
                variant="outlined"
                size="sm"
                onClick={() => setShowAddForm(true)}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Component
              </AppButton>
            )}
          </div>
        }
      >
        {components.length === 0 ? (
          <p className="text-sm text-[var(--color-gray-500)] text-center py-4">
            No additional salary components configured.
          </p>
        ) : (
          <div className="space-y-2 -mx-1">
            {components.map((comp) => (
              <div
                key={comp.id}
                className={`flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg border ${
                  comp.is_active
                    ? "border-[var(--color-gray-200)] bg-white"
                    : "border-[var(--color-gray-100)] bg-[var(--color-gray-50)] opacity-60"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                    {comp.name}
                  </p>
                  <p className="text-xs text-[var(--color-gray-500)]">
                    {comp.component_type.replace(/_/g, " ")} &middot;{" "}
                    {comp.frequency}
                    {comp.is_taxable && " &middot; Taxable"}
                    {comp.is_cpf_applicable && " &middot; CPF"}
                  </p>
                </div>
                <div className="text-right flex items-center gap-2">
                  <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                    ${comp.amount.toLocaleString()}
                  </span>
                  {isAdmin && comp.is_active && (
                    <button
                      type="button"
                      onClick={() => handleDeactivate(comp.id)}
                      className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
                      title="Deactivate"
                    >
                      <X className="h-3.5 w-3.5 text-[var(--color-gray-400)]" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </AppCard>

      {/* Add component form */}
      {showAddForm && (
        <AppCard variant="elevated">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Add Salary Component
            </h3>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="p-1 rounded-lg hover:bg-[var(--color-gray-100)]"
            >
              <X className="h-4 w-4 text-[var(--color-gray-500)]" />
            </button>
          </div>
          <form onSubmit={handleAddComponent} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <AppInput
                label="Component Name"
                value={newComponent.name}
                onChange={(e) =>
                  setNewComponent({ ...newComponent, name: e.target.value })
                }
                placeholder="e.g. Transport Allowance"
              />
              <AppInput
                label="Type"
                variant="select"
                options={[
                  { value: "allowance", label: "Allowance" },
                  { value: "bonus", label: "Bonus" },
                  { value: "commission", label: "Commission" },
                  { value: "overtime", label: "Overtime" },
                  { value: "deduction", label: "Deduction" },
                ]}
                value={newComponent.component_type}
                onChange={(e) =>
                  setNewComponent({
                    ...newComponent,
                    component_type: e.target.value,
                  })
                }
              />
              <AppInput
                label="Amount"
                variant="number"
                value={String(newComponent.amount)}
                onChange={(e) =>
                  setNewComponent({
                    ...newComponent,
                    amount: parseFloat(e.target.value) || 0,
                  })
                }
              />
              <AppInput
                label="Frequency"
                variant="select"
                options={[
                  { value: "monthly", label: "Monthly" },
                  { value: "annual", label: "Annual" },
                  { value: "one_time", label: "One-time" },
                ]}
                value={newComponent.frequency}
                onChange={(e) =>
                  setNewComponent({
                    ...newComponent,
                    frequency: e.target.value,
                  })
                }
              />
              <AppInput
                label="Effective From"
                value={newComponent.effective_from}
                onChange={(e) =>
                  setNewComponent({
                    ...newComponent,
                    effective_from: e.target.value,
                  })
                }
                placeholder="YYYY-MM-DD"
              />
              <AppInput
                label="Effective To (optional)"
                value={newComponent.effective_to}
                onChange={(e) =>
                  setNewComponent({
                    ...newComponent,
                    effective_to: e.target.value,
                  })
                }
                placeholder="YYYY-MM-DD"
              />
            </div>
            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2 text-sm text-[var(--color-gray-700)]">
                <input
                  type="checkbox"
                  checked={newComponent.is_taxable}
                  onChange={(e) =>
                    setNewComponent({
                      ...newComponent,
                      is_taxable: e.target.checked,
                    })
                  }
                  className="rounded border-[var(--color-gray-300)]"
                />
                Taxable
              </label>
              <label className="flex items-center gap-2 text-sm text-[var(--color-gray-700)]">
                <input
                  type="checkbox"
                  checked={newComponent.is_cpf_applicable}
                  onChange={(e) =>
                    setNewComponent({
                      ...newComponent,
                      is_cpf_applicable: e.target.checked,
                    })
                  }
                  className="rounded border-[var(--color-gray-300)]"
                />
                CPF Applicable
              </label>
            </div>
            <div className="flex gap-3 justify-end pt-2">
              <AppButton
                type="button"
                variant="outlined"
                size="sm"
                onClick={() => setShowAddForm(false)}
              >
                Cancel
              </AppButton>
              <AppButton
                type="submit"
                variant="primary"
                size="sm"
                loading={isSubmitting}
              >
                Add Component
              </AppButton>
            </div>
          </form>
        </AppCard>
      )}
    </div>
  );
}

/* ── Emergency Contacts Tab ─────────────────────────────────── */

function ContactsTab({
  employeeId,
  isAdmin,
}: {
  employeeId: number;
  isAdmin: boolean;
}) {
  const [contacts, setContacts] = useState<EmergencyContact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newContact, setNewContact] = useState({
    name: "",
    relationship: "",
    phone_primary: "",
    phone_secondary: "",
    email: "",
    is_next_of_kin: false,
    priority: 1,
  });

  const fetchContacts = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await employeesApi.listEmergencyContacts(employeeId);
      setContacts(data.contacts ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load emergency contacts.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  async function handleAddContact(e: React.FormEvent) {
    e.preventDefault();
    if (!newContact.name.trim() || !newContact.phone_primary.trim()) return;

    setIsSubmitting(true);
    try {
      await employeesApi.createEmergencyContact(
        employeeId,
        newContact as Omit<EmergencyContact, "id">,
      );
      toast.success("Emergency contact added");
      setShowAddForm(false);
      setNewContact({
        name: "",
        relationship: "",
        phone_primary: "",
        phone_secondary: "",
        email: "",
        is_next_of_kin: false,
        priority: 1,
      });
      fetchContacts();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to add contact";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) return <ListSkeleton />;
  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchContacts}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
          Emergency Contacts ({contacts.length})
        </h3>
        {isAdmin && (
          <AppButton
            variant="outlined"
            size="sm"
            onClick={() => setShowAddForm(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Contact
          </AppButton>
        )}
      </div>

      {contacts.length === 0 ? (
        <AppCard variant="standard">
          <p className="text-sm text-[var(--color-gray-500)] text-center py-6">
            No emergency contacts on file.
          </p>
        </AppCard>
      ) : (
        <div className="space-y-3">
          {contacts.map((contact) => (
            <AppCard key={contact.id} variant="standard">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-[var(--color-gray-900)]">
                      {contact.name}
                    </p>
                    {contact.is_next_of_kin && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-[var(--color-primary-bg)] text-[var(--color-primary)] font-medium">
                        Next of Kin
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                    {contact.relationship}
                  </p>
                </div>
                <div className="text-right text-sm">
                  <p className="text-[var(--color-gray-700)]">
                    {contact.phone_primary}
                  </p>
                  {contact.email && (
                    <p className="text-xs text-[var(--color-gray-500)]">
                      {contact.email}
                    </p>
                  )}
                </div>
              </div>
            </AppCard>
          ))}
        </div>
      )}

      {/* Add contact form */}
      {showAddForm && (
        <AppCard variant="elevated">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Add Emergency Contact
            </h3>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="p-1 rounded-lg hover:bg-[var(--color-gray-100)]"
            >
              <X className="h-4 w-4 text-[var(--color-gray-500)]" />
            </button>
          </div>
          <form onSubmit={handleAddContact} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <AppInput
                label="Name"
                value={newContact.name}
                onChange={(e) =>
                  setNewContact({ ...newContact, name: e.target.value })
                }
                placeholder="Contact full name"
              />
              <AppInput
                label="Relationship"
                value={newContact.relationship}
                onChange={(e) =>
                  setNewContact({
                    ...newContact,
                    relationship: e.target.value,
                  })
                }
                placeholder="e.g. Spouse, Parent"
              />
              <AppInput
                label="Primary Phone"
                value={newContact.phone_primary}
                onChange={(e) =>
                  setNewContact({
                    ...newContact,
                    phone_primary: e.target.value,
                  })
                }
                placeholder="+65 XXXX XXXX"
              />
              <AppInput
                label="Secondary Phone (optional)"
                value={newContact.phone_secondary}
                onChange={(e) =>
                  setNewContact({
                    ...newContact,
                    phone_secondary: e.target.value,
                  })
                }
                placeholder="+65 XXXX XXXX"
              />
              <AppInput
                label="Email (optional)"
                value={newContact.email}
                onChange={(e) =>
                  setNewContact({ ...newContact, email: e.target.value })
                }
                placeholder="contact@example.com"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-[var(--color-gray-700)]">
              <input
                type="checkbox"
                checked={newContact.is_next_of_kin}
                onChange={(e) =>
                  setNewContact({
                    ...newContact,
                    is_next_of_kin: e.target.checked,
                  })
                }
                className="rounded border-[var(--color-gray-300)]"
              />
              Next of Kin
            </label>
            <div className="flex gap-3 justify-end pt-2">
              <AppButton
                type="button"
                variant="outlined"
                size="sm"
                onClick={() => setShowAddForm(false)}
              >
                Cancel
              </AppButton>
              <AppButton
                type="submit"
                variant="primary"
                size="sm"
                loading={isSubmitting}
              >
                Add Contact
              </AppButton>
            </div>
          </form>
        </AppCard>
      )}
    </div>
  );
}

/* ── Documents Tab ──────────────────────────────────────────── */

function DocumentsTab({
  employeeId,
  isAdmin,
}: {
  employeeId: number;
  isAdmin: boolean;
}) {
  const [documents, setDocuments] = useState<EmployeeDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await employeesApi.listDocuments(employeeId);
      setDocuments(data.documents ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load documents.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;

    setIsUploading(true);
    try {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append("file", file);
        await employeesApi.uploadDocument(employeeId, formData);
      }
      toast.success(
        files.length === 1
          ? "Document uploaded"
          : `${files.length} documents uploaded`,
      );
      fetchDocuments();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to upload document";
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDelete(docId: number) {
    try {
      await employeesApi.deleteDocument(employeeId, docId);
      toast.success("Document deleted");
      fetchDocuments();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to delete document";
      toast.error(message);
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

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  if (isLoading) return <ListSkeleton />;
  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchDocuments}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  return (
    <div className="space-y-4">
      {/* Upload area */}
      {isAdmin && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-[12px] p-8 text-center transition-colors cursor-pointer ${
            isDragOver
              ? "border-[var(--color-primary)] bg-[var(--color-primary-bg)]"
              : "border-[var(--color-gray-200)] hover:border-[var(--color-gray-300)]"
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="h-8 w-8 text-[var(--color-gray-400)] mx-auto mb-2" />
          <p className="text-sm text-[var(--color-gray-600)]">
            {isUploading
              ? "Uploading..."
              : "Drop files here or click to upload"}
          </p>
          <p className="text-xs text-[var(--color-gray-400)] mt-1">
            PDF, images, or office documents up to 10MB
          </p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleUpload(e.target.files)}
          />
        </div>
      )}

      {/* Document list */}
      {documents.length === 0 ? (
        <AppCard variant="standard">
          <p className="text-sm text-[var(--color-gray-500)] text-center py-6">
            No documents uploaded yet.
          </p>
        </AppCard>
      ) : (
        <div className="space-y-2">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between gap-3 px-4 py-3 rounded-[8px] border border-[var(--color-gray-200)] bg-white"
            >
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <FileText className="h-5 w-5 text-[var(--color-gray-400)] shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                    {doc.file_name}
                  </p>
                  <p className="text-xs text-[var(--color-gray-500)]">
                    {doc.document_type.replace(/_/g, " ")} &middot;{" "}
                    {formatFileSize(doc.file_size)}
                    {doc.is_confidential && (
                      <span className="ml-1.5 text-amber-600 font-medium">
                        Confidential
                      </span>
                    )}
                  </p>
                </div>
              </div>
              {isAdmin && (
                <button
                  type="button"
                  onClick={() => handleDelete(doc.id)}
                  className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                  title="Delete document"
                >
                  <Trash2 className="h-4 w-4 text-[var(--color-gray-400)]" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── History Tab ────────────────────────────────────────────── */

function HistoryTab({ employeeId }: { employeeId: number }) {
  const [events, setEvents] = useState<EmploymentEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await employeesApi.listEmploymentHistory(employeeId);
      setEvents(data.events ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load employment history.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  if (isLoading) return <ListSkeleton rows={4} />;
  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchHistory}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  if (events.length === 0) {
    return (
      <AppCard variant="standard">
        <p className="text-sm text-[var(--color-gray-500)] text-center py-6">
          No employment events recorded.
        </p>
      </AppCard>
    );
  }

  return (
    <div className="relative pl-6">
      {/* Timeline line */}
      <div className="absolute left-2.5 top-2 bottom-2 w-px bg-[var(--color-gray-200)]" />

      <div className="space-y-4">
        {events.map((event) => (
          <div key={event.id} className="relative">
            {/* Timeline dot */}
            <div className="absolute -left-6 top-1.5 w-5 h-5 rounded-full bg-[var(--color-primary-bg)] border-2 border-[var(--color-primary)] flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-[var(--color-primary)]" />
            </div>

            <AppCard variant="flat">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-[var(--color-gray-900)]">
                    {event.event_type
                      .replace(/_/g, " ")
                      .replace(/\b\w/g, (c) => c.toUpperCase())}
                  </p>
                  <p className="text-sm text-[var(--color-gray-600)] mt-0.5">
                    {event.description}
                  </p>
                  {event.notes && (
                    <p className="text-xs text-[var(--color-gray-500)] mt-1 italic">
                      {event.notes}
                    </p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs font-medium text-[var(--color-gray-600)]">
                    {event.event_date}
                  </p>
                  {event.effective_date &&
                    event.effective_date !== event.event_date && (
                      <p className="text-xs text-[var(--color-gray-400)] mt-0.5">
                        Effective: {event.effective_date}
                      </p>
                    )}
                </div>
              </div>
            </AppCard>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────── */

interface EmployeeDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function EmployeeDetailPage({
  params,
}: EmployeeDetailPageProps) {
  const { id } = use(params);
  const employeeId = Number(id);
  const { user } = useAuth();

  const isAdmin = user?.role === "owner" || user?.role === "hr_manager";

  const [activeTab, setActiveTab] = useState<TabKey>("profile");
  const [employee, setEmployee] = useState<EmployeeDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const fetchEmployee = useCallback(async () => {
    if (!employeeId || isNaN(employeeId)) {
      setError("Invalid employee ID");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await employeesApi.getEmployee(employeeId);
      setEmployee(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load employee details.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchEmployee();
  }, [fetchEmployee]);

  const handleSaveProfile = useCallback(
    async (data: Partial<EmployeeDetail>) => {
      setIsSaving(true);
      try {
        const updated = await employeesApi.updateEmployee(employeeId, data);
        setEmployee(updated);
        toast.success("Employee profile updated");
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Failed to save changes";
        toast.error(message);
      } finally {
        setIsSaving(false);
      }
    },
    [employeeId],
  );

  /* ── Loading state ──────────────────────────────────────── */

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <Link
          href="/employees"
          className="inline-flex items-center gap-1.5 text-sm text-[var(--color-primary)] hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Employees
        </Link>
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-64 bg-[var(--color-gray-200)] rounded" />
          <div className="h-5 w-48 bg-[var(--color-gray-100)] rounded" />
          <div className="h-10 w-full bg-[var(--color-gray-100)] rounded-[8px]" />
        </div>
        <ProfileSkeleton />
      </div>
    );
  }

  /* ── Error state ────────────────────────────────────────── */

  if (error || !employee) {
    return (
      <div className="max-w-4xl mx-auto space-y-4 pb-8">
        <Link
          href="/employees"
          className="inline-flex items-center gap-1.5 text-sm text-[var(--color-primary)] hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Employees
        </Link>
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">
              {error || "Employee not found."}
            </p>
            <AppButton variant="outlined" size="sm" onClick={fetchEmployee}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      </div>
    );
  }

  /* ── Main render ────────────────────────────────────────── */

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Back link */}
      <Link
        href="/employees"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-primary)] hover:underline"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Employees
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-[var(--color-primary-bg)] shrink-0 mt-0.5">
            <User
              className="h-6 w-6 text-[var(--color-primary)]"
              aria-hidden="true"
            />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              {employee.name}
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              {employee.designation || employee.department}{" "}
              {employee.employee_id_internal &&
                `(${employee.employee_id_internal})`}
            </p>
            <div className="flex items-center gap-2 mt-1.5">
              <ConfirmationBadge
                status={employee.confirmation_status || "on_probation"}
              />
              {!employee.is_active && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]">
                  Inactive
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="border-b border-[var(--color-gray-200)] overflow-x-auto">
        <nav className="flex -mb-px" aria-label="Employee detail tabs">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors min-h-[44px] ${
                  isActive
                    ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                    : "border-transparent text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] hover:border-[var(--color-gray-300)]"
                }`}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === "profile" && (
        <ProfileTab
          employee={employee}
          isAdmin={isAdmin}
          onSave={handleSaveProfile}
          isSaving={isSaving}
        />
      )}
      {activeTab === "salary" && (
        <SalaryTab
          employeeId={employeeId}
          baseSalary={employee.salary_monthly || 0}
          isAdmin={isAdmin}
        />
      )}
      {activeTab === "contacts" && (
        <ContactsTab employeeId={employeeId} isAdmin={isAdmin} />
      )}
      {activeTab === "documents" && (
        <DocumentsTab employeeId={employeeId} isAdmin={isAdmin} />
      )}
      {activeTab === "history" && <HistoryTab employeeId={employeeId} />}
    </div>
  );
}
