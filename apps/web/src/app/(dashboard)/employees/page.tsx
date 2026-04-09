"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  AppCard,
  AppButton,
  AppInput,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  Users,
  Plus,
  Search,
  X,
  UserPlus,
  Upload,
  FileSpreadsheet,
  Copy,
  Check,
  CheckCircle,
  RefreshCw,
  Trash2,
  Mail,
  Shield,
  ClipboardList,
  ClipboardCheck,
  ChevronDown,
  ChevronRight,
  Calendar,
  AlertTriangle,
  Loader2,
  Download,
  Clock,
  BarChart3,
  Star,
  MessageSquare,
  Send,
  Monitor,
  UserX,
} from "lucide-react";
import {
  employeesApi,
  type Employee,
  type Invitation,
} from "@/services/api/employees";
import {
  onboardingApi,
  type OnboardingAssignment,
  type OnboardingAnalytics,
  type MyOnboardingProgress,
  type PreboardingTask,
  type PreboardingListResponse,
  type ITProvisioningTask,
  type ITProvisioningListResponse,
  type PulseSurvey,
  type PulseSurveyResponse,
} from "@/services/api/onboarding";
import { TemplateBuilder } from "@/components/onboarding/TemplateBuilder";
import { AssignTemplateModal } from "@/components/onboarding/AssignTemplateModal";

/* ── Tab definitions ─────────────────────────────────────── */

type TabId = "directory" | "onboarding" | "invitations";

interface TabDef {
  id: TabId;
  label: string;
  icon: typeof Users;
}

const TABS: TabDef[] = [
  { id: "directory", label: "Directory", icon: Users },
  { id: "onboarding", label: "Onboarding", icon: ClipboardList },
  { id: "invitations", label: "Invitations", icon: Mail },
];

/* ── Status badge ─────────────────────────────────────────── */

const STATUS_STYLES: Record<string, string> = {
  active: "bg-emerald-50 text-emerald-700 border-emerald-200",
  invited: "bg-amber-50 text-amber-700 border-amber-200",
  inactive:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]",
  terminated: "bg-red-50 text-red-700 border-red-200",
};

function StatusBadge({ status }: { status: string }) {
  const s = status || "active";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[s] || STATUS_STYLES.inactive}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

/* ── Confirmation status badge ────────────────────────────── */

const CONFIRM_STYLES: Record<string, string> = {
  confirmed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  on_probation: "bg-amber-50 text-amber-700 border-amber-200",
  extended: "bg-orange-50 text-orange-700 border-orange-200",
};

function ConfirmBadge({ status }: { status: string | undefined }) {
  if (!status) return null;
  const label = status
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${CONFIRM_STYLES[status] || "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]"}`}
    >
      {label}
    </span>
  );
}

/* ── Onboarding status badge ──────────────────────────────── */

const ONBOARDING_STATUS_STYLES: Record<string, string> = {
  in_progress: "bg-blue-50 text-blue-700 border-blue-200",
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  overdue: "bg-red-50 text-red-700 border-red-200",
  not_started:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]",
  cancelled:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]",
};

function OnboardingStatusBadge({ status }: { status: string }) {
  const s = status || "not_started";
  const label = s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${ONBOARDING_STATUS_STYLES[s] || ONBOARDING_STATUS_STYLES.not_started}`}
    >
      {label}
    </span>
  );
}

/* ── Profile completeness ─────────────────────────────────── */

const QUICK_FIELDS: (keyof Employee)[] = [
  "name",
  "email",
  "department",
  "designation",
  "employment_type",
  "start_date",
];

function ProfileBar({ employee }: { employee: Employee }) {
  let filled = 0;
  for (const key of QUICK_FIELDS) {
    const val = employee[key];
    if (val !== null && val !== undefined && val !== "") filled++;
  }
  const pct = Math.round((filled / QUICK_FIELDS.length) * 100);

  return (
    <div
      className="flex items-center gap-1.5"
      title={`${pct}% profile complete`}
    >
      <div className="w-14 h-1.5 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${pct === 100 ? "bg-emerald-500" : "bg-[var(--color-primary)]"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-[var(--color-gray-400)]">{pct}%</span>
    </div>
  );
}

/* ── Loading skeleton ─────────────────────────────────────── */

function TableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-5 border-b border-[var(--color-gray-100)] last:border-0"
        >
          <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-48 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full" />
          <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* ── Copy-to-clipboard hook ───────────────────────────────── */

function useCopyToClipboard(resetMs = 2000) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const copy = useCallback(
    (text: string, id = "default") => {
      navigator.clipboard.writeText(text).then(() => {
        setCopiedId(id);
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => setCopiedId(null), resetMs);
      });
    },
    [resetMs],
  );

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return { copiedId, copy };
}

/* ── Invite Link Success Modal ────────────────────────────── */

function InviteLinkModal({
  isOpen,
  email,
  inviteUrl,
  onClose,
}: {
  isOpen: boolean;
  email: string;
  inviteUrl: string;
  onClose: () => void;
}) {
  const { copiedId, copy } = useCopyToClipboard();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Check className="h-5 w-5 text-emerald-600" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Invitation Created
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

        <p className="text-sm text-[var(--color-gray-600)] mb-4">
          Share this link with <strong>{email}</strong> via WhatsApp, email, or
          any channel.
        </p>

        <div className="flex items-center gap-2 mb-4">
          <input
            readOnly
            value={inviteUrl}
            className="
              flex-1 rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
              bg-[var(--color-gray-50)] text-[var(--color-gray-700)]
              border-[var(--color-gray-200)] font-mono text-xs
              select-all truncate
            "
            onClick={(e) => (e.target as HTMLInputElement).select()}
          />
          <button
            type="button"
            onClick={() => copy(inviteUrl, "invite-link")}
            className="
              flex items-center justify-center gap-1.5 rounded-[8px] border px-3 py-2 min-h-[44px] text-sm font-medium
              transition-colors whitespace-nowrap
              border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]
              text-[var(--color-gray-700)]
            "
          >
            {copiedId === "invite-link" ? (
              <>
                <Check className="h-4 w-4 text-emerald-600" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                Copy
              </>
            )}
          </button>
        </div>

        <AppButton
          variant="primary"
          size="sm"
          onClick={onClose}
          className="w-full"
        >
          Done
        </AppButton>
      </div>
    </div>
  );
}

/* ── Invite Employee Modal ────────────────────────────────── */

const DEPARTMENT_OPTIONS = [
  "Engineering",
  "Sales",
  "HR",
  "Finance",
  "Operations",
  "Management",
  "Marketing",
] as const;

