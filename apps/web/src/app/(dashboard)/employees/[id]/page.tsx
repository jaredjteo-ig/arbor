"use client";

import { useState, useEffect, useCallback, useRef, use } from "react";
import Link from "next/link";
import {
  AppCard,
  AppButton,
  AppInput,
  DatePicker,
  EmployeePicker,
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
  Calendar,
  StickyNote,
  ClipboardCheck,
  Settings,
  Award,
  LayoutDashboard,
  Lock,
  AlertTriangle,
  TrendingUp,
  Edit,
  Filter,
  Users,
  HelpCircle,
  CalendarDays,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  employeesApi,
  type EmployeeDetail,
  type SalaryComponent,
  type EmergencyContact,
  type EmploymentEvent,
  type EmployeeDocument,
  type EmployeeNote,
  type EmployeeSkill,
  type CustomFieldDefinition,
  type CustomFieldValue,
  type AdminLeaveBalance,
  type FamilyMember,
} from "@/services/api/employees";
import { policiesApi } from "@/services/api/policies";

/* ── Constants ──────────────────────────────────────────────── */

type TabKey =
  | "overview"
  | "personal"
  | "employment"
  | "compensation"
  | "statutory"
  | "leave"
  | "documents"
  | "timeline"
  | "notes"
  | "onboarding"
  | "custom_fields"
  | "skills";

const TABS: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "personal", label: "Personal", icon: User },
  { key: "employment", label: "Employment", icon: Briefcase },
  { key: "compensation", label: "Compensation", icon: DollarSign },
  { key: "statutory", label: "Statutory", icon: Shield },
  { key: "leave", label: "Leave", icon: Calendar },
  { key: "documents", label: "Documents", icon: FileText },
  { key: "timeline", label: "Timeline", icon: Clock },
  { key: "notes", label: "Notes", icon: StickyNote },
  { key: "onboarding", label: "Onboarding", icon: ClipboardCheck },
  { key: "custom_fields", label: "Custom Fields", icon: Settings },
  { key: "skills", label: "Skills", icon: Award },
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

/* ── Helper: expiry badge ──────────────────────────────────── */

function getExpiryBadge(
  expiryDate?: string,
): { label: string; className: string } | null {
  if (!expiryDate) return null;
  const days = Math.ceil(
    (new Date(expiryDate).getTime() - Date.now()) / 86400000,
  );
  if (days < 0)
    return { label: "Expired", className: "bg-red-100 text-red-700" };
  if (days < 30)
    return {
      label: `${days}d left`,
      className: "bg-red-100 text-red-700",
    };
  if (days < 90)
    return {
      label: `${days}d left`,
      className: "bg-amber-100 text-amber-700",
    };
  return {
    label: `${days}d left`,
    className: "bg-emerald-100 text-emerald-700",
  };
}

/* ── Helper: tenure calculation ────────────────────────────── */

function computeTenure(startDate: string): string {
  if (!startDate) return "-";
  const start = new Date(startDate);
  const now = new Date();
  let years = now.getFullYear() - start.getFullYear();
  let months = now.getMonth() - start.getMonth();
  if (months < 0) {
    years--;
    months += 12;
  }
  if (years === 0 && months === 0) return "Less than a month";
  const parts: string[] = [];
  if (years > 0) parts.push(`${years} year${years > 1 ? "s" : ""}`);
  if (months > 0) parts.push(`${months} month${months > 1 ? "s" : ""}`);
  return parts.join(", ");
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

function GridSkeleton() {
  return (
    <div className="animate-pulse grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className="h-24 bg-[var(--color-gray-100)] rounded-[12px]"
        />
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

/* ── Overview Tab ──────────────────────────────────────────── */

function OverviewTab({
  employee,
  isAdmin,
  leaveBalances,
  onAction,
}: {
  employee: EmployeeDetail;
  isAdmin: boolean;
  leaveBalances: AdminLeaveBalance[];
  onAction: (action: string) => void;
}) {
  const completeness = computeCompleteness(employee);
  const tenure = computeTenure(employee.start_date);

  const annualBalance = leaveBalances.find(
    (b) => b.leave_type.toLowerCase() === "annual",
  );
  const leaveRemaining = annualBalance
    ? annualBalance.entitlement_days -
      annualBalance.used_days -
      annualBalance.pending_days
    : null;

  const workPassExpiry = getExpiryBadge(employee.work_pass_expiry);
  const workPassDaysLeft = employee.work_pass_expiry
    ? Math.ceil(
        (new Date(employee.work_pass_expiry).getTime() - Date.now()) / 86400000,
      )
    : null;

  return (
    <div className="space-y-6">
      {/* Employee summary card */}
      <AppCard variant="standard">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-[var(--color-primary-bg)] flex items-center justify-center shrink-0">
            <User className="h-8 w-8 text-[var(--color-primary)]" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-bold text-[var(--color-gray-900)] truncate">
              {employee.name}
            </h2>
            <p className="text-sm text-[var(--color-gray-500)]">
              {employee.department}
              {employee.designation ? ` - ${employee.designation}` : ""}
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
      </AppCard>

      {/* Metrics grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <AppCard variant="flat">
          <p className="text-xs text-[var(--color-gray-500)] mb-1">Tenure</p>
          <p className="text-lg font-bold text-[var(--color-gray-900)]">
            {tenure}
          </p>
          <p className="text-xs text-[var(--color-gray-400)] mt-0.5">
            Since {employee.start_date || "-"}
          </p>
        </AppCard>

        <AppCard variant="flat">
          <p className="text-xs text-[var(--color-gray-500)] mb-1">
            Leave Balance
          </p>
          <p className="text-lg font-bold text-[var(--color-gray-900)]">
            {leaveRemaining !== null ? `${leaveRemaining} days` : "-"}
          </p>
          <p className="text-xs text-[var(--color-gray-400)] mt-0.5">
            {annualBalance ? "Annual leave remaining" : "No data"}
          </p>
        </AppCard>

        <AppCard variant="flat">
          <p className="text-xs text-[var(--color-gray-500)] mb-1">
            Monthly Salary
          </p>
          <p className="text-lg font-bold text-[var(--color-gray-900)]">
            {employee.salary_monthly
              ? `$${employee.salary_monthly.toLocaleString()}`
              : "-"}
          </p>
          <p className="text-xs text-[var(--color-gray-400)] mt-0.5">
            Base salary
          </p>
        </AppCard>

        <AppCard variant="flat">
          <p className="text-xs text-[var(--color-gray-500)] mb-1">
            Profile Completeness
          </p>
          <p className="text-lg font-bold text-[var(--color-gray-900)]">
            {completeness}%
          </p>
          <div className="mt-1.5 h-1.5 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--color-primary)] rounded-full transition-all"
              style={{ width: `${completeness}%` }}
            />
          </div>
        </AppCard>
      </div>

      {/* Work pass warning */}
      {workPassDaysLeft !== null && workPassDaysLeft < 90 && (
        <AppCard variant="standard">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-[var(--color-gray-900)]">
                Work Pass Expiring Soon
              </p>
              <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                {employee.pass_type && `${employee.pass_type.toUpperCase()} - `}
                Expires {employee.work_pass_expiry}
                {workPassExpiry && (
                  <span
                    className={`ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${workPassExpiry.className}`}
                  >
                    {workPassExpiry.label}
                  </span>
                )}
              </p>
            </div>
          </div>
        </AppCard>
      )}

      {/* Probation info */}
      {employee.confirmation_status !== "confirmed" &&
        employee.probation_end_date && (
          <AppCard variant="standard">
            <div className="flex items-center gap-3">
              <Clock className="h-5 w-5 text-amber-500 shrink-0" />
              <div>
                <p className="text-sm font-medium text-[var(--color-gray-900)]">
                  On Probation
                </p>
                <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                  {employee.probation_months} months probation - ends{" "}
                  {employee.probation_end_date}
                </p>
              </div>
            </div>
          </AppCard>
        )}

      {/* Quick actions */}
      {isAdmin && (
        <SectionCard
          title="Quick Actions"
          icon={<TrendingUp className="h-4 w-4" />}
        >
          <div className="flex flex-wrap gap-2">
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => onAction("edit_employment")}
            >
              <Edit className="h-3.5 w-3.5 mr-1.5" />
              Edit Employment
            </AppButton>
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => onAction("edit_compensation")}
            >
              <DollarSign className="h-3.5 w-3.5 mr-1.5" />
              Edit Compensation
            </AppButton>
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => onAction("edit_statutory")}
            >
              <Shield className="h-3.5 w-3.5 mr-1.5" />
              Edit Statutory
            </AppButton>
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => onAction("run_payroll")}
            >
              <TrendingUp className="h-3.5 w-3.5 mr-1.5" />
              Run Payroll
            </AppButton>
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => onAction("generate_payslip")}
            >
              <FileText className="h-3.5 w-3.5 mr-1.5" />
              Generate Payslip
            </AppButton>
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => onAction("terminate")}
              className="text-red-600 border-red-200 hover:bg-red-50"
            >
              <X className="h-3.5 w-3.5 mr-1.5" />
              Terminate
            </AppButton>
          </div>
        </SectionCard>
      )}
    </div>
  );
}

/* ── Personal Tab ──────────────────────────────────────────── */

