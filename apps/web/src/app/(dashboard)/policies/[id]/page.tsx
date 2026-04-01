"use client";

import { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AppCard,
  AppButton,
  AppInput,
  toast,
} from "@/components/design-system";
import {
  ArrowLeft,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Edit,
  Archive,
  Users,
  History,
  LayoutDashboard,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  policiesApi,
  type PolicyRecord,
  type PolicyAcknowledgmentRecord,
} from "@/services/api/policies";

/* -- Helpers ----------------------------------------------------- */

const CATEGORY_LABELS: Record<string, string> = {
  employment_terms: "Employment Terms",
  leave_absence: "Leave & Absence",
  compensation_benefits: "Compensation & Benefits",
  workplace_safety: "Workplace Safety",
  fair_employment: "Fair Employment",
  foreign_worker: "Foreign Workers",
  tax_filing: "Tax & Filing",
  general_hr: "General HR",
  code_of_conduct: "Code of Conduct",
};

function formatCategory(raw: string): string {
  return (
    CATEGORY_LABELS[raw] ||
    raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

/* -- Types ------------------------------------------------------- */

type TabKey = "overview" | "content" | "versions" | "acknowledgments";

const ADMIN_TABS: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "content", label: "Content", icon: FileText },
  { key: "versions", label: "Versions", icon: History },
  { key: "acknowledgments", label: "Acknowledgments", icon: Users },
];

const EMPLOYEE_TABS: { key: TabKey; label: string; icon: React.ElementType }[] =
  [
    { key: "overview", label: "Overview", icon: LayoutDashboard },
    { key: "content", label: "Content", icon: FileText },
  ];

/* -- Status badge ------------------------------------------------ */

const STATUS_STYLES: Record<string, string> = {
  active: "bg-emerald-50 text-emerald-700 border-emerald-200",
  draft: "bg-amber-50 text-amber-700 border-amber-200",
  archived:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border-[var(--color-gray-200)]",
};

function StatusBadge({ status }: { status: string }) {
  const s = status || "draft";
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[s] || STATUS_STYLES.draft}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

/* -- Helper: format date ----------------------------------------- */

function formatDate(isoDate: string): string {
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

function formatDateTime(isoDate: string): string {
  if (!isoDate) return "-";
  try {
    return new Date(isoDate).toLocaleDateString("en-SG", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoDate;
  }
}

/* -- Helper: format file size ------------------------------------ */

function formatFileSize(bytes: number | null): string {
  if (!bytes) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/* -- Skeleton loaders -------------------------------------------- */

function DetailSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-6 w-64 bg-[var(--color-gray-200)] rounded" />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="space-y-1.5">
            <div className="h-3.5 w-24 bg-[var(--color-gray-200)] rounded" />
            <div className="h-[44px] w-full bg-[var(--color-gray-100)] rounded-[8px]" />
          </div>
        ))}
      </div>
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

/* -- Info Row ---------------------------------------------------- */

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium text-[var(--color-gray-500)] mb-1">
        {label}
      </dt>
      <dd className="text-sm text-[var(--color-gray-900)]">{value || "-"}</dd>
    </div>
  );
}

/* -- Overview Tab ------------------------------------------------ */

