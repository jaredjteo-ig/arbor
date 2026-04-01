"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  AppCard,
  AppButton,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  FileText,
  Plus,
  Search,
  FileType,
  FileBadge,
  Clock,
  AlertCircle,
  Bell,
  CheckCircle2,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { policiesApi, type PolicyRecord } from "@/services/api/policies";
import { PolicyCreateModal } from "@/components/policies/PolicyCreateModal";

/* -- Constants --------------------------------------------------- */

const POLICY_CATEGORIES = [
  "All",
  "Leave",
  "Compensation",
  "Workplace Conduct",
  "Health & Safety",
  "Flexible Work",
  "Data Privacy",
  "Anti-Harassment",
  "Termination",
  "Benefits",
  "Other",
] as const;

type StatusTab = "all" | "active" | "draft" | "archived";

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
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[s] || STATUS_STYLES.draft}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

/* -- File type icon ---------------------------------------------- */

function FileTypeIcon({ fileType }: { fileType: string | null }) {
  if (!fileType)
    return <FileText className="h-4 w-4 text-[var(--color-gray-400)]" />;
  const ft = fileType.toLowerCase();
  if (ft.includes("pdf")) return <FileBadge className="h-4 w-4 text-red-500" />;
  if (ft.includes("doc") || ft.includes("docx"))
    return <FileType className="h-4 w-4 text-blue-500" />;
  return <FileText className="h-4 w-4 text-[var(--color-gray-400)]" />;
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

/* -- Loading skeleton -------------------------------------------- */

function PolicyCardSkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse flex items-start gap-3">
        <div className="h-9 w-9 rounded-lg bg-[var(--color-gray-200)]" />
        <div className="flex-1">
          <div className="h-4 w-48 bg-[var(--color-gray-200)] rounded mb-2" />
          <div className="h-3 w-32 bg-[var(--color-gray-100)] rounded mb-2" />
          <div className="h-3 w-24 bg-[var(--color-gray-100)] rounded" />
        </div>
        <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full" />
      </div>
    </AppCard>
  );
}

/* -- Pending acknowledgment banner ------------------------------- */

function AcknowledgmentBanner({
  pendingCount,
  onViewPending,
}: {
  pendingCount: number;
  onViewPending: () => void;
}) {
  if (pendingCount === 0) return null;

  return (
    <div className="flex items-center gap-3 rounded-[12px] border border-amber-200 bg-amber-50 px-4 py-3">
      <Bell className="h-5 w-5 text-amber-600 shrink-0" />
      <div className="flex-1">
        <p className="text-sm font-medium text-amber-800">
          {pendingCount} {pendingCount === 1 ? "policy needs" : "policies need"}{" "}
          your acknowledgment
        </p>
        <p className="text-xs text-amber-600 mt-0.5">
          Please review and acknowledge the updated policies below.
        </p>
      </div>
      <AppButton variant="outlined" size="sm" onClick={onViewPending}>
        View
      </AppButton>
    </div>
  );
}

/* -- Policy Card ------------------------------------------------- */

function PolicyCard({
  policy,
  onClick,
}: {
  policy: PolicyRecord;
  onClick: () => void;
}) {
  return (
    <AppCard
      variant="flat"
      className="hover:border-[var(--color-primary)] transition-colors cursor-pointer"
    >
      <button
        type="button"
        onClick={onClick}
        className="w-full text-left flex items-start gap-3"
      >
        <div className="p-2 rounded-lg bg-[var(--color-primary-bg)] shrink-0">
          <FileText className="h-5 w-5 text-[var(--color-primary)]" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-[var(--color-gray-900)]">
              {policy.title}
            </p>
            <span className="text-[10px] font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-500)] px-1.5 py-0.5 rounded">
              v{policy.version_number}
            </span>
            <StatusBadge status={policy.status} />
          </div>

          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <span className="text-xs text-[var(--color-gray-500)]">
              {policy.category}
            </span>
            {policy.effective_date && (
              <span className="text-xs text-[var(--color-gray-400)] flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Effective {formatDate(policy.effective_date)}
              </span>
            )}
            {policy.file_name && (
              <span className="text-xs text-[var(--color-gray-400)] flex items-center gap-1">
                <FileTypeIcon fileType={policy.file_type} />
                {policy.file_name}
              </span>
            )}
          </div>

          {policy.requires_acknowledgment && (
            <div className="flex items-center gap-1 mt-1.5">
              <CheckCircle2 className="h-3 w-3 text-[var(--color-primary)]" />
              <span className="text-xs text-[var(--color-primary)]">
                Acknowledgment required
              </span>
            </div>
          )}
        </div>
      </button>
    </AppCard>
  );
}

/* -- Page -------------------------------------------------------- */