function PersonalTab({
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
          <DatePicker
            label="Date of Birth"
            value={getVal("date_of_birth")}
            onChange={(v) => updateField("date_of_birth", v)}
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
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "chinese", label: "Chinese" },
              { value: "malay", label: "Malay" },
              { value: "indian", label: "Indian" },
              { value: "eurasian", label: "Eurasian" },
              { value: "other", label: "Other" },
            ]}
            value={getVal("race")}
            onChange={(e) => updateField("race", e.target.value)}
            disabled={!isAdmin}
          />
          <AppInput
            label="Nationality"
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "Singaporean", label: "Singaporean" },
              { value: "Malaysian", label: "Malaysian" },
              { value: "Indonesian", label: "Indonesian" },
              { value: "Thai", label: "Thai" },
              { value: "Japanese", label: "Japanese" },
              { value: "Chinese", label: "Chinese" },
              { value: "Indian", label: "Indian" },
              { value: "Filipino", label: "Filipino" },
              { value: "Vietnamese", label: "Vietnamese" },
              { value: "Myanmar", label: "Myanmar" },
              { value: "Other", label: "Other" },
            ]}
            value={getVal("nationality")}
            onChange={(e) => updateField("nationality", e.target.value)}
            disabled={!isAdmin}
          />
        </div>
      </SectionCard>

      {/* Identity (NRIC only) */}
      <SectionCard title="Identity" icon={<Shield className="h-4 w-4" />}>
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

      {/* Emergency Contacts inline */}
      <ContactsInline employeeId={employee.id} isAdmin={isAdmin} />

      {/* Family Members inline */}
      <FamilyMembersInline employeeId={employee.id} isAdmin={isAdmin} />

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

/* ── Contacts Inline (used inside Personal tab) ────────────── */

function ContactsInline({
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

  return (
    <SectionCard
      title="Emergency Contacts"
      icon={<Phone className="h-4 w-4" />}
    >
      {isLoading ? (
        <ListSkeleton rows={2} />
      ) : error ? (
        <div className="py-4 text-center">
          <p className="text-sm text-[var(--color-error)] mb-2">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchContacts}>
            Try again
          </AppButton>
        </div>
      ) : (
        <div className="space-y-3">
          {contacts.length === 0 && (
            <p className="text-sm text-[var(--color-gray-500)] text-center py-3">
              No emergency contacts on file.
            </p>
          )}
          {contacts.map((contact) => (
            <div
              key={contact.id}
              className="flex items-start justify-between gap-3 px-3 py-2.5 rounded-lg border border-[var(--color-gray-200)] bg-white"
            >
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
          ))}
          {isAdmin && !showAddForm && (
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => setShowAddForm(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Contact
            </AppButton>
          )}
          {showAddForm && (
            <form onSubmit={handleAddContact} className="space-y-3 pt-2">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
              <div className="flex gap-3 justify-end">
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
          )}
        </div>
      )}
    </SectionCard>
  );
}

/* ── Family Members Inline (used inside Personal tab) ────────── */

function FamilyMembersInline({
  employeeId,
  isAdmin,
}: {
  employeeId: number;
  isAdmin: boolean;
}) {
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const [newMember, setNewMember] = useState({
    name: "",
    relationship: "",
    date_of_birth: "",
    gender: "",
    citizenship_status: "",
  });

  const fetchMembers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await employeesApi.listFamilyMembers(employeeId);
      setMembers(data.family_members ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load family members.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  function resetForm() {
    setNewMember({
      name: "",
      relationship: "",
      date_of_birth: "",
      gender: "",
      citizenship_status: "",
    });
  }

  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault();
    if (!newMember.name.trim() || !newMember.relationship.trim()) return;

    setIsSubmitting(true);
    try {
      await employeesApi.createFamilyMember(employeeId, newMember);
      toast.success("Family member added");
      setShowAddForm(false);
      resetForm();
      fetchMembers();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to add family member";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleUpdateMember(memberId: number) {
    setIsSubmitting(true);
    try {
      await employeesApi.updateFamilyMember(employeeId, memberId, newMember);
      toast.success("Family member updated");
      setEditingId(null);
      resetForm();
      fetchMembers();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to update family member";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteMember(memberId: number) {
    try {
      await employeesApi.deleteFamilyMember(employeeId, memberId);
      toast.success("Family member removed");
      fetchMembers();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to remove family member";
      toast.error(message);
    }
  }

  function startEdit(member: FamilyMember) {
    setEditingId(member.id);
    setNewMember({
      name: member.name,
      relationship: member.relationship,
      date_of_birth: member.date_of_birth || "",
      gender: member.gender || "",
      citizenship_status: member.citizenship_status || "",
    });
    setShowAddForm(false);
  }

  function cancelEdit() {
    setEditingId(null);
    resetForm();
  }

  const memberForm = (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <AppInput
        label="Name"
        value={newMember.name}
        onChange={(e) => setNewMember({ ...newMember, name: e.target.value })}
        placeholder="Full name"
      />
      <AppInput
        label="Relationship"
        variant="select"
        options={[
          { value: "", label: "Select..." },
          { value: "spouse", label: "Spouse" },
          { value: "child", label: "Child" },
          { value: "parent", label: "Parent" },
          { value: "sibling", label: "Sibling" },
          { value: "other", label: "Other" },
        ]}
        value={newMember.relationship}
        onChange={(e) =>
          setNewMember({ ...newMember, relationship: e.target.value })
        }
      />
      <DatePicker
        label="Date of Birth"
        value={newMember.date_of_birth}
        onChange={(v) => setNewMember({ ...newMember, date_of_birth: v })}
      />
      <AppInput
        label="Gender"
        variant="select"
        options={[
          { value: "", label: "Select..." },
          { value: "male", label: "Male" },
          { value: "female", label: "Female" },
        ]}
        value={newMember.gender}
        onChange={(e) => setNewMember({ ...newMember, gender: e.target.value })}
      />
      <AppInput
        label="Citizenship Status"
        variant="select"
        options={[
          { value: "", label: "Select..." },
          { value: "citizen", label: "Citizen" },
          { value: "pr", label: "Permanent Resident" },
          { value: "foreigner", label: "Foreigner" },
        ]}
        value={newMember.citizenship_status}
        onChange={(e) =>
          setNewMember({ ...newMember, citizenship_status: e.target.value })
        }
      />
    </div>
  );

  return (
    <SectionCard title="Family Members" icon={<Users className="h-4 w-4" />}>
      {/* Info tooltip */}
      <div className="relative inline-flex items-center gap-1.5 mb-3">
        <button
          type="button"
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          onClick={() => setShowTooltip(!showTooltip)}
          className="inline-flex items-center gap-1 text-xs text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] transition-colors"
        >
          <HelpCircle className="h-3.5 w-3.5" />
          Why do we need this?
        </button>
        {showTooltip && (
          <div className="absolute left-0 top-full mt-1 z-10 w-64 p-2.5 rounded-lg bg-[var(--color-gray-900)] text-white text-xs leading-relaxed shadow-lg">
            Family member information is used to determine leave eligibility
            (e.g., childcare leave, maternity leave) and statutory benefits.
          </div>
        )}
      </div>

      {isLoading ? (
        <ListSkeleton rows={2} />
      ) : error ? (
        <div className="py-4 text-center">
          <p className="text-sm text-[var(--color-error)] mb-2">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchMembers}>
            Try again
          </AppButton>
        </div>
      ) : (
        <div className="space-y-3">
          {members.length === 0 && !showAddForm && (
            <p className="text-sm text-[var(--color-gray-500)] text-center py-3">
              No family members on file.
            </p>
          )}
          {members.map((member) => {
            if (editingId === member.id) {
              return (
                <form
                  key={member.id}
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleUpdateMember(member.id);
                  }}
                  className="space-y-3 p-3 rounded-lg border border-[var(--color-primary)] bg-[var(--color-primary-bg)]"
                >
                  {memberForm}
                  <div className="flex gap-3 justify-end">
                    <AppButton
                      type="button"
                      variant="outlined"
                      size="sm"
                      onClick={cancelEdit}
                    >
                      Cancel
                    </AppButton>
                    <AppButton
                      type="submit"
                      variant="primary"
                      size="sm"
                      loading={isSubmitting}
                    >
                      Save
                    </AppButton>
                  </div>
                </form>
              );
            }

            return (
              <div
                key={member.id}
                className="flex items-start justify-between gap-3 px-3 py-2.5 rounded-lg border border-[var(--color-gray-200)] bg-white"
              >
                <div>
                  <p className="text-sm font-medium text-[var(--color-gray-900)]">
                    {member.name}
                  </p>
                  <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                    {member.relationship
                      .replace(/_/g, " ")
                      .replace(/\b\w/g, (c) => c.toUpperCase())}
                    {member.gender &&
                      ` \u00b7 ${member.gender.charAt(0).toUpperCase() + member.gender.slice(1)}`}
                    {member.date_of_birth &&
                      ` \u00b7 Born ${member.date_of_birth}`}
                  </p>
                  {member.citizenship_status && (
                    <span className="inline-flex items-center mt-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-600)]">
                      {member.citizenship_status === "pr"
                        ? "PR"
                        : member.citizenship_status
                            .replace(/_/g, " ")
                            .replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                  )}
                </div>
                {isAdmin && (
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => startEdit(member)}
                      className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
                      title="Edit"
                    >
                      <Edit className="h-3.5 w-3.5 text-[var(--color-gray-400)]" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteMember(member.id)}
                      className="p-1.5 rounded-lg hover:bg-red-50 transition-colors"
                      title="Remove"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-[var(--color-gray-400)] hover:text-red-500" />
                    </button>
                  </div>
                )}
              </div>
            );
          })}
          {isAdmin && !showAddForm && editingId === null && (
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => {
                resetForm();
                setShowAddForm(true);
              }}
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Family Member
            </AppButton>
          )}
          {showAddForm && (
            <form onSubmit={handleAddMember} className="space-y-3 pt-2">
              {memberForm}
              <div className="flex gap-3 justify-end">
                <AppButton
                  type="button"
                  variant="outlined"
                  size="sm"
                  onClick={() => {
                    setShowAddForm(false);
                    resetForm();
                  }}
                >
                  Cancel
                </AppButton>
                <AppButton
                  type="submit"
                  variant="primary"
                  size="sm"
                  loading={isSubmitting}
                >
                  Add Family Member
                </AppButton>
              </div>
            </form>
          )}
        </div>
      )}
    </SectionCard>
  );
}

/* ── Employment Tab ────────────────────────────────────────── */