function OverviewTab({
  policy,
  isAdmin,
  ackCount,
  totalEmployees,
}: {
  policy: PolicyRecord;
  isAdmin: boolean;
  ackCount: number;
  totalEmployees: number;
}) {
  return (
    <div className="space-y-6">
      {/* Summary card */}
      <AppCard variant="standard">
        <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-4 flex items-center gap-2">
          <FileText className="h-4 w-4 text-[var(--color-primary)]" />
          Policy Details
        </h3>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <InfoRow label="Title" value={policy.title} />
          <InfoRow label="Category" value={formatCategory(policy.category)} />
          <InfoRow
            label="Status"
            value={<StatusBadge status={policy.status} />}
          />
          <InfoRow
            label="Version"
            value={
              <span className="text-[10px] font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-600)] px-1.5 py-0.5 rounded">
                v{policy.version_number}
              </span>
            }
          />
          <InfoRow
            label="Effective Date"
            value={formatDate(policy.effective_date)}
          />
          <InfoRow
            label="Requires Acknowledgment"
            value={policy.requires_acknowledgment ? "Yes" : "No"}
          />
          {policy.file_name && (
            <>
              <InfoRow label="File Name" value={policy.file_name} />
              <InfoRow
                label="File Size"
                value={formatFileSize(policy.file_size_bytes)}
              />
            </>
          )}
          <InfoRow label="Created" value={formatDateTime(policy.created_at)} />
          <InfoRow
            label="Last Updated"
            value={formatDateTime(policy.updated_at)}
          />
        </dl>
      </AppCard>

      {/* Acknowledgment summary (admin only) */}
      {isAdmin && policy.requires_acknowledgment && (
        <AppCard variant="standard">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-4 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-[var(--color-primary)]" />
            Acknowledgment Summary
          </h3>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-600">{ackCount}</p>
              <p className="text-xs text-[var(--color-gray-500)]">
                Acknowledged
              </p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-[var(--color-gray-400)]">
                {totalEmployees > 0 ? totalEmployees - ackCount : "-"}
              </p>
              <p className="text-xs text-[var(--color-gray-500)]">Pending</p>
            </div>
            {totalEmployees > 0 && (
              <div className="flex-1">
                <div className="w-full h-2 bg-[var(--color-gray-100)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all"
                    style={{
                      width: `${Math.round((ackCount / totalEmployees) * 100)}%`,
                    }}
                  />
                </div>
                <p className="text-xs text-[var(--color-gray-400)] mt-1">
                  {Math.round((ackCount / totalEmployees) * 100)}% complete
                </p>
              </div>
            )}
          </div>
        </AppCard>
      )}
    </div>
  );
}

/* -- Content Tab ------------------------------------------------- */

function ContentTab({
  policy,
  isAdmin,
  onContentUpdated,
}: {
  policy: PolicyRecord;
  isAdmin: boolean;
  onContentUpdated: (updated: PolicyRecord) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(policy.content);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSave() {
    setIsSaving(true);
    try {
      await policiesApi.updateContent(policy.id, editContent);
      onContentUpdated({ ...policy, content: editContent });
      setIsEditing(false);
      toast.success("Content updated successfully");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to update content";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <AppCard variant="standard">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
          Policy Content
        </h3>
        {isAdmin && !isEditing && (
          <AppButton
            variant="text"
            size="sm"
            onClick={() => {
              setEditContent(policy.content);
              setIsEditing(true);
            }}
          >
            <Edit className="h-3.5 w-3.5 mr-1" />
            Edit Content
          </AppButton>
        )}
      </div>

      {isEditing ? (
        <div className="space-y-3">
          <AppInput
            variant="textarea"
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            rows={16}
          />
          <div className="flex gap-3 justify-end">
            <AppButton
              variant="outlined"
              size="sm"
              onClick={() => setIsEditing(false)}
              disabled={isSaving}
            >
              Cancel
            </AppButton>
            <AppButton
              variant="primary"
              size="sm"
              onClick={handleSave}
              loading={isSaving}
            >
              Save Changes
            </AppButton>
          </div>
        </div>
      ) : policy.content ? (
        <div className="text-sm text-[var(--color-gray-700)] whitespace-pre-wrap leading-relaxed">
          {policy.content}
        </div>
      ) : (
        <div className="py-8 text-center">
          <FileText className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2" />
          <p className="text-sm text-[var(--color-gray-500)]">
            No content available.
          </p>
          {isAdmin && (
            <AppButton
              variant="text"
              size="sm"
              onClick={() => setIsEditing(true)}
              className="mt-2"
            >
              <Edit className="h-3.5 w-3.5 mr-1" />
              Add Content
            </AppButton>
          )}
        </div>
      )}
    </AppCard>
  );
}

/* -- Versions Tab ------------------------------------------------ */

function VersionsTab({ policyId }: { policyId: number }) {
  const [versions, setVersions] = useState<PolicyRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVersions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await policiesApi.versions(policyId);
      setVersions(data.versions ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load versions.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [policyId]);

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  if (isLoading) return <ListSkeleton rows={3} />;

  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchVersions}>
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  if (versions.length === 0) {
    return (
      <AppCard variant="standard">
        <div className="py-8 text-center">
          <History className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2" />
          <p className="text-sm text-[var(--color-gray-500)]">
            No version history available.
          </p>
        </div>
      </AppCard>
    );
  }

  return (
    <div className="space-y-3">
      {versions
        .sort((a, b) => b.version_number - a.version_number)
        .map((v) => (
          <AppCard key={v.id} variant="flat">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                  Version {v.version_number}
                </span>
                <StatusBadge status={v.status} />
              </div>
              <div className="flex items-center gap-3 text-xs text-[var(--color-gray-500)]">
                {v.effective_date && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Effective {formatDate(v.effective_date)}
                  </span>
                )}
                <span>Updated {formatDateTime(v.updated_at)}</span>
              </div>
            </div>
          </AppCard>
        ))}
    </div>
  );
}

