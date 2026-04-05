"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  Receipt,
  Plus,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  Trash2,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  claimsApi,
  type Claim,
  type ClaimCategory,
} from "@/services/api/claims";

/* -- Currency formatter --------------------------------------------- */

function formatCurrency(amount: number): string {
  return `$${(amount ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/* -- Status badge -------------------------------------------------- */

const STATUS_STYLES: Record<string, string> = {
  draft:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

function StatusBadge({ status }: { status: string }) {
  const s = status || "pending";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[s] || STATUS_STYLES.draft}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

/* -- Loading skeletons ---------------------------------------------- */

function TableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-5 border-b border-[var(--color-gray-100)] last:border-0"
        >
          <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded" />
          <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* -- Add Item Row --------------------------------------------------- */

function AddItemRow({
  categories,
  onAdd,
}: {
  categories: ClaimCategory[];
  onAdd: (item: {
    category_id: number;
    description: string;
    amount: number;
    expense_date: string;
  }) => void;
}) {
  const [categoryId, setCategoryId] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [expenseDate, setExpenseDate] = useState("");

  function handleAdd() {
    if (!categoryId || !description.trim() || !amount || !expenseDate) return;

    onAdd({
      category_id: Number(categoryId),
      description: description.trim(),
      amount: parseFloat(amount),
      expense_date: expenseDate,
    });
    setCategoryId("");
    setDescription("");
    setAmount("");
    setExpenseDate("");
  }

  return (
    <div className="flex flex-col sm:flex-row gap-2 p-3 rounded-[8px] border border-dashed border-[var(--color-gray-300)] bg-[var(--color-gray-50)]">
      <select
        value={categoryId}
        onChange={(e) => setCategoryId(e.target.value)}
        className="
          flex-1 rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
          bg-[var(--color-surface-input)] text-[var(--foreground)]
          border-[var(--color-surface-input-border)]
          transition-colors
          focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
          focus:border-[var(--color-surface-input-focus)]
        "
      >
        <option value="">Category</option>
        {categories.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <input
        type="text"
        placeholder="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        className="
          flex-1 rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
          bg-[var(--color-surface-input)] text-[var(--foreground)]
          border-[var(--color-surface-input-border)]
          placeholder:text-[var(--color-gray-400)]
          transition-colors
          focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
          focus:border-[var(--color-surface-input-focus)]
        "
      />
      <input
        type="number"
        placeholder="Amount"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        step="0.01"
        min="0"
        className="
          w-28 rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
          bg-[var(--color-surface-input)] text-[var(--foreground)]
          border-[var(--color-surface-input-border)]
          placeholder:text-[var(--color-gray-400)]
          transition-colors
          focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
          focus:border-[var(--color-surface-input-focus)]
        "
      />
      <input
        type="date"
        value={expenseDate}
        onChange={(e) => setExpenseDate(e.target.value)}
        className="
          w-40 rounded-[8px] border px-3 py-2 text-sm min-h-[44px]
          bg-[var(--color-surface-input)] text-[var(--foreground)]
          border-[var(--color-surface-input-border)]
          transition-colors
          focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
          focus:border-[var(--color-surface-input-focus)]
        "
      />
      <AppButton
        variant="primary"
        size="sm"
        onClick={handleAdd}
        disabled={!categoryId || !description.trim() || !amount || !expenseDate}
      >
        <Plus className="h-4 w-4" />
      </AppButton>
    </div>
  );
}

/* -- New Claim Modal ------------------------------------------------ */

function NewClaimModal({
  isOpen,
  onClose,
  onSuccess,
  categories,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  categories: ClaimCategory[];
}) {
  const [title, setTitle] = useState("");
  const [items, setItems] = useState<
    {
      category_id: number;
      description: string;
      amount: number;
      expense_date: string;
    }[]
  >([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const totalAmount = items.reduce((sum, item) => sum + item.amount, 0);

  function addItem(item: {
    category_id: number;
    description: string;
    amount: number;
    expense_date: string;
  }) {
    setItems([...items, item]);
  }

  function removeItem(index: number) {
    setItems(items.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || items.length === 0) return;

    setIsSubmitting(true);
    try {
      const claim = await claimsApi.createClaim({ title: title.trim() });

      for (const item of items) {
        await claimsApi.addItem(claim.id, item);
      }

      await claimsApi.submitClaim(claim.id);

      toast.success("Claim submitted successfully");
      setTitle("");
      setItems([]);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to submit claim";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="relative w-full max-w-2xl mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Receipt className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              New Claim
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
          <AppInput
            label="Claim Title"
            value={title}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setTitle(e.target.value)
            }
            placeholder="e.g. March business travel expenses"
            required
          />

          {/* Items List */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-2">
              Expense Items
            </label>

            {items.length > 0 && (
              <div className="space-y-2 mb-3">
                {items.map((item, index) => {
                  const cat = categories.find((c) => c.id === item.category_id);
                  return (
                    <div
                      key={index}
                      className="flex items-center justify-between gap-3 p-2 rounded-[8px] border border-[var(--color-gray-200)] bg-white"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-[var(--color-gray-900)]">
                          {item.description}
                        </p>
                        <p className="text-xs text-[var(--color-gray-500)]">
                          {cat?.name ?? "Unknown"} &middot; {item.expense_date}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-sm font-medium text-[var(--color-gray-900)]">
                          {formatCurrency(item.amount)}
                        </span>
                        <button
                          type="button"
                          onClick={() => removeItem(index)}
                          className="p-1 rounded hover:bg-red-50 text-[var(--color-gray-400)] hover:text-red-600 transition-colors"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <AddItemRow categories={categories} onAdd={addItem} />

            {items.length > 0 && (
              <div className="flex justify-end mt-3">
                <p className="text-sm font-semibold text-[var(--color-gray-900)]">
                  Total: {formatCurrency(totalAmount)}
                </p>
              </div>
            )}
          </div>

          <p className="text-xs text-[var(--color-gray-500)]">
            You can upload receipts for each item after the claim is created.
          </p>

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
              disabled={!title.trim() || items.length === 0}
              className="flex-1"
            >
              Submit Claim
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* -- Reject Reason Modal -------------------------------------------- */

function RejectReasonModal({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
  isSubmitting: boolean;
}) {
  const [reason, setReason] = useState("");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-sm mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <h2 className="text-lg font-semibold text-[var(--color-gray-900)] mb-4">
          Reason for Rejection
        </h2>
        <AppInput
          variant="textarea"
          value={reason}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
            setReason(e.target.value)
          }
          placeholder="Enter reason for rejection..."
          required
        />
        <div className="flex gap-3 mt-4">
          <AppButton
            variant="outlined"
            size="sm"
            onClick={onClose}
            className="flex-1"
          >
            Cancel
          </AppButton>
          <AppButton
            variant="danger"
            size="sm"
            onClick={() => onConfirm(reason)}
            loading={isSubmitting}
            disabled={!reason.trim()}
            className="flex-1"
          >
            Reject
          </AppButton>
        </div>
      </div>
    </div>
  );
}

/* -- Admin Pending Claims ------------------------------------------- */

function PendingClaims({
  claims,
  onAction,
}: {
  claims: Claim[];
  onAction: () => void;
}) {
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [showRejectModal, setShowRejectModal] = useState<number | null>(null);

  const pending = claims.filter((c) => c.status === "pending");

  if (pending.length === 0) {
    return (
      <AppCard variant="standard">
        <div className="text-center py-4">
          <Check className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
          <p className="text-sm text-[var(--color-gray-600)]">
            No pending claims
          </p>
        </div>
      </AppCard>
    );
  }

  async function handleApprove(id: number) {
    setActionLoading(id);
    try {
      await claimsApi.approveClaim(id);
      toast.success("Claim approved");
      onAction();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to approve claim";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject(id: number, reason: string) {
    setActionLoading(id);
    try {
      await claimsApi.rejectClaim(id, reason);
      toast.success("Claim rejected");
      setShowRejectModal(null);
      onAction();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to reject claim";
      toast.error(message);
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <>
      <AppCard
        variant="standard"
        header={
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Pending Claims
            </h2>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
              {pending.length} pending
            </span>
          </div>
        }
      >
        <div className="space-y-3 -mx-5 -my-4 px-5 py-4">
          {pending.map((claim) => (
            <div
              key={claim.id}
              className="flex items-center justify-between gap-3 p-3 rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-gray-50)]"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                  {claim.employee_name}
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">
                  {claim.title} &middot; {formatCurrency(claim.total_amount)}{" "}
                  &middot; {(claim.items ?? []).length} item
                  {(claim.items ?? []).length !== 1 ? "s" : ""}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-sm font-semibold text-[var(--color-gray-900)]">
                  {formatCurrency(claim.total_amount)}
                </span>
                <AppButton
                  variant="primary"
                  size="sm"
                  onClick={() => handleApprove(claim.id)}
                  loading={actionLoading === claim.id}
                  disabled={actionLoading !== null}
                >
                  <Check className="h-4 w-4" />
                </AppButton>
                <AppButton
                  variant="danger"
                  size="sm"
                  onClick={() => setShowRejectModal(claim.id)}
                  disabled={actionLoading !== null}
                >
                  <X className="h-4 w-4" />
                </AppButton>
              </div>
            </div>
          ))}
        </div>
      </AppCard>

      <RejectReasonModal
        isOpen={showRejectModal !== null}
        onClose={() => setShowRejectModal(null)}
        onConfirm={(reason) => {
          if (showRejectModal !== null) {
            handleReject(showRejectModal, reason);
          }
        }}
        isSubmitting={actionLoading !== null}
      />
    </>
  );
}

/* -- Claims List ---------------------------------------------------- */

function ClaimsList({
  claims,
  isLoading,
  isAdmin,
}: {
  claims: Claim[];
  isLoading: boolean;
  isAdmin: boolean;
}) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  if (isLoading) {
    return (
      <AppCard variant="standard">
        <div className="-mx-5 -my-4">
          <TableSkeleton />
        </div>
      </AppCard>
    );
  }

  if (claims.length === 0) {
    return (
      <EmptyState
        icon={<Receipt className="h-12 w-12" aria-hidden="true" />}
        message="No claims"
        description={
          isAdmin
            ? "No claims have been submitted yet."
            : "You have not submitted any claims yet."
        }
      />
    );
  }

  return (
    <AppCard variant="standard">
      <div className="overflow-x-auto -mx-5 -my-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-gray-200)]">
              {isAdmin && (
                <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                  Employee
                </th>
              )}
              <th className="text-left py-3 px-5 font-medium text-[var(--color-gray-500)]">
                Title
              </th>
              <th className="text-right py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Amount
              </th>
              <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Items
              </th>
              <th className="text-center py-3 px-3 font-medium text-[var(--color-gray-500)]">
                Status
              </th>
              <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                Date
              </th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <>
                <tr
                  key={claim.id}
                  onClick={() =>
                    setExpandedId(expandedId === claim.id ? null : claim.id)
                  }
                  className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors cursor-pointer"
                >
                  {isAdmin && (
                    <td className="py-3 px-5 font-medium text-[var(--color-gray-900)]">
                      {claim.employee_name}
                    </td>
                  )}
                  <td className="py-3 px-5 text-[var(--color-gray-900)]">
                    <div className="flex items-center gap-2">
                      {claim.title}
                      {expandedId === claim.id ? (
                        <ChevronUp className="h-4 w-4 text-[var(--color-gray-400)]" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-[var(--color-gray-400)]" />
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right font-medium text-[var(--color-gray-900)]">
                    {formatCurrency(claim.total_amount)}
                  </td>
                  <td className="py-3 px-3 text-center text-[var(--color-gray-600)]">
                    {(claim.items ?? []).length}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <StatusBadge status={claim.status} />
                  </td>
                  <td className="py-3 px-5 text-center text-[var(--color-gray-600)]">
                    {(claim.created_at ?? "").split("T")[0] || "-"}
                  </td>
                </tr>
                {expandedId === claim.id && (
                  <tr key={`${claim.id}-detail`}>
                    <td
                      colSpan={isAdmin ? 6 : 5}
                      className="px-5 py-3 bg-[var(--color-gray-50)]"
                    >
                      {(claim.items ?? []).length > 0 ? (
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-[var(--color-gray-500)] mb-2">
                            Expense Items
                          </p>
                          {(claim.items ?? []).map((item) => (
                            <div
                              key={item.id}
                              className="flex items-center justify-between text-sm p-2 rounded-lg bg-white border border-[var(--color-gray-200)]"
                            >
                              <div>
                                <p className="text-[var(--color-gray-900)]">
                                  {item.description}
                                </p>
                                <p className="text-xs text-[var(--color-gray-500)]">
                                  {item.category_name} &middot;{" "}
                                  {item.expense_date}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-[var(--color-gray-900)]">
                                  {formatCurrency(item.amount)}
                                </span>
                                {item.receipt_url && (
                                  <span className="text-xs text-emerald-600">
                                    Receipt
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-[var(--color-gray-500)]">
                          No items in this claim.
                        </p>
                      )}

                      {claim.rejection_reason && (
                        <div className="mt-3">
                          <p className="text-xs font-medium text-[var(--color-gray-500)] mb-0.5">
                            Rejection Reason
                          </p>
                          <p className="text-sm text-red-700">
                            {claim.rejection_reason}
                          </p>
                        </div>
                      )}

                      {claim.approver_name && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-[var(--color-gray-500)] mb-0.5">
                            Reviewed By
                          </p>
                          <p className="text-sm text-[var(--color-gray-700)]">
                            {claim.approver_name}
                          </p>
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </AppCard>
  );
}

/* -- Page ---------------------------------------------------------- */

export default function ClaimsPage() {
  const { user } = useAuth();
  const isAdmin =
    user?.role === "owner" ||
    user?.role === "hr_manager" ||
    user?.role === "consultant";

  const [categories, setCategories] = useState<ClaimCategory[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewClaimModal, setShowNewClaimModal] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [catsRes, claimsRes] = await Promise.all([
        claimsApi.listCategories(),
        claimsApi.listClaims(
          statusFilter ? { status: statusFilter } : undefined,
        ),
      ]);
      setCategories(catsRes.categories ?? []);
      setClaims(claimsRes.claims ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to load claims data. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalPending = claims.filter((c) => c.status === "pending").length;
  const totalApproved = claims
    .filter((c) => c.status === "approved")
    .reduce((sum, c) => sum + c.total_amount, 0);

  if (error && !isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <div className="flex items-center gap-3">
          <Receipt
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            {isAdmin ? "Claims Management" : "My Claims"}
          </h1>
        </div>
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-error)] mb-3">{error}</p>
            <AppButton variant="outlined" size="sm" onClick={fetchData}>
              Try again
            </AppButton>
          </div>
        </AppCard>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Receipt
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              {isAdmin ? "Claims Management" : "My Claims"}
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              {isAdmin
                ? "Review and manage employee expense claims"
                : "Submit and track your expense claims"}
            </p>
          </div>
        </div>
        {!isAdmin && (
          <AppButton
            variant="primary"
            size="sm"
            onClick={() => setShowNewClaimModal(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            New Claim
          </AppButton>
        )}
      </div>

      {/* Quick Stats */}
      {!isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <AppCard variant="flat">
            <div className="text-center">
              <p className="text-2xl font-bold text-amber-600">
                {totalPending}
              </p>
              <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                Pending
              </p>
            </div>
          </AppCard>
          <AppCard variant="flat">
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-600">
                {formatCurrency(totalApproved)}
              </p>
              <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                Total Approved
              </p>
            </div>
          </AppCard>
          <AppCard variant="flat">
            <div className="text-center">
              <p className="text-2xl font-bold text-[var(--color-gray-900)]">
                {claims.length}
              </p>
              <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                Total Claims
              </p>
            </div>
          </AppCard>
        </div>
      )}

      {/* Admin: Pending Claims */}
      {isAdmin && !isLoading && (
        <PendingClaims claims={claims} onAction={fetchData} />
      )}

      {/* Filter Bar */}
      <div className="flex items-center gap-3">
        <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
          {isAdmin ? "All Claims" : "My Claims"}
        </h2>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="
            ml-auto rounded-[8px] border px-3 py-1.5 text-sm min-h-[36px]
            bg-[var(--color-surface-input)] text-[var(--foreground)]
            border-[var(--color-surface-input-border)]
            transition-colors
            focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
            focus:border-[var(--color-surface-input-focus)]
          "
        >
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      {/* Claims Table */}
      <ClaimsList claims={claims} isLoading={isLoading} isAdmin={isAdmin} />

      {/* New Claim Modal */}
      <NewClaimModal
        isOpen={showNewClaimModal}
        onClose={() => setShowNewClaimModal(false)}
        onSuccess={fetchData}
        categories={categories}
      />
    </div>
  );
}