function EmploymentTab({
  employee,
  employeeId,
  isAdmin,
  onSave,
  isSaving,
  onOpenModal,
}: {
  employee: EmployeeDetail;
  employeeId: number;
  isAdmin: boolean;
  onSave: (data: Partial<EmployeeDetail>) => Promise<void>;
  isSaving: boolean;
  onOpenModal: (modal: ModalType) => void;
}) {
  const [form, setForm] = useState<Partial<EmployeeDetail>>({});
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

  function handleConfirmEmployee() {
    onOpenModal("confirm");
  }

  return (
    <div className="space-y-6">
      {/* Employment Details */}
      <SectionCard
        title="Employment Details"
        icon={<Briefcase className="h-4 w-4" />}
      >
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
          <DatePicker
            label="Start Date"
            value={getVal("start_date")}
            onChange={(v) => updateField("start_date", v)}
            disabled={!isAdmin}
          />
          <DatePicker
            label="End Date"
            value={getVal("end_date")}
            onChange={(v) => updateField("end_date", v)}
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
          <EmployeePicker
            label="Reporting Manager"
            value={
              getVal("reporting_manager_id")
                ? Number(getVal("reporting_manager_id"))
                : null
            }
            onChange={(id) => updateField("reporting_manager_id", id || 0)}
            disabled={!isAdmin}
            excludeIds={employee?.id ? [employee.id] : []}
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
          <DatePicker
            label="Probation End Date"
            value={getVal("probation_end_date")}
            onChange={(v) => updateField("probation_end_date", v)}
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
        {isAdmin && employee.confirmation_status !== "confirmed" && (
          <div className="flex gap-3 mt-4 pt-4 border-t border-[var(--color-gray-100)]">
            <AppButton
              variant="primary"
              size="sm"
              onClick={handleConfirmEmployee}
            >
              <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
              Confirm Employee
            </AppButton>
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => onOpenModal("extend")}
            >
              Extend Probation
            </AppButton>
          </div>
        )}
      </SectionCard>

      {/* Save button */}
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

/* ── Compensation (Salary) Tab ─────────────────────────────── */

function CompensationTab({
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
                    {comp.is_taxable && " \u00b7 Taxable"}
                    {comp.is_cpf_applicable && " \u00b7 CPF"}
                  </p>
                </div>
                <div className="text-right flex items-center gap-2">
                  <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                    ${(comp.amount ?? 0).toLocaleString()}
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
              <DatePicker
                label="Effective From"
                value={newComponent.effective_from}
                onChange={(v) =>
                  setNewComponent({
                    ...newComponent,
                    effective_from: v,
                  })
                }
              />
              <DatePicker
                label="Effective To (optional)"
                value={newComponent.effective_to}
                onChange={(v) =>
                  setNewComponent({
                    ...newComponent,
                    effective_to: v,
                  })
                }
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

/* ── Statutory Tab ─────────────────────────────────────────── */

function StatutoryTab({
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

  const workPassExpiry = getExpiryBadge(employee.work_pass_expiry);

  return (
    <div className="space-y-6">
      {/* Immigration */}
      <SectionCard
        title="Immigration & Pass Details"
        icon={<Shield className="h-4 w-4" />}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <AppInput
            label="Immigration Status"
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "citizen", label: "Citizen" },
              { value: "pr", label: "Permanent Resident" },
              { value: "foreigner", label: "Foreigner" },
            ]}
            value={getVal("immigration_status")}
            onChange={(e) => updateField("immigration_status", e.target.value)}
            disabled={!isAdmin}
          />
          <DatePicker
            label="Immigration Effective Date"
            value={getVal("immigration_effective_date")}
            onChange={(v) => updateField("immigration_effective_date", v)}
            disabled={!isAdmin}
          />
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
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--color-gray-700)]">
              Work Pass Expiry
            </label>
            <div className="flex items-center gap-2">
              <DatePicker
                value={getVal("work_pass_expiry")}
                onChange={(v) => updateField("work_pass_expiry", v)}
                disabled={!isAdmin}
              />
              {workPassExpiry && (
                <span
                  className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${workPassExpiry.className}`}
                >
                  {workPassExpiry.label}
                </span>
              )}
            </div>
          </div>
        </div>
      </SectionCard>

      {/* Tax & CPF */}
      <SectionCard
        title="Tax & CPF Settings"
        icon={<DollarSign className="h-4 w-4" />}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <AppInput
            label="IRAS Auto-Inclusion"
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "true", label: "Yes" },
              { value: "false", label: "No" },
            ]}
            value={String(
              getVal("iras_auto_inclusion" as keyof EmployeeDetail) ?? "",
            )}
            onChange={(e) =>
              updateField(
                "iras_auto_inclusion" as keyof EmployeeDetail,
                e.target.value,
              )
            }
            disabled={!isAdmin}
          />
          <AppInput
            label="Tax Reference"
            value={getVal("tax_reference" as keyof EmployeeDetail)}
            onChange={(e) =>
              updateField(
                "tax_reference" as keyof EmployeeDetail,
                e.target.value,
              )
            }
            disabled={!isAdmin}
          />
          <AppInput
            label="CPF Status"
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "include", label: "Include" },
              { value: "exclude", label: "Exclude" },
              { value: "full_employer", label: "Full Employer" },
            ]}
            value={getVal("cpf_status" as keyof EmployeeDetail)}
            onChange={(e) =>
              updateField("cpf_status" as keyof EmployeeDetail, e.target.value)
            }
            disabled={!isAdmin}
          />
          <AppInput
            label="AMCS"
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "true", label: "Yes" },
              { value: "false", label: "No" },
            ]}
            value={String(getVal("amcs_enabled" as keyof EmployeeDetail) ?? "")}
            onChange={(e) =>
              updateField(
                "amcs_enabled" as keyof EmployeeDetail,
                e.target.value,
              )
            }
            disabled={!isAdmin}
          />
          <AppInput
            label="PMBS"
            variant="select"
            options={[
              { value: "", label: "Select..." },
              { value: "true", label: "Yes" },
              { value: "false", label: "No" },
            ]}
            value={String(getVal("pmbs_enabled" as keyof EmployeeDetail) ?? "")}
            onChange={(e) =>
              updateField(
                "pmbs_enabled" as keyof EmployeeDetail,
                e.target.value,
              )
            }
            disabled={!isAdmin}
          />
          <AppInput
            label="Community Chest Amount"
            variant="number"
            value={getVal("community_chest_amount" as keyof EmployeeDetail)}
            onChange={(e) =>
              updateField(
                "community_chest_amount" as keyof EmployeeDetail,
                parseFloat(e.target.value) || 0,
              )
            }
            disabled={!isAdmin}
          />
          <AppInput
            label="SHG Override"
            value={getVal("shg_override_amount" as keyof EmployeeDetail)}
            onChange={(e) =>
              updateField(
                "shg_override_amount" as keyof EmployeeDetail,
                e.target.value,
              )
            }
            disabled={!isAdmin}
            placeholder="Leave blank for auto-detection by race"
          />
        </div>
      </SectionCard>

      {/* Save button */}
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

/* ── Leave Tab ─────────────────────────────────────────────── */

function LeaveTab({ employeeId }: { employeeId: number }) {
  const [balances, setBalances] = useState<AdminLeaveBalance[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBalances = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await employeesApi.getEmployeeLeaveBalances(employeeId);
      setBalances(data.balances ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load leave balances.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchBalances();
  }, [fetchBalances]);

  if (isLoading) return <GridSkeleton />;
  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchBalances}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  if (balances.length === 0) {
    return (
      <AppCard variant="standard">
        <div className="py-8 text-center">
          <Calendar className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-3" />
          <p className="text-sm text-[var(--color-gray-500)]">
            No leave balances found. Ensure leave types are configured for this
            employee.
          </p>
        </div>
      </AppCard>
    );
  }

  return (
    <div className="space-y-3">
      {balances.map((balance) => {
        const remaining =
          balance.entitlement_days - balance.used_days - balance.pending_days;
        const usedPercent =
          balance.entitlement_days > 0
            ? (balance.used_days / balance.entitlement_days) * 100
            : 0;
        const pendingPercent =
          balance.entitlement_days > 0
            ? (balance.pending_days / balance.entitlement_days) * 100
            : 0;

        return (
          <AppCard key={balance.leave_type} variant="standard">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <p className="text-sm font-medium text-[var(--color-gray-900)]">
                  {balance.leave_type}
                </p>
                <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                  {balance.year}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-[var(--color-gray-900)]">
                  {balance.used_days} of {balance.entitlement_days} days used
                </p>
                {balance.pending_days > 0 && (
                  <p className="text-xs text-amber-600 mt-0.5">
                    {balance.pending_days} pending
                  </p>
                )}
              </div>
            </div>
            {/* Visual bar */}
            <div className="h-2.5 bg-[var(--color-gray-100)] rounded-full overflow-hidden flex">
              <div
                className="h-full bg-blue-500 transition-all"
                style={{ width: `${Math.min(usedPercent, 100)}%` }}
              />
              <div
                className="h-full bg-amber-400 transition-all"
                style={{
                  width: `${Math.min(pendingPercent, 100 - usedPercent)}%`,
                }}
              />
            </div>
            <div className="flex items-center gap-4 mt-2 text-xs text-[var(--color-gray-500)]">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                Used ({balance.used_days})
              </span>
              {balance.pending_days > 0 && (
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  Pending ({balance.pending_days})
                </span>
              )}
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-[var(--color-gray-200)]" />
                Remaining ({remaining})
              </span>
            </div>
          </AppCard>
        );
      })}
    </div>
  );
}

/* ── Documents Tab ──────────────────────────────────────────── */

const DOCUMENT_TYPES = [
  { value: "contract", label: "Contract" },
  { value: "nric", label: "NRIC" },
  { value: "work_permit", label: "Work Permit" },
  { value: "medical_certificate", label: "Medical Certificate" },
  { value: "tax_form", label: "Tax Form" },
  { value: "certificate", label: "Certificate" },
  { value: "other", label: "Other" },
] as const;

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
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadDocType, setUploadDocType] = useState("other");
  const [uploadDescription, setUploadDescription] = useState("");
  const [uploadExpiryDate, setUploadExpiryDate] = useState("");
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

  function handleFileSelect(files: FileList | null) {
    if (!files || files.length === 0) return;
    setSelectedFiles(Array.from(files));
    setShowUploadForm(true);
  }

  async function handleUploadSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    try {
      for (const file of selectedFiles) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("document_type", uploadDocType);
        if (uploadDescription.trim()) {
          formData.append("description", uploadDescription.trim());
        }
        if (uploadExpiryDate) {
          formData.append("expiry_date", uploadExpiryDate);
        }
        await employeesApi.uploadDocument(employeeId, formData);
      }
      toast.success(
        selectedFiles.length === 1
          ? "Document uploaded"
          : `${selectedFiles.length} documents uploaded`,
      );
      setShowUploadForm(false);
      setSelectedFiles([]);
      setUploadDocType("other");
      setUploadDescription("");
      setUploadExpiryDate("");
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
    handleFileSelect(e.dataTransfer.files);
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
      {isAdmin && !showUploadForm && (
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
            Drop files here or click to upload
          </p>
          <p className="text-xs text-[var(--color-gray-400)] mt-1">
            PDF, images, or office documents up to 10MB
          </p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
          />
        </div>
      )}

      {/* Upload form (shown after file selection) */}
      {showUploadForm && (
        <AppCard variant="elevated">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Upload Document{selectedFiles.length > 1 ? "s" : ""}
            </h3>
            <button
              type="button"
              onClick={() => {
                setShowUploadForm(false);
                setSelectedFiles([]);
              }}
              className="p-1 rounded-lg hover:bg-[var(--color-gray-100)]"
            >
              <X className="h-4 w-4 text-[var(--color-gray-500)]" />
            </button>
          </div>

          {/* Selected file names */}
          <div className="mb-4 space-y-1">
            {selectedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 text-sm text-[var(--color-gray-700)]"
              >
                <FileText className="h-4 w-4 text-[var(--color-gray-400)] shrink-0" />
                <span className="truncate">{file.name}</span>
                <span className="text-xs text-[var(--color-gray-400)] shrink-0">
                  ({formatFileSize(file.size)})
                </span>
              </div>
            ))}
          </div>

          <form onSubmit={handleUploadSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <AppInput
                label="Document Type"
                variant="select"
                options={DOCUMENT_TYPES.map((t) => ({
                  value: t.value,
                  label: t.label,
                }))}
                value={uploadDocType}
                onChange={(e) => setUploadDocType(e.target.value)}
              />
              <DatePicker
                label="Expiry Date (optional)"
                value={uploadExpiryDate}
                onChange={setUploadExpiryDate}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--color-gray-700)]">
                Description (optional)
              </label>
              <input
                type="text"
                value={uploadDescription}
                onChange={(e) => setUploadDescription(e.target.value)}
                placeholder="Brief description of the document"
                className="rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] focus:border-[var(--color-surface-input-focus)]"
              />
            </div>
            <div className="flex gap-3 justify-end pt-2">
              <AppButton
                type="button"
                variant="outlined"
                size="sm"
                onClick={() => {
                  setShowUploadForm(false);
                  setSelectedFiles([]);
                }}
              >
                Cancel
              </AppButton>
              <AppButton
                type="submit"
                variant="primary"
                size="sm"
                loading={isUploading}
              >
                Upload{" "}
                {selectedFiles.length > 1
                  ? `${selectedFiles.length} Files`
                  : "File"}
              </AppButton>
            </div>
          </form>
        </AppCard>
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
          {documents.map((doc) => {
            const expiryBadge = getExpiryBadge(doc.expiry_date);
            return (
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
                    {doc.description && (
                      <p className="text-xs text-[var(--color-gray-400)] mt-0.5 truncate">
                        {doc.description}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {expiryBadge && (
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${expiryBadge.className}`}
                    >
                      {expiryBadge.label}
                    </span>
                  )}
                  {doc.expiry_date && !expiryBadge && (
                    <span className="text-xs text-[var(--color-gray-400)] whitespace-nowrap flex items-center gap-1">
                      <CalendarDays className="h-3 w-3" />
                      {doc.expiry_date}
                    </span>
                  )}
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
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Timeline Tab ──────────────────────────────────────────── */

