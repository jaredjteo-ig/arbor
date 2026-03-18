"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  EmptyState,
  toast,
} from "@/components/design-system";
import { Package, Plus, CheckCircle, X } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  inventoryApi,
  type InventoryItem,
  type InventoryRequest,
} from "@/services/api/inventory";

/* ── Status badge ─────────────────────────────────────────── */

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-blue-50 text-blue-700 border-blue-200",
  issued: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
  available: "bg-emerald-50 text-emerald-700 border-emerald-200",
  reserved: "bg-amber-50 text-amber-700 border-amber-200",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[status] || STATUS_STYLES.pending}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

/* ── Skeleton ─────────────────────────────────────────────── */

function CardsSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-5"
        >
          <div className="h-5 w-32 bg-[var(--color-gray-200)] rounded mb-2" />
          <div className="h-3 w-24 bg-[var(--color-gray-200)] rounded" />
        </div>
      ))}
    </div>
  );
}

/* ── Request Item Modal ───────────────────────────────────── */

function RequestItemModal({
  isOpen,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) return;
    setIsSubmitting(true);
    try {
      await inventoryApi.createRequest({ description: description.trim() });
      toast.success("Item request submitted");
      setDescription("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to submit request";
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
      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Package className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Request Item
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
            variant="textarea"
            label="What do you need?"
            value={description}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
              setDescription(e.target.value)
            }
            placeholder="Describe the item you need, e.g. 'Laptop for development work' or 'Standing desk converter'"
            required
          />
          <p className="text-xs text-[var(--color-gray-500)]">
            Your request will be reviewed by your manager.
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
              className="flex-1"
            >
              Submit Request
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function MyInventoryPage() {
  const { user } = useAuth();

  const [myItems, setMyItems] = useState<InventoryItem[]>([]);
  const [myRequests, setMyRequests] = useState<InventoryRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [itemsRes, reqRes] = await Promise.all([
        inventoryApi.listMyItems(),
        inventoryApi.listRequests(),
      ]);
      setMyItems(itemsRes.items ?? []);
      setMyRequests(reqRes.requests ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load your inventory.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleAcknowledge(itemId: number) {
    try {
      await inventoryApi.acknowledgeReceipt(itemId);
      toast.success("Receipt acknowledged");
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to acknowledge receipt";
      toast.error(message);
    }
  }

  if (error && !isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 pb-8">
        <div className="flex items-center gap-3">
          <Package
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            My Inventory
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
          <Package
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              My Inventory
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Items assigned to you and your requests
            </p>
          </div>
        </div>
        <AppButton
          variant="primary"
          size="sm"
          onClick={() => setShowModal(true)}
        >
          <Plus className="h-4 w-4 mr-1" /> Request Item
        </AppButton>
      </div>

      {/* Assigned items */}
      <div>
        <h2 className="text-base font-semibold text-[var(--color-gray-900)] mb-3">
          Assigned to Me
        </h2>
        {isLoading ? (
          <CardsSkeleton />
        ) : myItems.length === 0 ? (
          <EmptyState
            icon={<Package className="h-12 w-12" aria-hidden="true" />}
            message="No items assigned"
            description="Items issued to you will appear here."
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {myItems.map((item) => (
              <AppCard key={item.id} variant="standard">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
                    {item.name}
                  </h3>
                  <StatusBadge status={item.status} />
                </div>
                <div className="space-y-1 text-xs text-[var(--color-gray-500)] mb-3">
                  {item.sku && <p>SKU: {item.sku}</p>}
                  {item.serial_number && <p>S/N: {item.serial_number}</p>}
                  {item.category_name && <p>Category: {item.category_name}</p>}
                </div>
                <AppButton
                  variant="outlined"
                  size="sm"
                  onClick={() => handleAcknowledge(item.id)}
                  className="w-full"
                >
                  <CheckCircle className="h-3.5 w-3.5 mr-1" /> Acknowledge
                  Receipt
                </AppButton>
              </AppCard>
            ))}
          </div>
        )}
      </div>

      {/* My Requests */}
      <div>
        <h2 className="text-base font-semibold text-[var(--color-gray-900)] mb-3">
          My Requests
        </h2>
        {isLoading ? (
          <CardsSkeleton />
        ) : myRequests.length === 0 ? (
          <AppCard variant="standard">
            <p className="text-sm text-[var(--color-gray-500)] text-center py-4">
              No pending requests.
            </p>
          </AppCard>
        ) : (
          <div className="space-y-3">
            {myRequests.map((req) => (
              <AppCard key={req.id} variant="standard">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[var(--color-gray-900)]">
                      {req.description}
                    </p>
                    <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                      Requested{" "}
                      {req.created_at
                        ? new Date(req.created_at).toLocaleDateString("en-SG")
                        : "-"}
                    </p>
                  </div>
                  <StatusBadge status={req.status} />
                </div>
              </AppCard>
            ))}
          </div>
        )}
      </div>

      <RequestItemModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSuccess={fetchData}
      />
    </div>
  );
}