function InviteEmployeeModal({
  isOpen,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (email: string, inviteUrl: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("employee");
  const [department, setDepartment] = useState("");
  const [designation, setDesignation] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;

    setIsSubmitting(true);
    try {
      const result = await employeesApi.invite({
        email: email.trim(),
        role,
        department: department.trim() || undefined,
        designation: designation.trim() || undefined,
      });
      const submittedEmail = email.trim();
      setEmail("");
      setRole("employee");
      setDepartment("");
      setDesignation("");
      onSuccess(submittedEmail, result.invite_url);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to send invitation";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Invite Employee
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
          <div>
            <label
              htmlFor="invite-email"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Email address
            </label>
            <AppInput
              id="invite-email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="colleague@company.com"
            />
          </div>

          <div>
            <label
              htmlFor="invite-role"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Role
            </label>
            <select
              id="invite-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="
                w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                transition-colors
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                focus:border-[var(--color-surface-input-focus)]
              "
            >
              <option value="employee">Employee</option>
              <option value="hr_manager">HR Manager</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="invite-department"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Department
            </label>
            <select
              id="invite-department"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="
                w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                transition-colors
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                focus:border-[var(--color-surface-input-focus)]
              "
            >
              <option value="">Select department (optional)</option>
              {DEPARTMENT_OPTIONS.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="invite-designation"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Designation
            </label>
            <AppInput
              id="invite-designation"
              value={designation}
              onChange={(e) => setDesignation(e.target.value)}
              placeholder="e.g. Software Engineer, Sales Executive"
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
              Send Invitation
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Invitation status badge ──────────────────────────────── */

const INVITATION_STATUS_STYLES: Record<string, string> = {
  pending: "bg-blue-50 text-blue-700 border-blue-200",
  expired: "bg-red-50 text-red-700 border-red-200",
  accepted: "bg-emerald-50 text-emerald-700 border-emerald-200",
  revoked:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]",
};

function InvitationStatusBadge({ status }: { status: string }) {
  const s = status || "pending";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${INVITATION_STATUS_STYLES[s] || INVITATION_STATUS_STYLES.revoked}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

/* ── Invitation table skeleton ────────────────────────────── */

function InvitationTableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 3 }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-5 border-b border-[var(--color-gray-100)] last:border-0"
        >
          <div className="h-4 w-40 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full" />
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* ── Import CSV Modal ─────────────────────────────────────── */

function ImportCsvModal({
  isOpen,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [step, setStep] = useState<"upload" | "preview" | "done">("upload");
  const [previewRecords, setPreviewRecords] = useState<unknown[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  async function handleFile(files: FileList | null) {
    if (!files || files.length === 0) return;
    const file = files[0];

    if (!file.name.endsWith(".csv")) {
      setError("Please select a CSV file.");
      return;
    }

    setIsProcessing(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const data = await employeesApi.importPreview(formData);
      setPreviewRecords(data.records ?? []);
      setStep("preview");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to process CSV file";
      setError(message);
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleConfirm() {
    setIsProcessing(true);
    setError(null);
    try {
      await employeesApi.importConfirm(previewRecords);
      toast.success(
        "Invitations sent! Share the invite links with your employees to complete registration.",
      );
      setStep("done");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to import employees";
      setError(message);
    } finally {
      setIsProcessing(false);
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
    handleFile(e.dataTransfer.files);
  }

  function handleClose() {
    setStep("upload");
    setPreviewRecords([]);
    setError(null);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={handleClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-lg mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Import Employees from CSV
            </h2>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-[8px] bg-red-50 border border-red-200 text-sm text-red-700">
            {error}
          </div>
        )}

        {step === "upload" && (
          <div>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-[12px] p-10 text-center transition-colors cursor-pointer ${
                isDragOver
                  ? "border-[var(--color-primary)] bg-[var(--color-primary-bg)]"
                  : "border-[var(--color-gray-200)] hover:border-[var(--color-gray-300)]"
              }`}
            >
              <Upload className="h-8 w-8 text-[var(--color-gray-400)] mx-auto mb-3" />
              <p className="text-sm text-[var(--color-gray-600)]">
                {isProcessing
                  ? "Processing CSV..."
                  : "Drop a CSV file here, or click to browse"}
              </p>
              <p className="text-xs text-[var(--color-gray-400)] mt-1">
                Columns: name, email, department, designation, employment_type,
                start_date
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => handleFile(e.target.files)}
              />
            </div>
            <div className="flex justify-end mt-4">
              <AppButton variant="outlined" size="sm" onClick={handleClose}>
                Cancel
              </AppButton>
            </div>
          </div>
        )}

        {step === "preview" && (
          <div>
            <p className="text-sm text-[var(--color-gray-600)] mb-3">
              Found {previewRecords.length} record
              {previewRecords.length !== 1 ? "s" : ""} to import. Please review
              and confirm.
            </p>
            <div className="max-h-60 overflow-y-auto border border-[var(--color-gray-200)] rounded-[8px]">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-gray-50)]">
                    <th className="text-left py-2 px-3 font-medium text-[var(--color-gray-500)]">
                      Name
                    </th>
                    <th className="text-left py-2 px-3 font-medium text-[var(--color-gray-500)]">
                      Email
                    </th>
                    <th className="text-left py-2 px-3 font-medium text-[var(--color-gray-500)]">
                      Department
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {previewRecords.map((rec, i) => {
                    const r = rec as Record<string, string>;
                    return (
                      <tr
                        key={i}
                        className="border-b border-[var(--color-gray-100)] last:border-0"
                      >
                        <td className="py-2 px-3 text-[var(--color-gray-900)]">
                          {r.name || "-"}
                        </td>
                        <td className="py-2 px-3 text-[var(--color-gray-600)]">
                          {r.email || "-"}
                        </td>
                        <td className="py-2 px-3 text-[var(--color-gray-600)]">
                          {r.department || "-"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex gap-3 justify-end mt-4">
              <AppButton
                variant="outlined"
                size="sm"
                onClick={() => {
                  setStep("upload");
                  setPreviewRecords([]);
                }}
              >
                Back
              </AppButton>
              <AppButton
                variant="primary"
                size="sm"
                onClick={handleConfirm}
                loading={isProcessing}
              >
                Import {previewRecords.length} Employee
                {previewRecords.length !== 1 ? "s" : ""}
              </AppButton>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Directory Tab
   ═══════════════════════════════════════════════════════════ */

function DirectoryTab({
  employees,
  isLoading,
  error,
  onRefresh,
  onInvite,
  onImport,
  onAssignOnboarding,
  onTerminate,
}: {
  employees: Employee[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  onInvite: () => void;
  onImport: () => void;
  onAssignOnboarding: (employee: Employee) => void;
  onTerminate: (employee: Employee) => void;
}) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [workPassFilter, setWorkPassFilter] = useState(false);
  const [workPassExpiryMap, setWorkPassExpiryMap] = useState<
    Record<number, string>
  >({});
  const [isLoadingWorkPass, setIsLoadingWorkPass] = useState(false);

  const fetchWorkPassData = useCallback(async () => {
    if (Object.keys(workPassExpiryMap).length > 0) return;
    setIsLoadingWorkPass(true);
    try {
      const map: Record<number, string> = {};
      const detailPromises = employees.map(async (emp) => {
        try {
          const detail = await employeesApi.getEmployee(emp.id);
          if (detail.work_pass_expiry) {
            map[emp.id] = detail.work_pass_expiry;
          }
        } catch {
          // Skip on failure
        }
      });
      await Promise.all(detailPromises);
      setWorkPassExpiryMap(map);
    } finally {
      setIsLoadingWorkPass(false);
    }
  }, [employees, workPassExpiryMap]);

  function handleToggleWorkPassFilter() {
    const newVal = !workPassFilter;
    setWorkPassFilter(newVal);
    if (
      newVal &&
      Object.keys(workPassExpiryMap).length === 0 &&
      employees.length > 0
    ) {
      fetchWorkPassData();
    }
  }

  const filteredEmployees = employees.filter((emp) => {
    const matchesSearch =
      emp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.department.toLowerCase().includes(searchQuery.toLowerCase());
    if (!matchesSearch) return false;
    if (workPassFilter) {
      const expiry = workPassExpiryMap[emp.id];
      if (!expiry) return false;
      const daysLeft = Math.ceil(
        (new Date(expiry).getTime() - Date.now()) / 86400000,
      );
      return daysLeft <= 90;
    }
    return true;
  });

  return (
    <div className="space-y-4">
      {/* Actions bar */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-gray-400)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name, email, or department..."
            className="
              w-full rounded-[8px] border px-3 py-2 pl-9 text-sm min-h-[44px]
              bg-[var(--color-surface-input)] text-[var(--foreground)]
              border-[var(--color-surface-input-border)]
              placeholder:text-[var(--color-gray-400)]
              transition-colors
              focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
              focus:border-[var(--color-surface-input-focus)]
            "
          />
        </div>
        <div className="flex items-center gap-2">
          <AppButton variant="outlined" size="sm" onClick={onImport}>
            <Upload className="h-4 w-4 mr-1" />
            Import CSV
          </AppButton>
          <AppButton variant="primary" size="sm" onClick={onInvite}>
            <Plus className="h-4 w-4 mr-1" />
            Invite Employee
          </AppButton>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleToggleWorkPassFilter}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
            workPassFilter
              ? "bg-amber-100 text-amber-800 border border-amber-300"
              : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:bg-[var(--color-gray-200)] border border-transparent"
          }`}
        >
          <Shield className="h-3.5 w-3.5" />
          Work Pass Expiring Soon
          {isLoadingWorkPass && (
            <span className="ml-1 inline-block h-3 w-3 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
          )}
        </button>
        {workPassFilter && (
          <button
            type="button"
            onClick={() => setWorkPassFilter(false)}
            className="text-xs text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] transition-colors"
          >
            Clear filter
          </button>
        )}
      </div>

      {/* Employee table / states */}
      {isLoading ? (
        <AppCard variant="standard">
          <div className="-mx-5 -my-4">
            <TableSkeleton />
          </div>
        </AppCard>
      ) : error ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={onRefresh}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      ) : employees.length === 0 ? (
        <EmptyState
          icon={<Users className="h-12 w-12" aria-hidden="true" />}
          message="No employees yet"
          description="Invite your first team member to get started."
          action={
            <AppButton variant="primary" size="sm" onClick={onInvite}>
              <Plus className="h-4 w-4 mr-1" />
              Invite Employee
            </AppButton>
          }
        />
      ) : (
        <AppCard variant="standard">
          <div className="-mx-5 -my-4">
            <table className="w-full table-fixed text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)]">
                  <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)] w-[14%]">
                    Name
                  </th>
                  <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)] w-[18%]">
                    Email
                  </th>
                  <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)] w-[12%]">
                    Department
                  </th>
                  <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)] w-[14%]">
                    Designation
                  </th>
                  <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)] w-[11%]">
                    Confirmation
                  </th>
                  <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)] w-[9%]">
                    Profile
                  </th>
                  <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)] w-[8%]">
                    Status
                  </th>
                  <th className="text-right py-3 px-5 font-medium text-[var(--color-gray-500)] w-[14%]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.map((emp) => {
                  const isActive =
                    emp.is_active !== false && emp.status !== "terminated";
                  return (
                    <tr
                      key={emp.id}
                      className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                    >
                      <td
                        className="py-3 px-5 font-medium text-[var(--color-gray-900)] cursor-pointer truncate"
                        onClick={() => router.push(`/employees/${emp.id}`)}
                        title={emp.name}
                      >
                        {emp.name}
                      </td>
                      <td
                        className="py-3 px-3 text-[var(--color-gray-600)] cursor-pointer truncate"
                        onClick={() => router.push(`/employees/${emp.id}`)}
                        title={emp.email}
                      >
                        {emp.email}
                      </td>
                      <td
                        className="py-3 px-3 text-[var(--color-gray-600)] cursor-pointer truncate"
                        onClick={() => router.push(`/employees/${emp.id}`)}
                        title={emp.department}
                      >
                        {emp.department || "-"}
                      </td>
                      <td
                        className="py-3 px-3 text-[var(--color-gray-600)] cursor-pointer truncate"
                        onClick={() => router.push(`/employees/${emp.id}`)}
                        title={emp.designation || ""}
                      >
                        {emp.designation || "-"}
                      </td>
                      <td
                        className="py-3 px-3 text-center cursor-pointer"
                        onClick={() => router.push(`/employees/${emp.id}`)}
                      >
                        <ConfirmBadge status={emp.confirmation_status} />
                      </td>
                      <td
                        className="py-3 px-3 text-center cursor-pointer"
                        onClick={() => router.push(`/employees/${emp.id}`)}
                      >
                        <ProfileBar employee={emp} />
                      </td>
                      <td
                        className="py-3 px-3 text-center cursor-pointer"
                        onClick={() => router.push(`/employees/${emp.id}`)}
                      >
                        <StatusBadge status={emp.status} />
                      </td>
                      <td className="py-3 px-5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onAssignOnboarding(emp);
                            }}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium text-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-colors"
                            title="Assign onboarding template"
                          >
                            <ClipboardCheck className="h-3.5 w-3.5" />
                            Onboard
                          </button>
                          {isActive && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                onTerminate(emp);
                              }}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
                              title="Terminate employee"
                            >
                              <UserX className="h-3.5 w-3.5" />
                              Terminate
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filteredEmployees.length === 0 && employees.length > 0 && (
                  <tr>
                    <td
                      colSpan={8}
                      className="py-8 text-center text-sm text-[var(--color-gray-500)]"
                    >
                      No employees found matching your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </AppCard>
      )}
    </div>
  );
}

