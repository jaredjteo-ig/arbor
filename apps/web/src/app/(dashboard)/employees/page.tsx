"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
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
  RefreshCw,
  Trash2,
  Clock,
  Mail,
  Shield,
  ClipboardList,
  ClipboardCheck,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import {
  employeesApi,
  type Employee,
  type Invitation,
} from "@/services/api/employees";
import {
  onboardingApi,
  type OnboardingAssignment,
  type MyOnboardingProgress,
  type ImportResult,
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
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;

    setIsSubmitting(true);
    try {
      const result = await employeesApi.invite({ email: email.trim(), role });
      const submittedEmail = email.trim();
      setEmail("");
      setRole("employee");
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
}: {
  employees: Employee[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  onInvite: () => void;
  onImport: () => void;
  onAssignOnboarding: (employee: Employee) => void;
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
          <div className="overflow-x-auto -mx-5 -my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)]">
                  <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                    Name
                  </th>
                  <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Email
                  </th>
                  <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Department
                  </th>
                  <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Designation
                  </th>
                  <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Confirmation
                  </th>
                  <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                    Profile
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
                {filteredEmployees.map((emp) => (
                  <tr
                    key={emp.id}
                    className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                  >
                    <td
                      className="py-3 px-5 font-medium text-[var(--color-gray-900)] cursor-pointer"
                      onClick={() => router.push(`/employees/${emp.id}`)}
                    >
                      {emp.name}
                    </td>
                    <td
                      className="py-3 px-3 text-[var(--color-gray-600)] cursor-pointer"
                      onClick={() => router.push(`/employees/${emp.id}`)}
                    >
                      {emp.email}
                    </td>
                    <td
                      className="py-3 px-3 text-[var(--color-gray-600)] cursor-pointer"
                      onClick={() => router.push(`/employees/${emp.id}`)}
                    >
                      {emp.department}
                    </td>
                    <td
                      className="py-3 px-3 text-[var(--color-gray-600)] cursor-pointer"
                      onClick={() => router.push(`/employees/${emp.id}`)}
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
                    </td>
                  </tr>
                ))}
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

/* ═══════════════════════════════════════════════════════════
   Onboarding Tab
   ═══════════════════════════════════════════════════════════ */

function OnboardingTab() {
  const [assignments, setAssignments] = useState<OnboardingAssignment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedDetail, setExpandedDetail] =
    useState<MyOnboardingProgress | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
  }, [fetchAssignments]);

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

  async function handleImportTemplate(files: FileList | null) {
    if (!files || files.length === 0) return;
    const file = files[0];

    setIsImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const result: ImportResult = await onboardingApi.importTemplate(formData);

      if (result.errors.length > 0) {
        toast.error(
          `Import completed with errors: ${result.errors.join(", ")}`,
        );
      } else {
        const warningNote =
          result.warnings.length > 0
            ? ` (${result.warnings.length} warning${result.warnings.length !== 1 ? "s" : ""})`
            : "";
        toast.success(
          `Template imported: ${result.modules_created} modules, ${result.steps_created} steps${warningNote}`,
        );
      }
      fetchAssignments();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to import template";
      toast.error(message);
    } finally {
      setIsImporting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
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

  return (
    <div className="space-y-6">
      {/* Template Builder */}
      <TemplateBuilder onImportClick={() => fileInputRef.current?.click()} />
      <input
        ref={fileInputRef}
        type="file"
        accept=".json,.csv,.xlsx"
        className="hidden"
        onChange={(e) => handleImportTemplate(e.target.files)}
      />

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
      ) : (
        <div className="space-y-3">
          {assignments.map((assignment) => {
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
  const [activeTab, setActiveTab] = useState<TabId>("directory");
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

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
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
          />
        )}
        {activeTab === "onboarding" && <OnboardingTab />}
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
        }}
      />
    </div>
  );
}
