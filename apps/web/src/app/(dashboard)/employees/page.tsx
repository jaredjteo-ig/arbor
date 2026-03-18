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
} from "lucide-react";
import {
  employeesApi,
  type Employee,
  type Invitation,
} from "@/services/api/employees";

/* -- Status badge -------------------------------------------------- */

const STATUS_STYLES: Record<string, string> = {
  active: "bg-emerald-50 text-emerald-700 border-emerald-200",
  invited: "bg-amber-50 text-amber-700 border-amber-200",
  inactive:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[status] || STATUS_STYLES.inactive}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

/* -- Confirmation status badge ------------------------------------- */

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

/* -- Profile completeness ------------------------------------------ */

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

/* -- Loading skeleton ---------------------------------------------- */

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

/* -- Copy-to-clipboard hook --------------------------------------- */

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

/* -- Invite Link Success Modal ------------------------------------ */

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

/* -- Invite Employee Modal ----------------------------------------- */

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

/* -- Invitation status badge -------------------------------------- */

const INVITATION_STATUS_STYLES: Record<string, string> = {
  pending: "bg-blue-50 text-blue-700 border-blue-200",
  expired: "bg-red-50 text-red-700 border-red-200",
  accepted: "bg-emerald-50 text-emerald-700 border-emerald-200",
  revoked:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]",
};

function InvitationStatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${INVITATION_STATUS_STYLES[status] || INVITATION_STATUS_STYLES.revoked}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

/* -- Invitation table skeleton ------------------------------------ */

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

/* -- Pending Invitations Section ---------------------------------- */

function PendingInvitationsSection({
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

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Mail
          className="h-5 w-5 text-[var(--color-gray-500)]"
          aria-hidden="true"
        />
        <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
          Pending Invitations
        </h2>
        {!isLoading && invitations.length > 0 && (
          <span className="text-xs font-medium text-[var(--color-gray-400)] bg-[var(--color-gray-100)] rounded-full px-2 py-0.5">
            {invitations.length}
          </span>
        )}
      </div>

      {isLoading ? (
        <AppCard variant="standard">
          <div className="-mx-5 -my-4">
            <InvitationTableSkeleton />
          </div>
        </AppCard>
      ) : error ? (
        <AppCard variant="standard">
          <div className="py-6 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={onRefresh}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      ) : invitations.length === 0 ? (
        <AppCard variant="standard">
          <div className="py-6 text-center">
            <Clock
              className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2"
              aria-hidden="true"
            />
            <p className="text-sm text-[var(--color-gray-500)]">
              No pending invitations
            </p>
          </div>
        </AppCard>
      ) : (
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
                          {/* Copy link — only for pending invitations with a URL */}
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

                          {/* Resend — for pending or expired */}
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

                          {/* Revoke — only for pending */}
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
      )}
    </div>
  );
}

/* -- Import CSV Modal ---------------------------------------------- */

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
      toast.success("Employees imported successfully");
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

/* -- Page ---------------------------------------------------------- */

export default function EmployeesPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
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
      setInvitations(Array.isArray(data) ? data : []);
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

  const filteredEmployees = employees.filter(
    (emp) =>
      emp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.department.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
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
              Manage your team members and employee access
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <AppButton
            variant="outlined"
            size="sm"
            onClick={() => setShowImportModal(true)}
          >
            <Upload className="h-4 w-4 mr-1" />
            Import CSV
          </AppButton>
          <AppButton
            variant="primary"
            size="sm"
            onClick={() => setShowInviteModal(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Invite Employee
          </AppButton>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
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
            <AppButton variant="outlined" size="sm" onClick={fetchEmployees}>
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
            <AppButton
              variant="primary"
              size="sm"
              onClick={() => setShowInviteModal(true)}
            >
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
                  <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.map((emp) => (
                  <tr
                    key={emp.id}
                    onClick={() => router.push(`/employees/${emp.id}`)}
                    className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors cursor-pointer"
                  >
                    <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                      {emp.name}
                    </td>
                    <td className="py-3 px-3 text-[var(--color-gray-600)]">
                      {emp.email}
                    </td>
                    <td className="py-3 px-3 text-[var(--color-gray-600)]">
                      {emp.department}
                    </td>
                    <td className="py-3 px-3 text-[var(--color-gray-600)]">
                      {emp.designation || "-"}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <ConfirmBadge status={emp.confirmation_status} />
                    </td>
                    <td className="py-3 px-3 text-center">
                      <ProfileBar employee={emp} />
                    </td>
                    <td className="py-3 px-5 text-center">
                      <StatusBadge status={emp.status} />
                    </td>
                  </tr>
                ))}
                {filteredEmployees.length === 0 && employees.length > 0 && (
                  <tr>
                    <td
                      colSpan={7}
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

      {/* Pending Invitations */}
      <PendingInvitationsSection
        invitations={invitations}
        isLoading={invitationsLoading}
        error={invitationsError}
        onRefresh={fetchInvitations}
      />

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
    </div>
  );
}