const TIMELINE_FILTERS = [
  "all",
  "profile",
  "salary",
  "leave",
  "status",
  "document",
  "note",
] as const;
type TimelineFilter = (typeof TIMELINE_FILTERS)[number];

const TIMELINE_FILTER_LABELS: Record<TimelineFilter, string> = {
  all: "All",
  profile: "Profile",
  salary: "Salary",
  leave: "Leave",
  status: "Status",
  document: "Document",
  note: "Note",
};

function categorizeEvent(eventType: string): TimelineFilter {
  const lower = eventType.toLowerCase();
  if (lower.includes("salary") || lower.includes("compensation"))
    return "salary";
  if (lower.includes("leave")) return "leave";
  if (
    lower.includes("hired") ||
    lower.includes("confirmed") ||
    lower.includes("terminated") ||
    lower.includes("status") ||
    lower.includes("probation")
  )
    return "status";
  if (lower.includes("document")) return "document";
  if (lower.includes("note")) return "note";
  return "profile";
}

const STATUS_EVENTS = new Set([
  "hired",
  "confirmed",
  "terminated",
  "resigned",
  "probation_extended",
]);

function TimelineTab({ employeeId }: { employeeId: number }) {
  const [events, setEvents] = useState<EmploymentEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<TimelineFilter>("all");

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

  const filtered =
    filter === "all"
      ? events
      : events.filter((e) => categorizeEvent(e.event_type) === filter);

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
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <Filter className="h-4 w-4 text-[var(--color-gray-400)] shrink-0" />
        {TIMELINE_FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
              filter === f
                ? "bg-[var(--color-primary)] text-white"
                : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:bg-[var(--color-gray-200)]"
            }`}
          >
            {TIMELINE_FILTER_LABELS[f]}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <AppCard variant="standard">
          <p className="text-sm text-[var(--color-gray-500)] text-center py-6">
            No events matching this filter.
          </p>
        </AppCard>
      ) : (
        <div className="relative pl-6">
          {/* Timeline line */}
          <div className="absolute left-2.5 top-2 bottom-2 w-px bg-[var(--color-gray-200)]" />

          <div className="space-y-4">
            {filtered.map((event) => {
              const eventLower = event.event_type.toLowerCase();
              const isStatusEvent = STATUS_EVENTS.has(eventLower);
              const isNegativeStatus =
                eventLower === "terminated" || eventLower === "resigned";
              const isSalaryEvent = eventLower.includes("salary");

              /* Dot color: red for terminated/resigned, green for positive status, blue for other */
              const dotOuter = isNegativeStatus
                ? "bg-red-50 border-red-500"
                : isStatusEvent
                  ? "bg-emerald-50 border-emerald-500"
                  : "bg-[var(--color-primary-bg)] border-[var(--color-primary)]";
              const dotInner = isNegativeStatus
                ? "bg-red-500"
                : isStatusEvent
                  ? "bg-emerald-500"
                  : "bg-[var(--color-primary)]";

              return (
                <div key={event.id} className="relative">
                  {/* Timeline dot */}
                  <div
                    className={`absolute -left-6 top-1.5 w-5 h-5 rounded-full border-2 flex items-center justify-center ${dotOuter}`}
                  >
                    <div className={`w-2 h-2 rounded-full ${dotInner}`} />
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
                        {/* Salary diff highlight */}
                        {isSalaryEvent &&
                          event.old_value &&
                          event.new_value && (
                            <p className="text-xs font-medium text-[var(--color-primary)] mt-1 flex items-center gap-1">
                              <TrendingUp className="h-3 w-3" />$
                              {String(
                                (event.old_value as Record<string, unknown>)
                                  .amount ?? "",
                              )}{" "}
                              &rarr; $
                              {String(
                                (event.new_value as Record<string, unknown>)
                                  .amount ?? "",
                              )}
                            </p>
                          )}
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
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Notes Tab ─────────────────────────────────────────────── */

const NOTE_TYPES = [
  "all",
  "general",
  "performance",
  "disciplinary",
  "confidential",
] as const;
type NoteFilter = (typeof NOTE_TYPES)[number];

const NOTE_TYPE_STYLES: Record<string, string> = {
  general: "bg-blue-50 text-blue-700",
  performance: "bg-emerald-50 text-emerald-700",
  disciplinary: "bg-red-50 text-red-700",
  confidential: "bg-purple-50 text-purple-700",
};

function NotesTab({
  employeeId,
  isAdmin,
}: {
  employeeId: number;
  isAdmin: boolean;
}) {
  const [notes, setNotes] = useState<EmployeeNote[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<NoteFilter>("all");
  const [showAddForm, setShowAddForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newNote, setNewNote] = useState({
    note_type: "general",
    content: "",
    is_confidential: false,
  });

  const fetchNotes = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await employeesApi.listNotes(employeeId);
      setNotes(data.notes ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load notes.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!newNote.content.trim()) return;

    setIsSubmitting(true);
    try {
      await employeesApi.createNote(employeeId, newNote);
      toast.success("Note added");
      setShowAddForm(false);
      setNewNote({ note_type: "general", content: "", is_confidential: false });
      fetchNotes();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to add note";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) return <ListSkeleton rows={3} />;
  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchNotes}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  const filtered =
    filter === "all" ? notes : notes.filter((n) => n.note_type === filter);

  return (
    <div className="space-y-4">
      {/* Filter + Add */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 overflow-x-auto">
          {NOTE_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setFilter(t)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors capitalize ${
                filter === t
                  ? "bg-[var(--color-primary)] text-white"
                  : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:bg-[var(--color-gray-200)]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        {isAdmin && (
          <AppButton
            variant="outlined"
            size="sm"
            onClick={() => setShowAddForm(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Note
          </AppButton>
        )}
      </div>

      {/* Notes list */}
      {filtered.length === 0 ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <StickyNote className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-3" />
            <p className="text-sm text-[var(--color-gray-500)]">
              {notes.length === 0
                ? "No notes recorded for this employee."
                : "No notes matching this filter."}
            </p>
          </div>
        </AppCard>
      ) : (
        <div className="space-y-3">
          {filtered.map((note) => (
            <AppCard key={note.id} variant="standard">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${NOTE_TYPE_STYLES[note.note_type] || "bg-[var(--color-gray-100)] text-[var(--color-gray-600)]"}`}
                    >
                      {note.note_type}
                    </span>
                    {note.is_confidential && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700">
                        <Lock className="h-3 w-3" />
                        Confidential
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-[var(--color-gray-700)] whitespace-pre-wrap">
                    {note.content}
                  </p>
                  <p className="text-xs text-[var(--color-gray-400)] mt-2">
                    Created by #{note.created_by}
                    {note.created_at && ` on ${note.created_at.split("T")[0]}`}
                  </p>
                </div>
              </div>
            </AppCard>
          ))}
        </div>
      )}

      {/* Add note form */}
      {showAddForm && (
        <AppCard variant="elevated">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Add Note
            </h3>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="p-1 rounded-lg hover:bg-[var(--color-gray-100)]"
            >
              <X className="h-4 w-4 text-[var(--color-gray-500)]" />
            </button>
          </div>
          <form onSubmit={handleAddNote} className="space-y-4">
            <AppInput
              label="Note Type"
              variant="select"
              options={[
                { value: "general", label: "General" },
                { value: "performance", label: "Performance" },
                { value: "disciplinary", label: "Disciplinary" },
                { value: "confidential", label: "Confidential" },
              ]}
              value={newNote.note_type}
              onChange={(e) =>
                setNewNote({ ...newNote, note_type: e.target.value })
              }
            />
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--color-gray-700)]">
                Content
              </label>
              <textarea
                value={newNote.content}
                onChange={(e) =>
                  setNewNote({ ...newNote, content: e.target.value })
                }
                rows={4}
                className="rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] resize-y"
                placeholder="Enter note content..."
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-[var(--color-gray-700)]">
              <input
                type="checkbox"
                checked={newNote.is_confidential}
                onChange={(e) =>
                  setNewNote({ ...newNote, is_confidential: e.target.checked })
                }
                className="rounded border-[var(--color-gray-300)]"
              />
              Mark as confidential
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
                Add Note
              </AppButton>
            </div>
          </form>
        </AppCard>
      )}
    </div>
  );
}