/* ── Owner role badge for pre-boarding tasks ─────────────── */

const OWNER_ROLE_STYLES: Record<string, string> = {
  hr: "bg-blue-50 text-blue-700 border-blue-200",
  manager: "bg-purple-50 text-purple-700 border-purple-200",
  it: "bg-cyan-50 text-cyan-700 border-cyan-200",
  office_manager: "bg-amber-50 text-amber-700 border-amber-200",
};

const OWNER_ROLE_LABELS: Record<string, string> = {
  hr: "HR",
  manager: "Manager",
  it: "IT",
  office_manager: "Operations",
};

function OwnerRoleBadge({ role }: { role: string }) {
  const normalised = role.toLowerCase();
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${OWNER_ROLE_STYLES[normalised] || "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]"}`}
    >
      {OWNER_ROLE_LABELS[normalised] || role}
    </span>
  );
}

/* ── Pre-boarding task deadline colour helper ─────────────── */

function getDeadlineStatus(
  task: PreboardingTask,
): "done" | "overdue" | "due_soon" | "normal" {
  if (task.status === "done") return "done";
  if (task.is_overdue) return "overdue";
  if (task.deadline_date) {
    const deadline = new Date(task.deadline_date);
    const now = new Date();
    const daysUntil = Math.ceil(
      (deadline.getTime() - now.getTime()) / 86400000,
    );
    if (daysUntil <= 3) return "due_soon";
  }
  return "normal";
}

/* ── Pre-boarding section inside expanded assignment ──────── */

function PreboardingSection({ employeeId }: { employeeId: number }) {
  const [data, setData] = useState<PreboardingListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [completingId, setCompletingId] = useState<number | null>(null);

  const fetchTasks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await onboardingApi.getPreboarding(employeeId);
      setData(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load pre-boarding tasks.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  async function handleComplete(taskId: number) {
    setCompletingId(taskId);
    try {
      const result = await onboardingApi.completePreboardingTask(taskId);
      // Update local state to reflect the change immediately
      setData((prev) => {
        if (!prev) return prev;
        const updatedTasks = prev.tasks.map((t) =>
          t.id === taskId ? { ...t, ...result.task } : t,
        );
        const pending = updatedTasks.filter(
          (t) => t.status === "pending",
        ).length;
        const done = updatedTasks.filter((t) => t.status === "done").length;
        return {
          tasks: updatedTasks,
          total: updatedTasks.length,
          pending,
          done,
        };
      });
      toast.success("Task marked as done.");
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to complete task. Please try again.";
      toast.error(message);
    } finally {
      setCompletingId(null);
    }
  }

  function formatDeadline(isoDate: string | null): string {
    if (!isoDate) return "-";
    try {
      return new Date(isoDate).toLocaleDateString("en-SG", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return isoDate;
    }
  }

  if (isLoading) {
    return (
      <div className="py-3 text-center">
        <span className="inline-block h-4 w-4 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-3 text-center">
        <p className="text-xs text-[var(--color-error)]">{error}</p>
        <button
          type="button"
          onClick={fetchTasks}
          className="mt-1 text-xs text-[var(--color-primary)] hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data || data.tasks.length === 0) {
    return (
      <p className="text-xs text-[var(--color-gray-500)] py-2">
        No pre-boarding tasks.
      </p>
    );
  }

  return (
    <div>
      {/* Summary counts */}
      <div className="flex items-center gap-3 mb-3">
        <span className="text-xs text-[var(--color-gray-600)]">
          {data.done}/{data.total} completed
        </span>
        {data.pending > 0 && (
          <span className="text-xs text-amber-600 font-medium">
            {data.pending} remaining
          </span>
        )}
      </div>

      {/* Task list */}
      <div className="space-y-1.5">
        {data.tasks.map((task) => {
          const deadlineStatus = getDeadlineStatus(task);
          const isDone = task.status === "done";
          const isCompleting = completingId === task.id;

          return (
            <div
              key={task.id}
              className={`flex items-center gap-3 py-2 px-3 rounded-[8px] border transition-colors ${
                isDone
                  ? "bg-emerald-50/50 border-emerald-100"
                  : deadlineStatus === "overdue"
                    ? "bg-red-50/50 border-red-100"
                    : deadlineStatus === "due_soon"
                      ? "bg-amber-50/50 border-amber-100"
                      : "bg-[var(--color-gray-50)] border-[var(--color-gray-100)]"
              }`}
            >
              {/* Checkbox */}
              <button
                type="button"
                disabled={isDone || isCompleting}
                onClick={() => handleComplete(task.id)}
                className={`h-5 w-5 rounded border flex items-center justify-center flex-shrink-0 transition-colors ${
                  isDone
                    ? "bg-emerald-500 border-emerald-500 cursor-default"
                    : isCompleting
                      ? "border-[var(--color-gray-300)] cursor-wait"
                      : "border-[var(--color-gray-300)] hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] cursor-pointer"
                }`}
                title={isDone ? "Completed" : "Mark as done"}
              >
                {isDone ? (
                  <Check className="h-3 w-3 text-white" />
                ) : isCompleting ? (
                  <Loader2 className="h-3 w-3 text-[var(--color-gray-400)] animate-spin" />
                ) : null}
              </button>

              {/* Task name */}
              <span
                className={`flex-1 text-xs ${
                  isDone
                    ? "text-[var(--color-gray-500)] line-through"
                    : "text-[var(--color-gray-800)]"
                }`}
              >
                {task.task_name}
              </span>

              {/* Owner role badge */}
              <OwnerRoleBadge role={task.owner_role} />

              {/* Deadline */}
              {task.deadline_date && (
                <span
                  className={`inline-flex items-center gap-1 text-[10px] font-medium flex-shrink-0 ${
                    isDone
                      ? "text-[var(--color-gray-400)]"
                      : deadlineStatus === "overdue"
                        ? "text-red-600"
                        : deadlineStatus === "due_soon"
                          ? "text-amber-600"
                          : "text-[var(--color-gray-500)]"
                  }`}
                >
                  {deadlineStatus === "overdue" && !isDone && (
                    <AlertTriangle className="h-3 w-3" />
                  )}
                  <Calendar className="h-3 w-3" />
                  {formatDeadline(task.deadline_date)}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Pre-boarding summary for assignment cards ───────────── */

function PreboardingSummary({ employeeId }: { employeeId: number }) {
  const [summary, setSummary] = useState<{
    done: number;
    total: number;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    onboardingApi
      .getPreboarding(employeeId)
      .then((result) => {
        if (!cancelled) {
          setSummary({ done: result.done, total: result.total });
        }
      })
      .catch(() => {
        // Silently fail -- this is a supplementary indicator
      });
    return () => {
      cancelled = true;
    };
  }, [employeeId]);

  if (!summary || summary.total === 0) return null;

  const pct = Math.round((summary.done / summary.total) * 100);
  const allDone = summary.done === summary.total;

  return (
    <div
      className="flex items-center gap-1.5 flex-shrink-0"
      title={`Pre-boarding: ${summary.done}/${summary.total} tasks done`}
    >
      <ClipboardCheck
        className={`h-3.5 w-3.5 ${allDone ? "text-emerald-500" : "text-[var(--color-gray-400)]"}`}
      />
      <div className="w-10 h-1.5 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${allDone ? "bg-emerald-500" : "bg-[var(--color-primary)]"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-[var(--color-gray-500)] whitespace-nowrap">
        {summary.done}/{summary.total}
      </span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   IT Provisioning Section (admin — inside expanded assignment)
   ═══════════════════════════════════════════════════════════ */

const IT_STATUS_OPTIONS = ["pending", "in_progress", "completed"] as const;

const IT_STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  in_progress: "bg-blue-50 text-blue-700 border-blue-200",
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  done: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const IT_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  in_progress: "In Progress",
  completed: "Completed",
  done: "Completed",
};

function ITProvisioningSection({ employeeId }: { employeeId: number }) {
  const [data, setData] = useState<ITProvisioningListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const fetchTasks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await onboardingApi.getITProvisioning(employeeId);
      setData(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load IT provisioning tasks.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  async function handleStatusChange(taskId: number, newStatus: string) {
    setUpdatingId(taskId);
    try {
      const result = await onboardingApi.updateITProvisioning(taskId, {
        status: newStatus,
      });
      setData((prev) => {
        if (!prev) return prev;
        const updatedTasks = prev.tasks.map((t) =>
          t.id === taskId ? { ...t, ...result.task } : t,
        );
        return {
          tasks: updatedTasks,
          total: updatedTasks.length,
          pending: updatedTasks.filter((t) => t.status === "pending").length,
          in_progress: updatedTasks.filter((t) => t.status === "in_progress")
            .length,
          completed: updatedTasks.filter(
            (t) => t.status === "completed" || t.status === "done",
          ).length,
        };
      });
      toast.success(
        `Task updated to ${IT_STATUS_LABELS[newStatus] || newStatus}.`,
      );
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to update task. Please try again.";
      toast.error(message);
    } finally {
      setUpdatingId(null);
    }
  }

  function formatDeadline(isoDate: string | null): string {
    if (!isoDate) return "-";
    try {
      return new Date(isoDate).toLocaleDateString("en-SG", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return isoDate;
    }
  }

  if (isLoading) {
    return (
      <div className="py-3 text-center">
        <span className="inline-block h-4 w-4 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-3 text-center">
        <p className="text-xs text-[var(--color-error)]">{error}</p>
        <button
          type="button"
          onClick={fetchTasks}
          className="mt-1 text-xs text-[var(--color-primary)] hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data || data.tasks.length === 0) {
    return (
      <p className="text-xs text-[var(--color-gray-500)] py-2">
        No IT provisioning tasks.
      </p>
    );
  }

  return (
    <div>
      {/* Summary counts */}
      <div className="flex items-center gap-3 mb-3">
        <span className="text-xs text-[var(--color-gray-600)]">
          {data.completed}/{data.total} completed
        </span>
        {data.in_progress > 0 && (
          <span className="text-xs text-blue-600 font-medium">
            {data.in_progress} in progress
          </span>
        )}
        {data.pending > 0 && (
          <span className="text-xs text-amber-600 font-medium">
            {data.pending} pending
          </span>
        )}
      </div>

      {/* Task list */}
      <div className="space-y-1.5">
        {data.tasks.map((task) => {
          const isDone = task.status === "completed" || task.status === "done";
          const isOverdue = task.is_overdue && !isDone;
          const isUpdating = updatingId === task.id;

          return (
            <div
              key={task.id}
              className={`flex items-center gap-3 py-2 px-3 rounded-[8px] border transition-colors ${
                isDone
                  ? "bg-emerald-50/50 border-emerald-100"
                  : isOverdue
                    ? "bg-red-50/50 border-red-100"
                    : "bg-[var(--color-gray-50)] border-[var(--color-gray-100)]"
              }`}
            >
              {/* Tool name */}
              <span
                className={`flex-1 text-xs ${
                  isDone
                    ? "text-[var(--color-gray-500)] line-through"
                    : "text-[var(--color-gray-800)]"
                }`}
              >
                {task.task_name}
              </span>

              {/* Category badge */}
              {task.category && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border bg-[var(--color-gray-50)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]">
                  {task.category}
                </span>
              )}

              {/* SLA / trigger */}
              {task.trigger && (
                <span className="text-[10px] text-[var(--color-gray-500)] flex-shrink-0">
                  SLA: {task.trigger}
                </span>
              )}

              {/* Deadline + overdue */}
              {task.deadline_date && (
                <span
                  className={`inline-flex items-center gap-1 text-[10px] font-medium flex-shrink-0 ${
                    isDone
                      ? "text-[var(--color-gray-400)]"
                      : isOverdue
                        ? "text-red-600"
                        : "text-[var(--color-gray-500)]"
                  }`}
                >
                  {isOverdue && <AlertTriangle className="h-3 w-3" />}
                  <Calendar className="h-3 w-3" />
                  {formatDeadline(task.deadline_date)}
                </span>
              )}

              {/* Status dropdown */}
              {isDone ? (
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium border ${IT_STATUS_STYLES.completed}`}
                >
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Completed
                </span>
              ) : (
                <select
                  value={task.status}
                  disabled={isUpdating}
                  onChange={(e) => handleStatusChange(task.id, e.target.value)}
                  className={`text-[10px] font-medium rounded border px-2 py-0.5 cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)] ${
                    isUpdating ? "opacity-50 cursor-wait" : ""
                  } ${IT_STATUS_STYLES[task.status] || "bg-[var(--color-gray-50)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]"}`}
                >
                  {IT_STATUS_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {IT_STATUS_LABELS[opt]}
                    </option>
                  ))}
                </select>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Pulse Survey Section (admin — inside expanded assignment)
   ═══════════════════════════════════════════════════════════ */