export default function PoliciesPage() {
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin =
    user?.role === "owner" ||
    user?.role === "hr_manager" ||
    user?.role === "consultant";

  /* State */
  const [policies, setPolicies] = useState<PolicyRecord[]>([]);
  const [pendingPolicies, setPendingPolicies] = useState<PolicyRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusTab, setStatusTab] = useState<StatusTab>("all");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);

  /* Debounced search */
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, [searchQuery]);

  /* Fetch policies */
  const fetchPolicies = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await policiesApi.list();
      setPolicies(data.policies ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load policies. Please try again.";
      setError(message);
      setPolicies([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /* Fetch pending acknowledgments (employee view) */
  const fetchPending = useCallback(async () => {
    if (isAdmin) return;
    try {
      const data = await policiesApi.pendingAcknowledgments();
      setPendingPolicies(data.pending_policies ?? []);
    } catch {
      // Non-critical: silently fail
    }
  }, [isAdmin]);

  useEffect(() => {
    fetchPolicies();
    fetchPending();
  }, [fetchPolicies, fetchPending]);

  /* Filter logic */
  const statusTabs: { key: StatusTab; label: string }[] = isAdmin
    ? [
        { key: "all", label: "All" },
        { key: "active", label: "Active" },
        { key: "draft", label: "Draft" },
        { key: "archived", label: "Archived" },
      ]
    : [
        { key: "all", label: "All" },
        { key: "active", label: "Active" },
      ];

  const filteredPolicies = policies.filter((p) => {
    /* Employee view: only active policies */
    if (!isAdmin && p.status !== "active") return false;

    /* Status tab */
    if (statusTab !== "all" && p.status !== statusTab) return false;

    /* Category filter */
    if (categoryFilter !== "All" && p.category !== categoryFilter) return false;

    /* Search */
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase();
      return (
        p.title.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q) ||
        (p.content && p.content.toLowerCase().includes(q))
      );
    }

    return true;
  });

  /* Group by category */
  const categoriesInUse = Array.from(
    new Set(filteredPolicies.map((p) => p.category)),
  ).sort();

  function handlePolicyCreated() {
    setShowCreateModal(false);
    fetchPolicies();
    toast.success("Policy created successfully");
  }

  function scrollToPending() {
    document
      .getElementById("pending-acknowledgments")
      ?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <FileText
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Company Policies
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              {isAdmin
                ? "Manage company policies, track acknowledgments, and ensure compliance."
                : "Review company policies and acknowledge updates."}
            </p>
          </div>
        </div>
        {isAdmin && (
          <AppButton
            variant="primary"
            size="sm"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Policy
          </AppButton>
        )}
      </div>

      {/* Pending acknowledgment banner (employee view) */}
      {!isAdmin && pendingPolicies.length > 0 && (
        <AcknowledgmentBanner
          pendingCount={pendingPolicies.length}
          onViewPending={scrollToPending}
        />
      )}

      {/* Filters */}
      <div className="space-y-3">
        {/* Status tabs */}
        <div className="flex items-center gap-1 flex-wrap">
          {statusTabs.map((tab) => {
            const count =
              tab.key === "all"
                ? policies.filter((p) =>
                    !isAdmin ? p.status === "active" : true,
                  ).length
                : policies.filter((p) => p.status === tab.key).length;

            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setStatusTab(tab.key)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                  statusTab === tab.key
                    ? "bg-[var(--color-primary-bg)] text-[var(--color-primary)] border border-[var(--color-primary)]"
                    : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:bg-[var(--color-gray-200)] border border-transparent"
                }`}
              >
                {tab.label}
                <span className="text-[10px] opacity-70">{count}</span>
              </button>
            );
          })}
        </div>

        {/* Search + Category */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-gray-400)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search policies..."
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
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="
              rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
              bg-[var(--color-surface-input)] text-[var(--foreground)]
              border-[var(--color-surface-input-border)]
              transition-colors
              focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
              focus:border-[var(--color-surface-input-focus)]
            "
          >
            {POLICY_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat === "All" ? "All Categories" : cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Policy list */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((n) => (
            <PolicyCardSkeleton key={n} />
          ))}
        </div>
      ) : error ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <AlertCircle className="h-8 w-8 text-[var(--color-error)] mx-auto mb-2" />
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={fetchPolicies}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      ) : filteredPolicies.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-12 w-12" aria-hidden="true" />}
          message={
            policies.length === 0
              ? "No policies yet"
              : "No policies match your filters"
          }
          description={
            policies.length === 0
              ? isAdmin
                ? "Add your first company policy to get started."
                : "Your company has not uploaded any policies yet."
              : "Try adjusting your search or filters."
          }
          action={
            policies.length === 0 && isAdmin ? (
              <AppButton
                variant="primary"
                size="sm"
                onClick={() => setShowCreateModal(true)}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Policy
              </AppButton>
            ) : undefined
          }
        />
      ) : categoryFilter !== "All" || debouncedSearch ? (
        /* Flat list when filtering */
        <div className="space-y-3">
          {filteredPolicies.map((policy) => (
            <PolicyCard
              key={policy.id}
              policy={policy}
              onClick={() => router.push(`/policies/${policy.id}`)}
            />
          ))}
        </div>
      ) : (
        /* Grouped by category */
        <div className="space-y-6">
          {categoriesInUse.map((category) => {
            const categoryPolicies = filteredPolicies.filter(
              (p) => p.category === category,
            );
            return (
              <div key={category}>
                <h2 className="text-sm font-semibold text-[var(--color-gray-700)] mb-3 flex items-center gap-2">
                  {category}
                  <span className="text-xs font-normal text-[var(--color-gray-400)]">
                    ({categoryPolicies.length})
                  </span>
                </h2>
                <div className="space-y-3">
                  {categoryPolicies.map((policy) => (
                    <PolicyCard
                      key={policy.id}
                      policy={policy}
                      onClick={() => router.push(`/policies/${policy.id}`)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pending acknowledgments section (employee view) */}
      {!isAdmin && pendingPolicies.length > 0 && (
        <div id="pending-acknowledgments">
          <h2 className="text-lg font-semibold text-[var(--color-gray-900)] mb-3 flex items-center gap-2">
            <Bell className="h-5 w-5 text-amber-500" aria-hidden="true" />
            Pending Acknowledgments
          </h2>
          <div className="space-y-3">
            {pendingPolicies.map((policy) => (
              <PolicyCard
                key={`pending-${policy.id}`}
                policy={policy}
                onClick={() => router.push(`/policies/${policy.id}`)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Create policy modal */}
      <PolicyCreateModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={handlePolicyCreated}
      />
    </div>
  );
}