/* ── Onboarding Tab ────────────────────────────────────────── */

function OnboardingTab({
  employee,
  documents,
}: {
  employee: EmployeeDetail;
  documents: EmployeeDocument[];
}) {
  const completeness = computeCompleteness(employee);

  /* Fetch policy acknowledgment status for onboarding checklist */
  const [policyStatus, setPolicyStatus] = useState<{
    totalRequired: number;
    pendingCount: number;
    loaded: boolean;
  }>({ totalRequired: 0, pendingCount: 0, loaded: false });

  useEffect(() => {
    let cancelled = false;

    async function fetchPolicyStatus() {
      try {
        /* Fetch all policies and pending in parallel to compute counts */
        const [allData, pendingData] = await Promise.all([
          policiesApi.list(),
          policiesApi.pendingAcknowledgments(),
        ]);

        if (cancelled) return;

        const requiringAck = (allData.policies ?? []).filter(
          (p) => p.requires_acknowledgment && p.status === "active",
        );
        const pending = pendingData.pending_policies ?? [];

        setPolicyStatus({
          totalRequired: requiringAck.length,
          pendingCount: pending.length,
          loaded: true,
        });
      } catch {
        /* Non-critical: show as incomplete if we cannot determine status */
        if (!cancelled) {
          setPolicyStatus({ totalRequired: 0, pendingCount: 0, loaded: true });
        }
      }
    }

    fetchPolicyStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  const policyAckDone =
    policyStatus.loaded &&
    policyStatus.totalRequired > 0 &&
    policyStatus.pendingCount === 0;

  const policyAckDetail = !policyStatus.loaded
    ? "Checking..."
    : policyStatus.totalRequired === 0
      ? "No policies require acknowledgment"
      : policyStatus.pendingCount === 0
        ? `All ${policyStatus.totalRequired} policies acknowledged`
        : `${policyStatus.totalRequired - policyStatus.pendingCount} of ${policyStatus.totalRequired} acknowledged`;

  const checklistItems = [
    {
      label: "Profile completed (>80%)",
      done: completeness > 80,
      detail: `${completeness}% complete`,
      href: undefined as string | undefined,
    },
    {
      label: "NRIC / FIN submitted",
      done: Boolean(employee.nric_fin),
      detail: employee.nric_fin ? "Submitted" : "Missing",
      href: undefined as string | undefined,
    },
    {
      label: "Bank details submitted",
      done: Boolean(employee.bank_name && employee.bank_account_number),
      detail:
        employee.bank_name && employee.bank_account_number
          ? employee.bank_name
          : "Missing",
      href: undefined as string | undefined,
    },
    {
      label: "Emergency contact added",
      done: false, // Will be updated async
      detail: "Check Personal tab",
      href: undefined as string | undefined,
    },
    {
      label: "Employment contract uploaded",
      done: documents.some(
        (d) =>
          d.document_type.toLowerCase().includes("contract") ||
          d.document_type.toLowerCase().includes("employment"),
      ),
      detail: documents.some(
        (d) =>
          d.document_type.toLowerCase().includes("contract") ||
          d.document_type.toLowerCase().includes("employment"),
      )
        ? "Uploaded"
        : "Not found",
      href: undefined as string | undefined,
    },
    {
      label: "Tax form submitted",
      done: documents.some(
        (d) =>
          d.document_type.toLowerCase().includes("tax") ||
          d.document_type.toLowerCase().includes("ir8a") ||
          d.document_type.toLowerCase().includes("iras"),
      ),
      detail: documents.some(
        (d) =>
          d.document_type.toLowerCase().includes("tax") ||
          d.document_type.toLowerCase().includes("ir8a") ||
          d.document_type.toLowerCase().includes("iras"),
      )
        ? "Uploaded"
        : "Not found",
      href: undefined as string | undefined,
    },
    {
      label: "Company policies acknowledged",
      done: policyAckDone,
      detail: policyAckDetail,
      href: "/policies" as string | undefined,
    },
  ];

  const doneCount = checklistItems.filter((i) => i.done).length;
  const progress = Math.round((doneCount / checklistItems.length) * 100);

  return (
    <div className="space-y-4">
      {/* Progress */}
      <AppCard variant="standard">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Onboarding Progress
          </h3>
          <span className="text-sm font-medium text-[var(--color-gray-600)]">
            {doneCount} of {checklistItems.length} items
          </span>
        </div>
        <div className="h-2 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
          <div
            className="h-full bg-[var(--color-primary)] rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </AppCard>

      {/* Checklist */}
      <div className="space-y-2">
        {checklistItems.map((item, idx) => {
          const content = (
            <>
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                  item.done ? "bg-emerald-500" : "bg-[var(--color-gray-200)]"
                }`}
              >
                {item.done && (
                  <CheckCircle2 className="h-3.5 w-3.5 text-white" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p
                  className={`text-sm font-medium ${
                    item.done
                      ? "text-emerald-700"
                      : "text-[var(--color-gray-900)]"
                  }`}
                >
                  {item.label}
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">
                  {item.detail}
                </p>
              </div>
            </>
          );

          if (item.href) {
            return (
              <Link
                key={idx}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-[8px] border transition-colors ${
                  item.done
                    ? "border-emerald-200 bg-emerald-50"
                    : "border-[var(--color-gray-200)] bg-white hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)]"
                }`}
              >
                {content}
              </Link>
            );
          }

          return (
            <div
              key={idx}
              className={`flex items-center gap-3 px-4 py-3 rounded-[8px] border ${
                item.done
                  ? "border-emerald-200 bg-emerald-50"
                  : "border-[var(--color-gray-200)] bg-white"
              }`}
            >
              {content}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Custom Fields Tab ─────────────────────────────────────── */

function CustomFieldsTab({
  employeeId,
  isAdmin,
}: {
  employeeId: number;
  isAdmin: boolean;
}) {
  const [definitions, setDefinitions] = useState<CustomFieldDefinition[]>([]);
  const [values, setValues] = useState<CustomFieldValue[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [formValues, setFormValues] = useState<Record<number, string>>({});
  const [hasChanges, setHasChanges] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [defsData, valsData] = await Promise.all([
        employeesApi.listCustomFields(),
        employeesApi.listCustomFieldValues(employeeId),
      ]);
      const employeeDefs = (defsData.custom_fields ?? []).filter(
        (d) => d.applies_to === "employee",
      );
      setDefinitions(employeeDefs);
      setValues(valsData.values ?? []);

      // Initialize form
      const initial: Record<number, string> = {};
      for (const def of employeeDefs) {
        const existing = (valsData.values ?? []).find(
          (v) => v.field_definition_id === def.id,
        );
        initial[def.id] = existing?.value ?? "";
      }
      setFormValues(initial);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load custom fields.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function handleFieldChange(defId: number, value: string) {
    setFormValues((prev) => ({ ...prev, [defId]: value }));
    setHasChanges(true);
  }

  async function handleSave() {
    if (!hasChanges) return;
    setIsSaving(true);
    try {
      for (const def of definitions) {
        const value = formValues[def.id] ?? "";
        const existing = values.find((v) => v.field_definition_id === def.id);
        if (existing) {
          await employeesApi.updateCustomFieldValue(employeeId, existing.id, {
            value,
          });
        } else if (value) {
          await employeesApi.setCustomFieldValue(employeeId, {
            field_definition_id: def.id,
            entity_type: "employee",
            entity_id: employeeId,
            value,
          });
        }
      }
      toast.success("Custom fields saved");
      setHasChanges(false);
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save custom fields";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) return <ProfileSkeleton />;
  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchData}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  if (definitions.length === 0) {
    return (
      <AppCard variant="standard">
        <div className="py-8 text-center">
          <Settings className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-3" />
          <p className="text-sm text-[var(--color-gray-500)]">
            No custom fields defined for employees. Configure them in Company
            Settings.
          </p>
        </div>
      </AppCard>
    );
  }

  return (
    <div className="space-y-6">
      <SectionCard
        title="Custom Fields"
        icon={<Settings className="h-4 w-4" />}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {definitions
            .sort((a, b) => a.display_order - b.display_order)
            .map((def) => {
              const fieldValue = formValues[def.id] ?? "";

              if (def.field_type === "checkbox") {
                return (
                  <label
                    key={def.id}
                    className="flex items-center gap-2 text-sm text-[var(--color-gray-700)] min-h-[44px]"
                  >
                    <input
                      type="checkbox"
                      checked={fieldValue === "true"}
                      onChange={(e) =>
                        handleFieldChange(
                          def.id,
                          e.target.checked ? "true" : "false",
                        )
                      }
                      disabled={!isAdmin}
                      className="rounded border-[var(--color-gray-300)]"
                    />
                    {def.field_label}
                    {def.is_required && <span className="text-red-500">*</span>}
                  </label>
                );
              }

              if (def.field_type === "dropdown") {
                let options: { value: string; label: string }[] = [
                  { value: "", label: "Select..." },
                ];
                try {
                  const parsed = JSON.parse(def.dropdown_options || "[]");
                  if (Array.isArray(parsed)) {
                    options = [
                      { value: "", label: "Select..." },
                      ...parsed.map((opt: string) => ({
                        value: opt,
                        label: opt,
                      })),
                    ];
                  }
                } catch {
                  /* invalid JSON */
                }
                return (
                  <AppInput
                    key={def.id}
                    label={`${def.field_label}${def.is_required ? " *" : ""}`}
                    variant="select"
                    options={options}
                    value={fieldValue}
                    onChange={(e) => handleFieldChange(def.id, e.target.value)}
                    disabled={!isAdmin}
                  />
                );
              }

              return (
                <AppInput
                  key={def.id}
                  label={`${def.field_label}${def.is_required ? " *" : ""}`}
                  variant={
                    def.field_type === "number"
                      ? "number"
                      : def.field_type === "date"
                        ? "date"
                        : undefined
                  }
                  value={fieldValue}
                  onChange={(
                    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
                  ) => handleFieldChange(def.id, e.target.value)}
                  disabled={!isAdmin}
                />
              );
            })}
        </div>
      </SectionCard>

      {isAdmin && (
        <div className="flex justify-end gap-3 pt-2">
          <AppButton
            variant="primary"
            size="md"
            onClick={handleSave}
            loading={isSaving}
            disabled={!hasChanges}
          >
            Save Custom Fields
          </AppButton>
        </div>
      )}
    </div>
  );
}

/* ── Skills Tab ────────────────────────────────────────────── */

const PROFICIENCY_STYLES: Record<string, string> = {
  beginner: "bg-blue-50 text-blue-700",
  intermediate: "bg-amber-50 text-amber-700",
  advanced: "bg-emerald-50 text-emerald-700",
  expert: "bg-purple-50 text-purple-700",
};

function SkillsTab({
  employeeId,
  isAdmin,
}: {
  employeeId: number;
  isAdmin: boolean;
}) {
  const [skills, setSkills] = useState<EmployeeSkill[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newSkill, setNewSkill] = useState({
    skill_name: "",
    proficiency_level: "intermediate",
    certification_name: "",
    certification_number: "",
    certified_date: "",
    expiry_date: "",
    issuing_body: "",
  });

  const fetchSkills = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await employeesApi.listSkills(employeeId);
      setSkills(data.skills ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load skills.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  async function handleAddSkill(e: React.FormEvent) {
    e.preventDefault();
    if (!newSkill.skill_name.trim()) return;

    setIsSubmitting(true);
    try {
      await employeesApi.createSkill(employeeId, newSkill);
      toast.success("Skill added");
      setShowAddForm(false);
      setNewSkill({
        skill_name: "",
        proficiency_level: "intermediate",
        certification_name: "",
        certification_number: "",
        certified_date: "",
        expiry_date: "",
        issuing_body: "",
      });
      fetchSkills();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to add skill";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteSkill(skillId: number) {
    try {
      await employeesApi.deleteSkill(employeeId, skillId);
      toast.success("Skill removed");
      fetchSkills();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to remove skill";
      toast.error(message);
    }
  }

  if (isLoading) return <ListSkeleton rows={3} />;
  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchSkills}>
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
          Skills & Certifications ({skills.length})
        </h3>
        {isAdmin && (
          <AppButton
            variant="outlined"
            size="sm"
            onClick={() => setShowAddForm(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Skill
          </AppButton>
        )}
      </div>

      {skills.length === 0 ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <Award className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-3" />
            <p className="text-sm text-[var(--color-gray-500)]">
              No skills or certifications recorded.
            </p>
          </div>
        </AppCard>
      ) : (
        <div className="space-y-3">
          {skills.map((skill) => {
            const expiryBadge = getExpiryBadge(skill.expiry_date);
            const isExpired =
              skill.expiry_date &&
              new Date(skill.expiry_date).getTime() < Date.now();

            return (
              <AppCard key={skill.id} variant="standard">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p
                        className={`text-sm font-medium ${isExpired ? "text-[var(--color-gray-400)] line-through" : "text-[var(--color-gray-900)]"}`}
                      >
                        {skill.skill_name}
                      </p>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${PROFICIENCY_STYLES[skill.proficiency_level] || "bg-[var(--color-gray-100)] text-[var(--color-gray-600)]"}`}
                      >
                        {skill.proficiency_level}
                      </span>
                      {expiryBadge && (
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${expiryBadge.className}`}
                        >
                          {expiryBadge.label}
                        </span>
                      )}
                    </div>
                    {skill.certification_name && (
                      <p className="text-xs text-[var(--color-gray-500)] mt-1">
                        {skill.certification_name}
                        {skill.certification_number &&
                          ` (#${skill.certification_number})`}
                        {skill.issuing_body && ` - ${skill.issuing_body}`}
                      </p>
                    )}
                    {skill.certified_date && (
                      <p className="text-xs text-[var(--color-gray-400)] mt-0.5">
                        Certified: {skill.certified_date}
                        {skill.expiry_date &&
                          ` | Expires: ${skill.expiry_date}`}
                      </p>
                    )}
                  </div>
                  {isAdmin && (
                    <button
                      type="button"
                      onClick={() => handleDeleteSkill(skill.id)}
                      className="p-2 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                      title="Remove skill"
                    >
                      <Trash2 className="h-4 w-4 text-[var(--color-gray-400)]" />
                    </button>
                  )}
                </div>
              </AppCard>
            );
          })}
        </div>
      )}

      {/* Add skill form */}
      {showAddForm && (
        <AppCard variant="elevated">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Add Skill / Certification
            </h3>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="p-1 rounded-lg hover:bg-[var(--color-gray-100)]"
            >
              <X className="h-4 w-4 text-[var(--color-gray-500)]" />
            </button>
          </div>
          <form onSubmit={handleAddSkill} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <AppInput
                label="Skill Name"
                value={newSkill.skill_name}
                onChange={(e) =>
                  setNewSkill({ ...newSkill, skill_name: e.target.value })
                }
                placeholder="e.g. Project Management"
              />
              <AppInput
                label="Proficiency Level"
                variant="select"
                options={[
                  { value: "beginner", label: "Beginner" },
                  { value: "intermediate", label: "Intermediate" },
                  { value: "advanced", label: "Advanced" },
                  { value: "expert", label: "Expert" },
                ]}
                value={newSkill.proficiency_level}
                onChange={(e) =>
                  setNewSkill({
                    ...newSkill,
                    proficiency_level: e.target.value,
                  })
                }
              />
              <AppInput
                label="Certification Name (optional)"
                value={newSkill.certification_name}
                onChange={(e) =>
                  setNewSkill({
                    ...newSkill,
                    certification_name: e.target.value,
                  })
                }
                placeholder="e.g. PMP"
              />
              <AppInput
                label="Certification Number (optional)"
                value={newSkill.certification_number}
                onChange={(e) =>
                  setNewSkill({
                    ...newSkill,
                    certification_number: e.target.value,
                  })
                }
              />
              <DatePicker
                label="Certified Date"
                value={newSkill.certified_date}
                onChange={(v) =>
                  setNewSkill({
                    ...newSkill,
                    certified_date: v,
                  })
                }
              />
              <DatePicker
                label="Expiry Date"
                value={newSkill.expiry_date}
                onChange={(v) =>
                  setNewSkill({
                    ...newSkill,
                    expiry_date: v,
                  })
                }
              />
              <AppInput
                label="Issuing Body (optional)"
                value={newSkill.issuing_body}
                onChange={(e) =>
                  setNewSkill({
                    ...newSkill,
                    issuing_body: e.target.value,
                  })
                }
                placeholder="e.g. PMI"
              />
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
                Add Skill
              </AppButton>
            </div>
          </form>
        </AppCard>
      )}
    </div>
  );
}

/* ── Shared Modal Shell ─────────────────────────────────────── */

type ModalType =
  | "employment"
  | "compensation"
  | "statutory"
  | "confirm"
  | "extend"
  | "terminate"
  | null;

function EditModal({
  isOpen,
  onClose,
  title,
  children,
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-[12px] shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b border-[var(--color-gray-200)]">
          <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)]"
          >
            <X className="h-4 w-4 text-[var(--color-gray-500)]" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

/* ── Edit Employment Modal Content ─────────────────────────── */

function EditEmploymentForm({
  employee,
  employeeId,
  onSaved,
  onClose,
}: {
  employee: EmployeeDetail;
  employeeId: number;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    department: employee.department || "",
    designation: employee.designation || "",
    employment_type: employee.employment_type || "",
    working_hours_type: employee.working_hours_type || "",
    reporting_manager_id: employee.reporting_manager_id ?? "",
    overtime_eligible: employee.overtime_eligible ?? false,
    tags: employee.tags || "",
  });
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSaving(true);
    try {
      await employeesApi.updateEmployee(employeeId, {
        department: form.department,
        designation: form.designation,
        employment_type: form.employment_type,
        working_hours_type: form.working_hours_type,
        reporting_manager_id: form.reporting_manager_id
          ? Number(form.reporting_manager_id)
          : null,
        overtime_eligible: form.overtime_eligible,
        tags: form.tags,
      } as Partial<EmployeeDetail>);
      toast.success("Employment details updated");
      onSaved();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to update employment";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <AppInput
          label="Department"
          value={form.department}
          onChange={(e) => setForm({ ...form, department: e.target.value })}
        />
        <AppInput
          label="Designation"
          value={form.designation}
          onChange={(e) => setForm({ ...form, designation: e.target.value })}
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
          value={form.employment_type}
          onChange={(e) =>
            setForm({ ...form, employment_type: e.target.value })
          }
        />
        <AppInput
          label="Working Hours Type"
          variant="select"
          options={[
            { value: "", label: "Select..." },
            { value: "fixed", label: "Fixed" },
            { value: "shift", label: "Shift" },
            { value: "flexible", label: "Flexible" },
          ]}
          value={form.working_hours_type}
          onChange={(e) =>
            setForm({ ...form, working_hours_type: e.target.value })
          }
        />
        <EmployeePicker
          label="Reporting Manager"
          value={
            form.reporting_manager_id ? Number(form.reporting_manager_id) : null
          }
          onChange={(id) =>
            setForm({ ...form, reporting_manager_id: id ? String(id) : "" })
          }
          excludeIds={employeeId ? [Number(employeeId)] : []}
        />
        <AppInput
          label="Tags (comma-separated)"
          value={form.tags}
          onChange={(e) => setForm({ ...form, tags: e.target.value })}
          placeholder="e.g. remote, senior"
        />
      </div>
      <label className="flex items-center gap-2 text-sm text-[var(--color-gray-700)]">
        <input
          type="checkbox"
          checked={form.overtime_eligible}
          onChange={(e) =>
            setForm({ ...form, overtime_eligible: e.target.checked })
          }
          className="rounded border-[var(--color-gray-300)]"
        />
        Overtime Eligible
      </label>
      <div className="flex gap-3 justify-end pt-2">
        <AppButton type="button" variant="outlined" size="md" onClick={onClose}>
          Cancel
        </AppButton>
        <AppButton type="submit" variant="primary" size="md" loading={isSaving}>
          Save Changes
        </AppButton>
      </div>
    </form>
  );
}

/* ── Edit Compensation Modal Content ───────────────────────── */

function EditCompensationForm({
  employee,
  employeeId,
  onSaved,
  onClose,
}: {
  employee: EmployeeDetail;
  employeeId: number;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    salary_monthly: employee.salary_monthly || 0,
    salary_type: employee.salary_type || "monthly",
    payment_method: employee.payment_method || "",
    payment_frequency: employee.payment_frequency || "monthly",
  });
  const [isSaving, setIsSaving] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const salaryChanged =
    employee.salary_monthly && form.salary_monthly !== employee.salary_monthly;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // If salary changed, show confirmation first
    if (salaryChanged && !showConfirm) {
      setShowConfirm(true);
      return;
    }
    setIsSaving(true);
    try {
      await employeesApi.updateEmployee(employeeId, {
        salary_monthly: form.salary_monthly,
        salary_type: form.salary_type,
        payment_method: form.payment_method,
        payment_frequency: form.payment_frequency,
      } as Partial<EmployeeDetail>);
      toast.success("Compensation updated");
      onSaved();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to update compensation";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Salary change warning */}
      {showConfirm && salaryChanged && (
        <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-50 border border-amber-200">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">
              Salary Change Confirmation
            </p>
            <p className="text-sm text-amber-700 mt-1">
              Changing monthly salary from{" "}
              <span className="font-semibold">
                ${employee.salary_monthly.toLocaleString()}
              </span>{" "}
              to{" "}
              <span className="font-semibold">
                ${form.salary_monthly.toLocaleString()}
              </span>
              . This will be logged in the employee timeline.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <AppInput
          label="Monthly Salary ($)"
          variant="number"
          value={String(form.salary_monthly)}
          onChange={(e) => {
            setForm({
              ...form,
              salary_monthly: parseFloat(e.target.value) || 0,
            });
            setShowConfirm(false);
          }}
        />
        <AppInput
          label="Salary Type"
          variant="select"
          options={[
            { value: "monthly", label: "Monthly" },
            { value: "daily", label: "Daily" },
            { value: "hourly", label: "Hourly" },
          ]}
          value={form.salary_type}
          onChange={(e) => setForm({ ...form, salary_type: e.target.value })}
        />
        <AppInput
          label="Payment Method"
          variant="select"
          options={[
            { value: "", label: "Select..." },
            { value: "giro", label: "GIRO" },
            { value: "fast", label: "FAST" },
            { value: "cheque", label: "Cheque" },
            { value: "cash", label: "Cash" },
          ]}
          value={form.payment_method}
          onChange={(e) => setForm({ ...form, payment_method: e.target.value })}
        />
        <AppInput
          label="Payment Frequency"
          variant="select"
          options={[
            { value: "monthly", label: "Monthly" },
            { value: "bi_weekly", label: "Bi-Weekly" },
            { value: "weekly", label: "Weekly" },
          ]}
          value={form.payment_frequency}
          onChange={(e) =>
            setForm({ ...form, payment_frequency: e.target.value })
          }
        />
      </div>
      <div className="flex gap-3 justify-end pt-2">
        <AppButton type="button" variant="outlined" size="md" onClick={onClose}>
          Cancel
        </AppButton>
        <AppButton type="submit" variant="primary" size="md" loading={isSaving}>
          {showConfirm ? "Confirm & Save" : "Save Changes"}
        </AppButton>
      </div>
    </form>
  );
}

/* ── Edit Statutory Modal Content ──────────────────────────── */

function EditStatutoryForm({
  employee,
  employeeId,
  onSaved,
  onClose,
}: {
  employee: EmployeeDetail;
  employeeId: number;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    immigration_status: employee.immigration_status || "",
    pass_type: employee.pass_type || "",
    work_pass_number: employee.work_pass_number || "",
    work_pass_expiry: employee.work_pass_expiry || "",
    iras_auto_inclusion: String(employee.iras_auto_inclusion ?? ""),
    tax_reference: employee.tax_reference || "",
    cpf_status: employee.cpf_status || "",
  });
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSaving(true);
    try {
      await employeesApi.updateEmployee(employeeId, {
        immigration_status: form.immigration_status,
        pass_type: form.pass_type,
        work_pass_number: form.work_pass_number,
        work_pass_expiry: form.work_pass_expiry,
        iras_auto_inclusion: form.iras_auto_inclusion,
        tax_reference: form.tax_reference,
        cpf_status: form.cpf_status,
      } as Partial<EmployeeDetail>);
      toast.success("Statutory details updated");
      onSaved();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to update statutory info";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <AppInput
          label="Immigration Status"
          variant="select"
          options={[
            { value: "", label: "Select..." },
            { value: "citizen", label: "Citizen" },
            { value: "pr_year1", label: "PR Year 1" },
            { value: "pr_year2", label: "PR Year 2" },
            { value: "pr_year3_plus", label: "PR Year 3+" },
            { value: "foreigner", label: "Foreigner" },
          ]}
          value={form.immigration_status}
          onChange={(e) =>
            setForm({ ...form, immigration_status: e.target.value })
          }
        />
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
          value={form.pass_type}
          onChange={(e) => setForm({ ...form, pass_type: e.target.value })}
        />
        <AppInput
          label="Work Pass Number"
          value={form.work_pass_number}
          onChange={(e) =>
            setForm({ ...form, work_pass_number: e.target.value })
          }
          placeholder="Encrypted on save"
        />
        <DatePicker
          label="Work Pass Expiry"
          value={form.work_pass_expiry}
          onChange={(v) => setForm({ ...form, work_pass_expiry: v })}
        />
        <AppInput
          label="IRAS Auto-Inclusion"
          variant="select"
          options={[
            { value: "", label: "Select..." },
            { value: "true", label: "Yes" },
            { value: "false", label: "No" },
          ]}
          value={form.iras_auto_inclusion}
          onChange={(e) =>
            setForm({ ...form, iras_auto_inclusion: e.target.value })
          }
        />
        <AppInput
          label="Tax Reference"
          value={form.tax_reference}
          onChange={(e) => setForm({ ...form, tax_reference: e.target.value })}
        />
        <AppInput
          label="CPF Status"
          variant="select"
          options={[
            { value: "", label: "Select..." },
            { value: "include", label: "Include" },
            { value: "exclude", label: "Exclude" },
            { value: "full_employer", label: "Full Employer" },
          ]}
          value={form.cpf_status}
          onChange={(e) => setForm({ ...form, cpf_status: e.target.value })}
        />
      </div>
      <div className="flex gap-3 justify-end pt-2">
        <AppButton type="button" variant="outlined" size="md" onClick={onClose}>
          Cancel
        </AppButton>
        <AppButton type="submit" variant="primary" size="md" loading={isSaving}>
          Save Changes
        </AppButton>
      </div>
    </form>
  );
}

/* ── Confirm Probation Modal Content ───────────────────────── */

function ConfirmProbationForm({
  employee,
  employeeId,
  onSaved,
  onClose,
}: {
  employee: EmployeeDetail;
  employeeId: number;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [remarks, setRemarks] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSaving(true);
    try {
      await employeesApi.confirmEmployee(employeeId, remarks || undefined);
      toast.success(`${employee.name} has been confirmed`);
      onSaved();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to confirm employee";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex items-start gap-3 p-4 rounded-lg bg-emerald-50 border border-emerald-200">
        <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-emerald-800">
            Confirm {employee.name} has passed probation?
          </p>
          <p className="text-sm text-emerald-700 mt-1">
            This will change their status from probation to confirmed. The
            change will be recorded in the employee timeline.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-[var(--color-gray-700)]">
          Notes (optional)
        </label>
        <textarea
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
          rows={3}
          className="rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] resize-y"
          placeholder="Optional remarks about the confirmation..."
        />
      </div>

      <div className="flex gap-3 justify-end pt-2">
        <AppButton type="button" variant="outlined" size="md" onClick={onClose}>
          Cancel
        </AppButton>
        <AppButton type="submit" variant="primary" size="md" loading={isSaving}>
          Confirm Employee
        </AppButton>
      </div>
    </form>
  );
}

/* ── Extend Probation Modal Content ────────────────────────── */

function ExtendProbationForm({
  employee,
  employeeId,
  onSaved,
  onClose,
}: {
  employee: EmployeeDetail;
  employeeId: number;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [newEndDate, setNewEndDate] = useState("");
  const [remarks, setRemarks] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!newEndDate) {
      toast.error("Please enter a new probation end date");
      return;
    }
    setIsSaving(true);
    try {
      await employeesApi.extendProbation(
        employeeId,
        newEndDate,
        remarks || undefined,
      );
      toast.success("Probation period extended");
      onSaved();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to extend probation";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-50 border border-amber-200">
        <Clock className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-amber-800">
            Extend probation for {employee.name}
          </p>
          <p className="text-sm text-amber-700 mt-1">
            Current probation end date:{" "}
            <span className="font-semibold">
              {employee.probation_end_date || "Not set"}
            </span>
          </p>
        </div>
      </div>

      <DatePicker
        label="New End Date"
        value={newEndDate}
        onChange={setNewEndDate}
      />

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-[var(--color-gray-700)]">
          Remarks (optional)
        </label>
        <textarea
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
          rows={3}
          className="rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] resize-y"
          placeholder="Reason for extension..."
        />
      </div>

      <div className="flex gap-3 justify-end pt-2">
        <AppButton type="button" variant="outlined" size="md" onClick={onClose}>
          Cancel
        </AppButton>
        <AppButton type="submit" variant="primary" size="md" loading={isSaving}>
          Extend Probation
        </AppButton>
      </div>
    </form>
  );
}

/* ── Terminate Employee Modal Content ──────────────────────── */

function TerminateEmployeeForm({
  employee,
  employeeId,
  onSaved,
  onClose,
}: {
  employee: EmployeeDetail;
  employeeId: number;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!endDate) {
      toast.error("Please enter a termination date");
      return;
    }
    if (!reason.trim()) {
      toast.error("Please enter a reason for termination");
      return;
    }
    setIsSaving(true);
    try {
      await employeesApi.updateEmployee(employeeId, {
        end_date: endDate,
        confirmation_status: "terminated",
        is_active: false,
      } as Partial<EmployeeDetail>);
      toast.success("Employee terminated");
      onSaved();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to terminate employee";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex items-start gap-3 p-4 rounded-lg bg-red-50 border border-red-200">
        <AlertTriangle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-red-800">
            Terminate {employee.name}
          </p>
          <p className="text-sm text-red-700 mt-1">
            This action cannot be undone. The employee will be marked as
            terminated and their access will be revoked.
          </p>
        </div>
      </div>

      <DatePicker
        label="Termination Date"
        value={endDate}
        onChange={setEndDate}
      />

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-[var(--color-gray-700)]">
          Reason for Termination
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={4}
          className="rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] focus:outline-none focus:ring-2 focus:ring-red-500 resize-y"
          placeholder="Provide the reason for termination..."
        />
      </div>

      <div className="flex gap-3 justify-end pt-2">
        <AppButton type="button" variant="outlined" size="md" onClick={onClose}>
          Cancel
        </AppButton>
        <AppButton type="submit" variant="danger" size="md" loading={isSaving}>
          Terminate Employee
        </AppButton>
      </div>
    </form>
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

  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [employee, setEmployee] = useState<EmployeeDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [editModal, setEditModal] = useState<ModalType>(null);

  // Shared data for Overview and Onboarding tabs
  const [leaveBalances, setLeaveBalances] = useState<AdminLeaveBalance[]>([]);
  const [onboardingDocs, setOnboardingDocs] = useState<EmployeeDocument[]>([]);

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

  // Fetch shared data for overview/onboarding
  const fetchSharedData = useCallback(async () => {
    if (!employeeId || isNaN(employeeId)) return;
    try {
      const [balData, docsData] = await Promise.all([
        employeesApi.getEmployeeLeaveBalances(employeeId).catch(() => ({
          balances: [] as AdminLeaveBalance[],
        })),
        employeesApi.listDocuments(employeeId).catch(() => ({
          documents: [] as EmployeeDocument[],
        })),
      ]);
      setLeaveBalances(balData.balances ?? []);
      setOnboardingDocs(docsData.documents ?? []);
    } catch {
      // Non-critical - overview/onboarding degrade gracefully
    }
  }, [employeeId]);

  useEffect(() => {
    fetchEmployee();
    fetchSharedData();
  }, [fetchEmployee, fetchSharedData]);

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

  function handleQuickAction(action: string) {
    switch (action) {
      case "edit_employment":
        setEditModal("employment");
        break;
      case "edit_compensation":
        setEditModal("compensation");
        break;
      case "edit_statutory":
        setEditModal("statutory");
        break;
      case "run_payroll":
        toast.info("Run Payroll - coming soon");
        break;
      case "generate_payslip":
        toast.info("Generate Payslip - coming soon");
        break;
      case "terminate":
        setEditModal("terminate");
        break;
      default:
        break;
    }
  }

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

        {/* Header action buttons (admin) */}
        {isAdmin && (
          <div className="flex items-center gap-2 flex-wrap">
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => setEditModal("employment")}
            >
              <Edit className="h-3.5 w-3.5 mr-1.5" />
              Edit
            </AppButton>
            <AppButton
              variant="danger"
              size="sm"
              onClick={() => setEditModal("terminate")}
            >
              <X className="h-3.5 w-3.5 mr-1.5" />
              Terminate
            </AppButton>
          </div>
        )}
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
      {activeTab === "overview" && (
        <OverviewTab
          employee={employee}
          isAdmin={isAdmin}
          leaveBalances={leaveBalances}
          onAction={handleQuickAction}
        />
      )}
      {activeTab === "personal" && (
        <PersonalTab
          employee={employee}
          isAdmin={isAdmin}
          onSave={handleSaveProfile}
          isSaving={isSaving}
        />
      )}
      {activeTab === "employment" && (
        <EmploymentTab
          employee={employee}
          employeeId={employeeId}
          isAdmin={isAdmin}
          onSave={handleSaveProfile}
          isSaving={isSaving}
          onOpenModal={setEditModal}
        />
      )}
      {activeTab === "compensation" && (
        <CompensationTab
          employeeId={employeeId}
          baseSalary={employee.salary_monthly || 0}
          isAdmin={isAdmin}
        />
      )}
      {activeTab === "statutory" && (
        <StatutoryTab
          employee={employee}
          isAdmin={isAdmin}
          onSave={handleSaveProfile}
          isSaving={isSaving}
        />
      )}
      {activeTab === "leave" && <LeaveTab employeeId={employeeId} />}
      {activeTab === "documents" && (
        <DocumentsTab employeeId={employeeId} isAdmin={isAdmin} />
      )}
      {activeTab === "timeline" && <TimelineTab employeeId={employeeId} />}
      {activeTab === "notes" && (
        <NotesTab employeeId={employeeId} isAdmin={isAdmin} />
      )}
      {activeTab === "onboarding" && (
        <OnboardingTab employee={employee} documents={onboardingDocs} />
      )}
      {activeTab === "custom_fields" && (
        <CustomFieldsTab employeeId={employeeId} isAdmin={isAdmin} />
      )}
      {activeTab === "skills" && (
        <SkillsTab employeeId={employeeId} isAdmin={isAdmin} />
      )}

      {/* ── Modals ──────────────────────────────────────────── */}

      <EditModal
        isOpen={editModal === "employment"}
        onClose={() => setEditModal(null)}
        title="Edit Employment"
      >
        <EditEmploymentForm
          employee={employee}
          employeeId={employeeId}
          onSaved={fetchEmployee}
          onClose={() => setEditModal(null)}
        />
      </EditModal>

      <EditModal
        isOpen={editModal === "compensation"}
        onClose={() => setEditModal(null)}
        title="Edit Compensation"
      >
        <EditCompensationForm
          employee={employee}
          employeeId={employeeId}
          onSaved={fetchEmployee}
          onClose={() => setEditModal(null)}
        />
      </EditModal>

      <EditModal
        isOpen={editModal === "statutory"}
        onClose={() => setEditModal(null)}
        title="Edit Statutory Details"
      >
        <EditStatutoryForm
          employee={employee}
          employeeId={employeeId}
          onSaved={fetchEmployee}
          onClose={() => setEditModal(null)}
        />
      </EditModal>

      <EditModal
        isOpen={editModal === "confirm"}
        onClose={() => setEditModal(null)}
        title="Confirm Probation"
      >
        <ConfirmProbationForm
          employee={employee}
          employeeId={employeeId}
          onSaved={fetchEmployee}
          onClose={() => setEditModal(null)}
        />
      </EditModal>

      <EditModal
        isOpen={editModal === "extend"}
        onClose={() => setEditModal(null)}
        title="Extend Probation"
      >
        <ExtendProbationForm
          employee={employee}
          employeeId={employeeId}
          onSaved={fetchEmployee}
          onClose={() => setEditModal(null)}
        />
      </EditModal>

      <EditModal
        isOpen={editModal === "terminate"}
        onClose={() => setEditModal(null)}
        title="Terminate Employee"
      >
        <TerminateEmployeeForm
          employee={employee}
          employeeId={employeeId}
          onSaved={fetchEmployee}
          onClose={() => setEditModal(null)}
        />
      </EditModal>
    </div>
  );
}