function ScoreBadge({ score }: { score: number }) {
  let colorClass = "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (score < 3.5) {
    colorClass = "bg-red-50 text-red-700 border-red-200";
  } else if (score < 4) {
    colorClass = "bg-amber-50 text-amber-700 border-amber-200";
  }
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}
    >
      <Star className="h-3 w-3 fill-current" />
      {score.toFixed(1)}
    </span>
  );
}

function PulseSurveySection({
  assignmentId,
  employeeId,
}: {
  assignmentId: number;
  employeeId: number;
}) {
  const [surveys, setSurveys] = useState<PulseSurvey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [triggerType, setTriggerType] = useState<string | null>(null);
  const [expandedSurveyId, setExpandedSurveyId] = useState<number | null>(null);
  const [surveyResponses, setSurveyResponses] = useState<PulseSurveyResponse[]>(
    [],
  );
  const [isLoadingResponses, setIsLoadingResponses] = useState(false);

  const fetchSurveys = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await onboardingApi.listSurveys();
      const filtered = (data.surveys ?? []).filter(
        (s) => s.assignment_id === assignmentId,
      );
      setSurveys(filtered);
    } catch {
      /* Non-critical */
    } finally {
      setIsLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => {
    fetchSurveys();
  }, [fetchSurveys]);

  async function handleTrigger(surveyType: string) {
    setTriggerType(surveyType);
    try {
      await onboardingApi.triggerSurvey({
        employee_id: employeeId,
        assignment_id: assignmentId,
        survey_type: surveyType,
      });
      toast.success(
        `${surveyType === "day_60" ? "Day 60" : "Day 30"} survey sent.`,
      );
      fetchSurveys();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to trigger survey.";
      toast.error(message);
    } finally {
      setTriggerType(null);
    }
  }

  async function handleExpandResults(surveyId: number) {
    if (expandedSurveyId === surveyId) {
      setExpandedSurveyId(null);
      setSurveyResponses([]);
      return;
    }
    setExpandedSurveyId(surveyId);
    setIsLoadingResponses(true);
    try {
      const data = await onboardingApi.getSurveyResults(surveyId);
      setSurveyResponses(data.responses ?? []);
    } catch {
      toast.error("Unable to load survey responses.");
    } finally {
      setIsLoadingResponses(false);
    }
  }

  const hasDay30 = surveys.some((s) => s.survey_type === "day_30");
  const hasDay60 = surveys.some((s) => s.survey_type === "day_60");

  if (isLoading) {
    return (
      <div className="py-2">
        <div className="animate-pulse h-4 w-32 bg-[var(--color-gray-200)] rounded" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-[var(--color-gray-500)]" />
          <h4 className="text-xs font-semibold text-[var(--color-gray-700)] uppercase tracking-wider">
            Pulse Surveys
          </h4>
        </div>
        <div className="flex items-center gap-2">
          {!hasDay30 && (
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => handleTrigger("day_30")}
              disabled={triggerType !== null}
            >
              {triggerType === "day_30" ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <Send className="h-3 w-3 mr-1" />
              )}
              Send Day 30
            </AppButton>
          )}
          {!hasDay60 && (
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => handleTrigger("day_60")}
              disabled={triggerType !== null}
            >
              {triggerType === "day_60" ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <Send className="h-3 w-3 mr-1" />
              )}
              Send Day 60
            </AppButton>
          )}
        </div>
      </div>

      {surveys.length === 0 ? (
        <p className="text-xs text-[var(--color-gray-500)]">
          No pulse surveys sent yet.
        </p>
      ) : (
        <div className="space-y-2">
          {surveys.map((s) => {
            const isCompleted = s.status === "completed";
            const isExpanded = expandedSurveyId === s.id;
            const typeLabel = s.survey_type === "day_60" ? "Day 60" : "Day 30";

            return (
              <div
                key={s.id}
                className="border border-[var(--color-gray-100)] rounded-lg"
              >
                <button
                  type="button"
                  onClick={() =>
                    isCompleted ? handleExpandResults(s.id) : undefined
                  }
                  disabled={!isCompleted}
                  className={`w-full text-left flex items-center gap-3 px-3 py-2.5 ${
                    isCompleted
                      ? "hover:bg-[var(--color-gray-50)] cursor-pointer"
                      : "cursor-default"
                  } transition-colors rounded-lg`}
                >
                  <span className="text-xs font-medium text-[var(--color-gray-700)] flex-shrink-0">
                    {typeLabel}
                  </span>

                  {isCompleted ? (
                    <>
                      <ScoreBadge score={s.average_score} />
                      {s.flagged && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-50 text-red-700 border border-red-200">
                          <AlertTriangle className="h-3 w-3" />
                          Disengagement risk
                        </span>
                      )}
                      <span className="flex-1" />
                      {isExpanded ? (
                        <ChevronDown className="h-3 w-3 text-[var(--color-gray-400)]" />
                      ) : (
                        <ChevronRight className="h-3 w-3 text-[var(--color-gray-400)]" />
                      )}
                    </>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-500)]">
                      Pending
                    </span>
                  )}
                </button>

                {isExpanded && isCompleted && (
                  <div className="px-3 pb-3 border-t border-[var(--color-gray-100)]">
                    {isLoadingResponses ? (
                      <div className="py-3 text-center">
                        <span className="inline-block h-4 w-4 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
                      </div>
                    ) : (
                      <div className="space-y-2 mt-2">
                        {surveyResponses.map((r) => (
                          <div key={r.id} className="flex items-start gap-3">
                            <span className="text-xs text-[var(--color-gray-500)] w-5 text-right flex-shrink-0 pt-0.5">
                              Q{r.question_number}
                            </span>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs text-[var(--color-gray-700)]">
                                {r.question_text}
                              </p>
                              <div className="flex items-center gap-1 mt-0.5">
                                {[1, 2, 3, 4, 5].map((star) => (
                                  <Star
                                    key={star}
                                    className={`h-3 w-3 ${
                                      star <= r.score
                                        ? "fill-amber-400 text-amber-400"
                                        : "fill-none text-[var(--color-gray-300)]"
                                    }`}
                                  />
                                ))}
                              </div>
                              {r.comment && (
                                <p className="text-[11px] text-[var(--color-gray-500)] mt-0.5 italic">
                                  &ldquo;{r.comment}&rdquo;
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Onboarding Tab
   ═══════════════════════════════════════════════════════════ */

function OnboardingTab({
  refreshKey,
}: {
  /** Increment from parent to trigger assignment list re-fetch. */
  refreshKey?: number;
}) {
  const [assignments, setAssignments] = useState<OnboardingAssignment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedDetail, setExpandedDetail] =
    useState<MyOnboardingProgress | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [analytics, setAnalytics] = useState<OnboardingAnalytics | null>(null);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(true);

  /* ── Filter state ───────────────────────────────────────── */
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [isExporting, setIsExporting] = useState(false);

  const fetchAnalytics = useCallback(async () => {
    setIsLoadingAnalytics(true);
    try {
      const data = await onboardingApi.getAnalytics();
      setAnalytics(data);
    } catch {
      // Analytics are supplementary — failing silently is acceptable
      setAnalytics(null);
    } finally {
      setIsLoadingAnalytics(false);
    }
  }, []);

  const fetchAssignments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await onboardingApi.listAssignments();
      setAssignments(data.assignments ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load onboarding data. Please try again.";
      setError(message);
      setAssignments([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAssignments();
    fetchAnalytics();
  }, [fetchAssignments, fetchAnalytics]);

  /* Re-fetch assignments + analytics when parent signals (e.g. after assigning a template) */
  useEffect(() => {
    if (refreshKey !== undefined && refreshKey > 0) {
      fetchAssignments();
      fetchAnalytics();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  async function handleExpand(assignment: OnboardingAssignment) {
    if (expandedId === assignment.id) {
      setExpandedId(null);
      setExpandedDetail(null);
      return;
    }

    setExpandedId(assignment.id);
    setExpandedDetail(null);
    setIsLoadingDetail(true);
    try {
      const detail = await onboardingApi.getAssignment(assignment.id);
      setExpandedDetail(detail);
    } catch {
      toast.error("Unable to load onboarding details.");
    } finally {
      setIsLoadingDetail(false);
    }
  }

  function formatDate(isoDate: string | null | undefined): string {
    if (!isoDate) return "-";
    try {
      return new Date(isoDate).toLocaleDateString("en-SG", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return isoDate;
    }
  }

  /** Determine effective status, flagging overdue assignments. */
  function getEffectiveStatus(a: OnboardingAssignment): string {
    if (a.status === "completed" || a.status === "cancelled") return a.status;
    if (a.due_date) {
      const dueDate = new Date(a.due_date);
      if (dueDate < new Date() && a.completion_percentage < 100) {
        return "overdue";
      }
    }
    return a.status;
  }

  /* ── Derive unique departments from assignment data ─────── */
  const departments = Array.from(
    new Set(
      assignments
        .map((a) => a.department)
        .filter((d): d is string => Boolean(d)),
    ),
  ).sort();

  /* ── Client-side filtering ─────────────────────────────── */
  const filteredAssignments = assignments.filter((a) => {
    // Status filter
    if (statusFilter) {
      const effective = getEffectiveStatus(a);
      if (effective !== statusFilter) return false;
    }
    // Department filter
    if (departmentFilter) {
      const dept = a.department ?? "";
      if (dept.toLowerCase() !== departmentFilter.toLowerCase()) return false;
    }
    // Search by employee name
    if (searchQuery) {
      const name = (a.employee_name ?? "").toLowerCase();
      if (!name.includes(searchQuery.toLowerCase())) return false;
    }
    return true;
  });

  /* ── Export handler ─────────────────────────────────────── */
  async function handleExport() {
    setIsExporting(true);
    try {
      await onboardingApi.exportAssignments({
        status: statusFilter || undefined,
        department: departmentFilter || undefined,
      });
      toast.success("Export downloaded successfully.");
    } catch {
      toast.error("Unable to export assignments. Please try again.");
    } finally {
      setIsExporting(false);
    }
  }

  const hasActiveFilters = Boolean(
    searchQuery || statusFilter || departmentFilter,
  );

  /* ── Analytics colour helper ──────────────────────────────── */
  function rateColor(rate: number): string {
    if (rate >= 80) return "text-emerald-600";
    if (rate >= 60) return "text-amber-600";
    return "text-red-600";
  }

  function rateBg(rate: number): string {
    if (rate >= 80) return "bg-emerald-50";
    if (rate >= 60) return "bg-amber-50";
    return "bg-red-50";
  }

  return (
    <div className="space-y-6">
      {/* Template Builder (upload + list) */}
      <TemplateBuilder />

      {/* Analytics summary cards */}
      {isLoadingAnalytics ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((n) => (
            <AppCard key={n} variant="flat">
              <div className="animate-pulse py-2">
                <div className="h-3 w-20 bg-[var(--color-gray-200)] rounded mb-3" />
                <div className="h-7 w-12 bg-[var(--color-gray-200)] rounded" />
              </div>
            </AppCard>
          ))}
        </div>
      ) : analytics && analytics.total_assignments > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Total Assignments */}
          <AppCard variant="flat">
            <div className="flex items-start gap-3 py-1">
              <div className="rounded-lg bg-blue-50 p-2 flex-shrink-0">
                <ClipboardList className="h-4 w-4 text-blue-600" />
              </div>
              <div>
                <p className="text-xs font-medium text-[var(--color-gray-500)]">
                  Total Assignments
                </p>
                <p className="text-xl font-semibold text-[var(--color-gray-900)] mt-0.5">
                  {analytics.total_assignments}
                </p>
                <p className="text-[10px] text-[var(--color-gray-400)] mt-0.5">
                  {analytics.in_progress} in progress
                </p>
              </div>
            </div>
          </AppCard>

          {/* Completion Rate */}
          <AppCard variant="flat">
            <div className="flex items-start gap-3 py-1">
              <div
                className={`rounded-lg p-2 flex-shrink-0 ${rateBg(analytics.completion_rate)}`}
              >
                <CheckCircle
                  className={`h-4 w-4 ${rateColor(analytics.completion_rate)}`}
                />
              </div>
              <div>
                <p className="text-xs font-medium text-[var(--color-gray-500)]">
                  Completion Rate
                </p>
                <p
                  className={`text-xl font-semibold mt-0.5 ${rateColor(analytics.completion_rate)}`}
                >
                  {analytics.completion_rate}%
                </p>
                <p className="text-[10px] text-[var(--color-gray-400)] mt-0.5">
                  {analytics.completed} of {analytics.total_assignments}{" "}
                  completed
                </p>
              </div>
            </div>
          </AppCard>

          {/* Avg Days to Complete */}
          <AppCard variant="flat">
            <div className="flex items-start gap-3 py-1">
              <div className="rounded-lg bg-violet-50 p-2 flex-shrink-0">
                <Clock className="h-4 w-4 text-violet-600" />
              </div>
              <div>
                <p className="text-xs font-medium text-[var(--color-gray-500)]">
                  Avg Days to Complete
                </p>
                <p className="text-xl font-semibold text-[var(--color-gray-900)] mt-0.5">
                  {analytics.avg_completion_days > 0
                    ? analytics.avg_completion_days
                    : "\u2014"}
                </p>
                <p className="text-[10px] text-[var(--color-gray-400)] mt-0.5">
                  {analytics.completed > 0
                    ? `across ${analytics.completed} completed`
                    : "no completions yet"}
                </p>
              </div>
            </div>
          </AppCard>

          {/* Overdue */}
          <AppCard variant="flat">
            <div className="flex items-start gap-3 py-1">
              <div
                className={`rounded-lg p-2 flex-shrink-0 ${analytics.overdue > 0 ? "bg-red-50" : "bg-emerald-50"}`}
              >
                <AlertTriangle
                  className={`h-4 w-4 ${analytics.overdue > 0 ? "text-red-600" : "text-emerald-600"}`}
                />
              </div>
              <div>
                <p className="text-xs font-medium text-[var(--color-gray-500)]">
                  Overdue
                </p>
                <p
                  className={`text-xl font-semibold mt-0.5 ${analytics.overdue > 0 ? "text-red-600" : "text-emerald-600"}`}
                >
                  {analytics.overdue}
                </p>
                <p className="text-[10px] text-[var(--color-gray-400)] mt-0.5">
                  {analytics.overdue > 0 ? "need attention" : "all on track"}
                </p>
              </div>
            </div>
          </AppCard>
        </div>
      ) : null}

      {/* Divider */}
      <div className="border-t border-[var(--color-gray-200)]" />

      {/* Assignments section */}
      <div>
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-gray-800)]">
              Onboarding Assignments
            </h3>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
              Track employee onboarding progress
            </p>
          </div>
          <AppButton
            variant="outlined"
            size="sm"
            onClick={handleExport}
            disabled={isExporting || assignments.length === 0}
          >
            {isExporting ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Download className="h-4 w-4 mr-1" />
            )}
            Export CSV
          </AppButton>
        </div>

        {/* Filters bar */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-gray-400)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by employee name..."
              className="
                w-full rounded-[8px] border px-3 py-2 pl-9 text-sm min-h-[36px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                placeholder:text-[var(--color-gray-400)]
                transition-colors
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                focus:border-[var(--color-surface-input-focus)]
              "
            />
          </div>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="
              rounded-[8px] border px-3 py-2 text-sm min-h-[36px]
              bg-[var(--color-surface-input)] text-[var(--foreground)]
              border-[var(--color-surface-input-border)]
              transition-colors
              focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
              focus:border-[var(--color-surface-input-focus)]
            "
          >
            <option value="">All Statuses</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="overdue">Overdue</option>
            <option value="cancelled">Cancelled</option>
          </select>

          {/* Department filter */}
          {departments.length > 0 && (
            <select
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="
                rounded-[8px] border px-3 py-2 text-sm min-h-[36px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                transition-colors
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                focus:border-[var(--color-surface-input-focus)]
              "
            >
              <option value="">All Departments</option>
              {departments.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          )}

          {/* Clear filters */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery("");
                setStatusFilter("");
                setDepartmentFilter("");
              }}
              className="inline-flex items-center gap-1 px-2 py-1.5 rounded-md text-xs font-medium text-[var(--color-gray-600)] hover:bg-[var(--color-gray-100)] transition-colors"
            >
              <X className="h-3 w-3" />
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <AppCard variant="standard">
          <div className="-mx-5 -my-4">
            <TableSkeleton />
          </div>
        </AppCard>
      ) : error ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={fetchAssignments}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      ) : assignments.length === 0 ? (
        <EmptyState
          icon={<ClipboardList className="h-12 w-12" aria-hidden="true" />}
          message="No employees are currently onboarding"
          description="Assign a template from the Directory tab to start tracking onboarding progress."
        />
      ) : filteredAssignments.length === 0 ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-gray-500)] mb-3">
              No assignments match the current filters.
            </p>
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => {
                setSearchQuery("");
                setStatusFilter("");
                setDepartmentFilter("");
              }}
            >
              Clear filters
            </AppButton>
          </div>
        </AppCard>
      ) : (
        <div className="space-y-3">
          {filteredAssignments.map((assignment) => {
            const isExpanded = expandedId === assignment.id;
            const effectiveStatus = getEffectiveStatus(assignment);
            const pct = assignment.completion_percentage;

            return (
              <AppCard key={assignment.id} variant="standard">
                {/* Summary row */}
                <button
                  type="button"
                  onClick={() => handleExpand(assignment)}
                  className="w-full text-left flex items-center gap-4 -mx-5 -my-4 px-5 py-4 hover:bg-[var(--color-gray-50)] transition-colors rounded-[12px]"
                >
                  {/* Expand chevron */}
                  <div className="flex-shrink-0">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-[var(--color-gray-400)]" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-[var(--color-gray-400)]" />
                    )}
                  </div>

                  {/* Employee name + template */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                      {assignment.employee_name ||
                        `Employee #${assignment.employee_id}`}
                    </p>
                    <p className="text-xs text-[var(--color-gray-500)] truncate">
                      {assignment.template_name ||
                        `Template #${assignment.template_id}`}
                      {assignment.due_date
                        ? ` \u00B7 Due ${formatDate(assignment.due_date)}`
                        : ""}
                    </p>
                  </div>

                  {/* Pre-boarding summary */}
                  <PreboardingSummary employeeId={assignment.employee_id} />

                  {/* Progress bar */}
                  <div className="flex items-center gap-2 flex-shrink-0 w-36">
                    <div className="flex-1 h-2 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          pct === 100
                            ? "bg-emerald-500"
                            : effectiveStatus === "overdue"
                              ? "bg-red-500"
                              : "bg-[var(--color-primary)]"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-[var(--color-gray-600)] w-9 text-right">
                      {pct}%
                    </span>
                  </div>

                  {/* Status */}
                  <div className="flex-shrink-0">
                    <OnboardingStatusBadge status={effectiveStatus} />
                  </div>
                </button>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-[var(--color-gray-100)]">
                    {isLoadingDetail ? (
                      <div className="py-4 text-center">
                        <span className="inline-block h-5 w-5 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
                      </div>
                    ) : expandedDetail?.assignment ? (
                      <div className="space-y-3">
                        {(expandedDetail.assignment.modules ?? []).map(
                          (mod) => {
                            /* getAssignment uses "steps_progress" key; normalise */
                            const stepsList =
                              mod.steps_progress ?? mod.steps ?? [];
                            return (
                              <div key={mod.id ?? mod.module_id}>
                                <div className="flex items-center gap-2 mb-2">
                                  <h4 className="text-xs font-semibold text-[var(--color-gray-700)] uppercase tracking-wider">
                                    {mod.name ?? mod.module_name}
                                  </h4>
                                  {mod.is_mandatory && (
                                    <span className="text-[10px] font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">
                                      Required
                                    </span>
                                  )}
                                  {mod.estimated_duration_minutes ? (
                                    <span className="text-[10px] text-[var(--color-gray-400)]">
                                      {mod.estimated_duration_minutes} min
                                    </span>
                                  ) : null}
                                </div>
                                <div className="space-y-1 ml-2">
                                  {stepsList.map((sp) => {
                                    const isComplete =
                                      sp.status === "completed";
                                    return (
                                      <div
                                        key={sp.id}
                                        className="flex items-center gap-2 py-1"
                                      >
                                        <div
                                          className={`h-4 w-4 rounded-full border flex items-center justify-center flex-shrink-0 ${
                                            isComplete
                                              ? "bg-emerald-500 border-emerald-500"
                                              : "border-[var(--color-gray-300)]"
                                          }`}
                                        >
                                          {isComplete && (
                                            <Check className="h-2.5 w-2.5 text-white" />
                                          )}
                                        </div>
                                        <span
                                          className={`text-xs ${
                                            isComplete
                                              ? "text-[var(--color-gray-500)] line-through"
                                              : "text-[var(--color-gray-700)]"
                                          }`}
                                        >
                                          {sp.step_title}
                                        </span>
                                        {sp.step_type && (
                                          <span className="text-[10px] text-[var(--color-gray-400)] bg-[var(--color-gray-50)] rounded px-1.5 py-0.5">
                                            {sp.step_type.replace(/_/g, " ")}
                                          </span>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            );
                          },
                        )}

                        {/* Pre-boarding Tasks */}
                        <div className="pt-3 border-t border-[var(--color-gray-100)]">
                          <div className="flex items-center gap-2 mb-3">
                            <ClipboardCheck className="h-4 w-4 text-[var(--color-gray-500)]" />
                            <h4 className="text-xs font-semibold text-[var(--color-gray-700)] uppercase tracking-wider">
                              Pre-boarding Tasks
                            </h4>
                          </div>
                          <PreboardingSection
                            employeeId={assignment.employee_id}
                          />
                        </div>

                        {/* IT Provisioning */}
                        <div className="pt-3 border-t border-[var(--color-gray-100)]">
                          <div className="flex items-center gap-2 mb-3">
                            <Monitor className="h-4 w-4 text-[var(--color-gray-500)]" />
                            <h4 className="text-xs font-semibold text-[var(--color-gray-700)] uppercase tracking-wider">
                              IT Provisioning
                            </h4>
                          </div>
                          <ITProvisioningSection
                            employeeId={assignment.employee_id}
                          />
                        </div>

                        {/* Pulse Surveys */}
                        <div className="pt-3 border-t border-[var(--color-gray-100)]">
                          <PulseSurveySection
                            assignmentId={assignment.id}
                            employeeId={assignment.employee_id}
                          />
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-[var(--color-gray-500)] text-center py-4">
                        No module details available.
                      </p>
                    )}
                  </div>
                )}
              </AppCard>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Terminate Employee Modal
   ═══════════════════════════════════════════════════════════ */

const EXIT_TYPE_OPTIONS = [
  { value: "termination", label: "Termination" },
  { value: "resignation", label: "Resignation" },
  { value: "retrenchment", label: "Retrenchment" },
  { value: "contract_end", label: "Contract End" },
] as const;

function TerminateEmployeeModal({
  isOpen,
  employee,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  employee: Employee | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [exitType, setExitType] = useState("termination");
  const [lastWorkingDay, setLastWorkingDay] = useState("");
  const [reason, setReason] = useState("");
  const [noticeServed, setNoticeServed] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  if (!isOpen || !employee) return null;

  const canSubmit =
    exitType && lastWorkingDay && confirmText.toLowerCase() === "terminate";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!employee || !canSubmit) return;

    setIsSubmitting(true);
    try {
      await employeesApi.processExit(employee.id, {
        exit_type: exitType,
        last_working_day: lastWorkingDay,
        reason: reason.trim() || undefined,
        notice_served: noticeServed,
      });
      toast.success(`Exit processed for ${employee.name}.`);
      setExitType("termination");
      setLastWorkingDay("");
      setReason("");
      setNoticeServed(false);
      setConfirmText("");
      onSuccess();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to process employee exit";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleClose() {
    setExitType("termination");
    setLastWorkingDay("");
    setReason("");
    setNoticeServed(false);
    setConfirmText("");
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={handleClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <UserX className="h-5 w-5 text-red-600" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Process Employee Exit
            </h2>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>

        <div className="mb-4 p-3 rounded-[8px] bg-red-50 border border-red-200">
          <p className="text-sm text-red-700">
            You are about to process the exit for{" "}
            <strong>{employee.name}</strong>. This will deactivate their account
            and calculate the final settlement.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="exit-type"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Exit Type
            </label>
            <select
              id="exit-type"
              value={exitType}
              onChange={(e) => setExitType(e.target.value)}
              className="
                w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                transition-colors
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                focus:border-[var(--color-surface-input-focus)]
              "
            >
              {EXIT_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="last-working-day"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Last Working Day
            </label>
            <input
              id="last-working-day"
              type="date"
              value={lastWorkingDay}
              onChange={(e) => setLastWorkingDay(e.target.value)}
              className="
                w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                transition-colors
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                focus:border-[var(--color-surface-input-focus)]
              "
            />
          </div>

          <div>
            <label
              htmlFor="exit-reason"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Reason (optional)
            </label>
            <textarea
              id="exit-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              placeholder="Reason for exit..."
              className="
                w-full rounded-[8px] border px-3 py-2 text-sm
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                placeholder:text-[var(--color-gray-400)]
                transition-colors resize-none
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                focus:border-[var(--color-surface-input-focus)]
              "
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              id="notice-served"
              type="checkbox"
              checked={noticeServed}
              onChange={(e) => setNoticeServed(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
            />
            <label
              htmlFor="notice-served"
              className="text-sm text-[var(--color-gray-700)]"
            >
              Notice period has been served
            </label>
          </div>

          <div>
            <label
              htmlFor="confirm-terminate"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Type <strong>terminate</strong> to confirm
            </label>
            <AppInput
              id="confirm-terminate"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="terminate"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <AppButton
              type="button"
              variant="outlined"
              size="sm"
              onClick={handleClose}
              className="flex-1"
            >
              Cancel
            </AppButton>
            <AppButton
              type="submit"
              variant="primary"
              size="sm"
              loading={isSubmitting}
              disabled={!canSubmit}
              className="flex-1 !bg-red-600 hover:!bg-red-700 !border-red-600 disabled:!bg-red-300 disabled:!border-red-300"
            >
              Process Exit
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Invitations Tab
   ═══════════════════════════════════════════════════════════ */

function InvitationsTab({
  invitations,
  isLoading,
  error,
  onRefresh,
}: {
  invitations: Invitation[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}) {
  const { copiedId, copy } = useCopyToClipboard();
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  function formatDate(isoDate: string): string {
    try {
      return new Date(isoDate).toLocaleDateString("en-SG", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return isoDate;
    }
  }

  async function handleResend(inv: Invitation) {
    setActionLoading(`resend-${inv.id}`);
    try {
      const result = await employeesApi.resendInvitation(inv.id);
      copy(result.invite_url, `resend-${inv.id}`);
      toast.success("Invitation resent — link copied to clipboard");
      onRefresh();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to resend invitation";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleRevoke(inv: Invitation) {
    setActionLoading(`revoke-${inv.id}`);
    try {
      await employeesApi.revokeInvitation(inv.id);
      toast.success("Invitation revoked");
      onRefresh();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to revoke invitation";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  if (isLoading) {
    return (
      <AppCard variant="standard">
        <div className="-mx-5 -my-4">
          <InvitationTableSkeleton />
        </div>
      </AppCard>
    );
  }

  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={onRefresh}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  if (invitations.length === 0) {
    return (
      <EmptyState
        icon={<Mail className="h-12 w-12" aria-hidden="true" />}
        message="No invitations"
        description="When you invite employees, their invitation status will appear here."
      />
    );
  }

  return (
    <AppCard variant="standard">
      <div className="overflow-x-auto -mx-5 -my-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-gray-200)]">
              <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                Email
              </th>
              <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Role
              </th>
              <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Status
              </th>
              <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Sent
              </th>
              <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Expires
              </th>
              <th className="text-right py-3 px-5 font-medium text-[var(--color-gray-500)]">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {invitations.map((inv) => {
              const isPending = inv.status === "pending";
              const canResend =
                inv.status === "pending" || inv.status === "expired";

              return (
                <tr
                  key={inv.id}
                  className="border-b border-[var(--color-gray-100)] last:border-0"
                >
                  <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                    {inv.email}
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)] capitalize">
                    {inv.role.replace(/_/g, " ")}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <InvitationStatusBadge status={inv.status} />
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)]">
                    {formatDate(inv.created_at)}
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-600)]">
                    {formatDate(inv.expires_at)}
                  </td>
                  <td className="py-3 px-5">
                    <div className="flex items-center justify-end gap-1">
                      {/* Copy link */}
                      {isPending && inv.invite_url && (
                        <button
                          type="button"
                          title="Copy invite link"
                          onClick={() =>
                            copy(inv.invite_url as string, `copy-${inv.id}`)
                          }
                          className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"
                        >
                          {copiedId === `copy-${inv.id}` ? (
                            <Check className="h-4 w-4 text-emerald-600" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </button>
                      )}

                      {/* Resend */}
                      {canResend && (
                        <button
                          type="button"
                          title="Resend invitation"
                          disabled={actionLoading === `resend-${inv.id}`}
                          onClick={() => handleResend(inv)}
                          className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] disabled:opacity-50"
                        >
                          <RefreshCw
                            className={`h-4 w-4 ${actionLoading === `resend-${inv.id}` ? "animate-spin" : ""}`}
                          />
                        </button>
                      )}

                      {/* Revoke */}
                      {isPending && (
                        <button
                          type="button"
                          title="Revoke invitation"
                          disabled={actionLoading === `revoke-${inv.id}`}
                          onClick={() => handleRevoke(inv)}
                          className="p-1.5 rounded-lg hover:bg-red-50 transition-colors text-[var(--color-gray-500)] hover:text-red-600 disabled:opacity-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </AppCard>
  );
}

/* ═══════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════ */

export default function EmployeesPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as TabId) || "directory";
  const [activeTab, setActiveTab] = useState<TabId>(
    ["directory", "onboarding", "invitations"].includes(initialTab)
      ? initialTab
      : "directory",
  );
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  /* Invite link modal state */
  const [inviteLinkData, setInviteLinkData] = useState<{
    email: string;
    inviteUrl: string;
  } | null>(null);

  /* Assign onboarding modal state */
  const [assignTarget, setAssignTarget] = useState<{
    employeeId: number;
    employeeName: string;
  } | null>(null);

  /* Key to signal OnboardingTab to re-fetch assignments */
  const [assignmentRefreshKey, setAssignmentRefreshKey] = useState(0);

  /* Terminate employee modal state */
  const [terminateTarget, setTerminateTarget] = useState<Employee | null>(null);

  /* Sync tab with URL search param when it changes (e.g. sidebar click) */
  useEffect(() => {
    const tabParam = searchParams.get("tab") as TabId | null;
    if (
      tabParam &&
      ["directory", "onboarding", "invitations"].includes(tabParam)
    ) {
      setActiveTab(tabParam);
    } else if (!tabParam) {
      setActiveTab("directory");
    }
  }, [searchParams]);

  /* Invitations state */
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [invitationsLoading, setInvitationsLoading] = useState(true);
  const [invitationsError, setInvitationsError] = useState<string | null>(null);

  const fetchEmployees = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await employeesApi.list();
      setEmployees(data.employees ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load employees. Please try again.";
      setError(message);
      setEmployees([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchInvitations = useCallback(async () => {
    setInvitationsLoading(true);
    setInvitationsError(null);
    try {
      const data = await employeesApi.listInvitations();
      const list = Array.isArray(data)
        ? data
        : ((data as any)?.invitations ?? []);
      setInvitations(list);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load invitations. Please try again.";
      setInvitationsError(message);
      setInvitations([]);
    } finally {
      setInvitationsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEmployees();
    fetchInvitations();
  }, [fetchEmployees, fetchInvitations]);

  function handleInviteSuccess(email: string, inviteUrl: string) {
    setShowInviteModal(false);
    setInviteLinkData({ email, inviteUrl });
    fetchEmployees();
    fetchInvitations();
  }

  /** Invitation count for tab badge */
  const pendingInvitationCount = invitations.filter(
    (inv) => inv.status === "pending",
  ).length;

  /* ── RBAC: only owner / hr_manager may manage employees ── */
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

  return (
    <AdminGuard>
      <div className="max-w-7xl mx-auto space-y-6 pb-8">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Users
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Employees
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Manage your team members, onboarding, and employee access
            </p>
          </div>
        </div>

        {/* Tab navigation */}
        <nav
          role="tablist"
          aria-label="Employee sections"
          className="flex gap-1 overflow-x-auto border-b border-[var(--color-gray-200)] -mb-px"
        >
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const badgeCount =
              tab.id === "invitations" ? pendingInvitationCount : 0;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                aria-controls={`panel-${tab.id}`}
                id={`tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                className={`inline-flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] ${
                  isActive
                    ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                    : "border-transparent text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] hover:border-[var(--color-gray-300)]"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
                {badgeCount > 0 && (
                  <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-700">
                    {badgeCount}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Tab panels */}
        <div
          role="tabpanel"
          id={`panel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
        >
          {activeTab === "directory" && (
            <DirectoryTab
              employees={employees}
              isLoading={isLoading}
              error={error}
              onRefresh={fetchEmployees}
              onInvite={() => setShowInviteModal(true)}
              onImport={() => setShowImportModal(true)}
              onAssignOnboarding={(emp) =>
                setAssignTarget({
                  employeeId: emp.id,
                  employeeName: emp.name,
                })
              }
              onTerminate={(emp) => setTerminateTarget(emp)}
            />
          )}
          {activeTab === "onboarding" && (
            <OnboardingTab refreshKey={assignmentRefreshKey} />
          )}
          {activeTab === "invitations" && (
            <InvitationsTab
              invitations={invitations}
              isLoading={invitationsLoading}
              error={invitationsError}
              onRefresh={fetchInvitations}
            />
          )}
        </div>

        {/* Modals */}
        <InviteEmployeeModal
          isOpen={showInviteModal}
          onClose={() => setShowInviteModal(false)}
          onSuccess={handleInviteSuccess}
        />
        <InviteLinkModal
          isOpen={inviteLinkData !== null}
          email={inviteLinkData?.email ?? ""}
          inviteUrl={inviteLinkData?.inviteUrl ?? ""}
          onClose={() => setInviteLinkData(null)}
        />
        <ImportCsvModal
          isOpen={showImportModal}
          onClose={() => setShowImportModal(false)}
          onSuccess={() => {
            fetchEmployees();
            fetchInvitations();
          }}
        />
        <AssignTemplateModal
          isOpen={assignTarget !== null}
          employeeId={assignTarget?.employeeId ?? 0}
          employeeName={assignTarget?.employeeName ?? ""}
          onClose={() => setAssignTarget(null)}
          onAssigned={() => {
            setAssignTarget(null);
            fetchEmployees();
            setAssignmentRefreshKey((k) => k + 1);
          }}
        />
        <TerminateEmployeeModal
          isOpen={terminateTarget !== null}
          employee={terminateTarget}
          onClose={() => setTerminateTarget(null)}
          onSuccess={() => {
            setTerminateTarget(null);
            fetchEmployees();
          }}
        />
      </div>
    </AdminGuard>
  );
}