/* -- Acknowledgments Tab ----------------------------------------- */

function AcknowledgmentsTab({ policyId }: { policyId: number }) {
  const [acknowledgments, setAcknowledgments] = useState<
    PolicyAcknowledgmentRecord[]
  >([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAcknowledgments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await policiesApi.acknowledgments(policyId);
      setAcknowledgments(data.acknowledgments ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load acknowledgments.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [policyId]);

  useEffect(() => {
    fetchAcknowledgments();
  }, [fetchAcknowledgments]);

  if (isLoading) return <ListSkeleton rows={4} />;

  if (error) {
    return (
      <AppCard variant="standard">
        <div className="py-6 text-center">
          <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
          <AppButton
            variant="outlined"
            size="sm"
            onClick={fetchAcknowledgments}
          >
            Try again
          </AppButton>
        </div>
      </AppCard>
    );
  }

  if (acknowledgments.length === 0) {
    return (
      <AppCard variant="standard">
        <div className="py-8 text-center">
          <Users className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2" />
          <p className="text-sm text-[var(--color-gray-500)]">
            No acknowledgments yet.
          </p>
        </div>
      </AppCard>
    );
  }

  return (
    <AppCard variant="standard">
      <div className="overflow-x-auto -mx-5 -my-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-gray-200)]">
              <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                Employee ID
              </th>
              <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Version
              </th>
              <th className="text-left py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Acknowledged
              </th>
              <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {acknowledgments.map((ack) => (
              <tr
                key={ack.id}
                className="border-b border-[var(--color-gray-100)] last:border-0"
              >
                <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                  Employee #{ack.employee_id}
                </td>
                <td className="py-3 px-3 text-center text-[var(--color-gray-600)]">
                  v{ack.version_acknowledged}
                </td>
                <td className="py-3 px-3 text-[var(--color-gray-600)]">
                  {formatDateTime(ack.acknowledged_at)}
                </td>
                <td className="py-3 px-5 text-center">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle2 className="h-3 w-3" />
                    Acknowledged
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppCard>
  );
}

/* -- Employee Acknowledge Button --------------------------------- */

function AcknowledgeButton({
  policy,
  onAcknowledged,
}: {
  policy: PolicyRecord;
  onAcknowledged: () => void;
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleAcknowledge() {
    setIsSubmitting(true);
    try {
      await policiesApi.acknowledge(policy.id, policy.version_number);
      toast.success("Policy acknowledged successfully");
      onAcknowledged();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to acknowledge policy";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex items-center gap-3 rounded-[12px] border border-amber-200 bg-amber-50 px-4 py-3">
      <AlertCircle className="h-5 w-5 text-amber-600 shrink-0" />
      <div className="flex-1">
        <p className="text-sm font-medium text-amber-800">
          Acknowledgment Required
        </p>
        <p className="text-xs text-amber-600 mt-0.5">
          Please review the policy content and confirm your acknowledgment.
        </p>
      </div>
      <AppButton
        variant="primary"
        size="sm"
        onClick={handleAcknowledge}
        loading={isSubmitting}
      >
        <CheckCircle2 className="h-4 w-4 mr-1" />I Acknowledge
      </AppButton>
    </div>
  );
}

/* -- Page -------------------------------------------------------- */

export default function PolicyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const policyId = Number(resolvedParams.id);

  const router = useRouter();
  const { user } = useAuth();
  const isAdmin =
    user?.role === "owner" ||
    user?.role === "hr_manager" ||
    user?.role === "consultant";

  const [policy, setPolicy] = useState<PolicyRecord | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [ackCount, setAckCount] = useState(0);
  const [needsAck, setNeedsAck] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const [showArchiveConfirm, setShowArchiveConfirm] = useState(false);

  /* Fetch policy */
  const fetchPolicy = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await policiesApi.get(policyId);
      setPolicy(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load this policy.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [policyId]);

  /* Fetch acknowledgment count (admin) */
  const fetchAckCount = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const data = await policiesApi.acknowledgments(policyId);
      setAckCount(data.acknowledgments?.length ?? 0);
    } catch {
      // Non-critical
    }
  }, [policyId, isAdmin]);

  /* Check if employee needs to acknowledge */
  const checkPendingAck = useCallback(async () => {
    if (isAdmin) return;
    try {
      const data = await policiesApi.pendingAcknowledgments();
      const isPending = (data.pending_policies ?? []).some(
        (p) => p.id === policyId,
      );
      setNeedsAck(isPending);
    } catch {
      // Non-critical
    }
  }, [policyId, isAdmin]);

  useEffect(() => {
    fetchPolicy();
    fetchAckCount();
    checkPendingAck();
  }, [fetchPolicy, fetchAckCount, checkPendingAck]);

  /* Archive handler */
  async function handleArchive() {
    if (!policy) return;
    setIsArchiving(true);
    try {
      await policiesApi.archive(policy.id);
      toast.success("Policy archived successfully");
      router.push("/policies");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to archive policy";
      toast.error(message);
    } finally {
      setIsArchiving(false);
    }
  }

  function handleContentUpdated(updated: PolicyRecord) {
    setPolicy(updated);
  }

  function handleAcknowledged() {
    setNeedsAck(false);
    fetchAckCount();
  }

  const tabs = isAdmin ? ADMIN_TABS : EMPLOYEE_TABS;

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <div className="flex items-center gap-2">
          <Link
            href="/policies"
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-[var(--color-gray-500)]" />
          </Link>
          <div className="h-6 w-48 bg-[var(--color-gray-200)] rounded animate-pulse" />
        </div>
        <DetailSkeleton />
      </div>
    );
  }

  if (error || !policy) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <Link
          href="/policies"
          className="inline-flex items-center gap-1 text-sm text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Policies
        </Link>
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <AlertCircle className="h-8 w-8 text-[var(--color-error)] mx-auto mb-2" />
            <p className="text-sm text-[var(--color-error)] mb-3">
              {error || "Policy not found"}
            </p>
            <AppButton variant="outlined" size="sm" onClick={fetchPolicy}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Back link + header */}
      <div>
        <Link
          href="/policies"
          className="inline-flex items-center gap-1 text-sm text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Policies
        </Link>

        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--color-primary-bg)]">
              <FileText className="h-6 w-6 text-[var(--color-primary)]" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                  {policy.title}
                </h1>
                <span className="text-[10px] font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-500)] px-1.5 py-0.5 rounded">
                  v{policy.version_number}
                </span>
                <StatusBadge status={policy.status} />
              </div>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                {formatCategory(policy.category)}
                {policy.effective_date &&
                  ` \u00b7 Effective ${formatDate(policy.effective_date)}`}
              </p>
            </div>
          </div>

          {isAdmin &&
            policy.status !== "archived" &&
            (showArchiveConfirm ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-[var(--color-gray-600)]">
                  Archive this policy?
                </span>
                <AppButton
                  variant="danger"
                  size="sm"
                  onClick={handleArchive}
                  loading={isArchiving}
                >
                  Yes, archive
                </AppButton>
                <AppButton
                  variant="text"
                  size="sm"
                  onClick={() => setShowArchiveConfirm(false)}
                  disabled={isArchiving}
                >
                  Cancel
                </AppButton>
              </div>
            ) : (
              <AppButton
                variant="outlined"
                size="sm"
                onClick={() => setShowArchiveConfirm(true)}
              >
                <Archive className="h-4 w-4 mr-1" />
                Archive
              </AppButton>
            ))}
        </div>
      </div>

      {/* Employee acknowledge banner */}
      {!isAdmin && needsAck && policy.requires_acknowledgment && (
        <AcknowledgeButton
          policy={policy}
          onAcknowledged={handleAcknowledged}
        />
      )}

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-[var(--color-gray-200)] overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px ${
                activeTab === tab.key
                  ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                  : "border-transparent text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] hover:border-[var(--color-gray-300)]"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && (
        <OverviewTab
          policy={policy}
          isAdmin={isAdmin}
          ackCount={ackCount}
          totalEmployees={0}
        />
      )}

      {activeTab === "content" && (
        <ContentTab
          policy={policy}
          isAdmin={isAdmin}
          onContentUpdated={handleContentUpdated}
        />
      )}

      {activeTab === "versions" && isAdmin && (
        <VersionsTab policyId={policy.id} />
      )}

      {activeTab === "acknowledgments" && isAdmin && (
        <AcknowledgmentsTab policyId={policy.id} />
      )}
    </div>
  );
}
