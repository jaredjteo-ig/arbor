"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  EmployeePicker,
  EmptyState,
  toast,
} from "@/components/design-system";
import {
  Package,
  Plus,
  MapPin,
  Tag,
  ArrowRight,
  X,
  UserCheck,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { AdminGuard } from "@/components/auth/AdminGuard";
import {
  inventoryApi,
  type InventoryLocation,
  type InventoryCategory,
  type InventoryItem,
} from "@/services/api/inventory";

/* ── Helpers ──────────────────────────────────────────────── */

function formatCurrency(amount: number): string {
  return `$${(amount ?? 0).toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/* ── Status styles ────────────────────────────────────────── */

const ITEM_STATUS_STYLES: Record<string, string> = {
  available: "bg-emerald-50 text-emerald-700 border-emerald-200",
  reserved: "bg-amber-50 text-amber-700 border-amber-200",
  issued: "bg-blue-50 text-blue-700 border-blue-200",
  maintenance: "bg-orange-50 text-orange-700 border-orange-200",
  retired:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] border-[var(--color-gray-200)]",
};

function StatusBadge({ status }: { status: string }) {
  const s = status || "available";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${ITEM_STATUS_STYLES[s] || ITEM_STATUS_STYLES.available}`}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

/* ── Skeleton ─────────────────────────────────────────────── */

function CardsSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: 6 }, (_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-5"
        >
          <div className="h-5 w-32 bg-[var(--color-gray-200)] rounded mb-2" />
          <div className="h-3 w-20 bg-[var(--color-gray-200)] rounded mb-2" />
          <div className="h-3 w-24 bg-[var(--color-gray-200)] rounded" />
        </div>
      ))}
    </div>
  );
}

/* ── Create Item Modal ────────────────────────────────────── */

function CreateItemModal({
  isOpen,
  onClose,
  onSuccess,
  categories,
  locations,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  categories: InventoryCategory[];
  locations: InventoryLocation[];
}) {
  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [serialNumber, setSerialNumber] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [purchaseCost, setPurchaseCost] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !categoryId || !locationId) return;
    setIsSubmitting(true);
    try {
      await inventoryApi.createItem({
        name: name.trim(),
        sku: sku.trim(),
        category_id: Number(categoryId),
        location_id: Number(locationId),
        serial_number: serialNumber.trim(),
        quantity: Number(quantity) || 1,
        purchase_cost: Number(purchaseCost) || 0,
      });
      toast.success("Inventory item added");
      setName("");
      setSku("");
      setCategoryId("");
      setLocationId("");
      setSerialNumber("");
      setQuantity("1");
      setPurchaseCost("");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to create item";
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
      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Package className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Add Item
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
          <div className="grid grid-cols-2 gap-3">
            <AppInput
              label="Name"
              value={name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setName(e.target.value)
              }
              required
            />
            <AppInput
              label="SKU"
              value={sku}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setSku(e.target.value)
              }
              placeholder="e.g. ITM-001"
            />
          </div>
          <div>
            <label
              htmlFor="inv-category"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Category
            </label>
            <select
              id="inv-category"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
              required
            >
              <option value="">Select category</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label
              htmlFor="inv-location"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Location
            </label>
            <select
              id="inv-location"
              value={locationId}
              onChange={(e) => setLocationId(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
              required
            >
              <option value="">Select location</option>
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <AppInput
            label="Serial Number"
            value={serialNumber}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setSerialNumber(e.target.value)
            }
          />
          <div className="grid grid-cols-2 gap-3">
            <AppInput
              label="Quantity"
              value={quantity}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setQuantity(e.target.value)
              }
            />
            <AppInput
              label="Purchase Cost"
              value={purchaseCost}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setPurchaseCost(e.target.value)
              }
              placeholder="0.00"
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
              Add Item
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Issue Item Modal ──────────────────────────────────────── */

function IssueItemModal({
  isOpen,
  onClose,
  onSuccess,
  itemName,
  itemId,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  itemName: string;
  itemId: number;
}) {
  const [employeeId, setEmployeeId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!employeeId || employeeId <= 0) return;
    setIsSubmitting(true);
    try {
      await inventoryApi.issueItem(itemId, { employee_id: employeeId });
      toast.success("Item issued");
      setEmployeeId(null);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to issue item";
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
      <div className="relative w-full max-w-sm mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Issue Item
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
          Issuing{" "}
          <span className="font-medium text-[var(--color-gray-900)]">
            {itemName}
          </span>
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <EmployeePicker
            label="Employee"
            value={employeeId}
            onChange={(id) => setEmployeeId(id)}
          />
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
              disabled={!employeeId}
              className="flex-1"
            >
              Issue
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function InventoryPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "hr_manager";

  const [locations, setLocations] = useState<InventoryLocation[]>([]);
  const [categories, setCategories] = useState<InventoryCategory[]>([]);
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [issueTarget, setIssueTarget] = useState<{
    id: number;
    name: string;
  } | null>(null);
  const [search, setSearch] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [locRes, catRes, itemRes] = await Promise.all([
        inventoryApi.listLocations(),
        inventoryApi.listCategories(),
        inventoryApi.listItems(),
      ]);
      setLocations(locRes.locations ?? []);
      setCategories(catRes.categories ?? []);
      setItems(itemRes.items ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load inventory.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleReturn(itemId: number) {
    try {
      await inventoryApi.returnItem(itemId, {});
      toast.success("Item returned");
      fetchData();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to return item";
      toast.error(message);
    }
  }

  const filtered = items.filter((item) => {
    const matchesSearch =
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.sku.toLowerCase().includes(search.toLowerCase());
    const matchesCategory =
      !filterCategory || item.category_id === Number(filterCategory);
    const matchesStatus = !filterStatus || item.status === filterStatus;
    return matchesSearch && matchesCategory && matchesStatus;
  });

  if (error && !isLoading) {
    return (
      <AdminGuard>
        <div className="max-w-5xl mx-auto space-y-6 pb-8">
          <div className="flex items-center gap-3">
            <Package
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Inventory
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
      </AdminGuard>
    );
  }

  return (
    <AdminGuard>
      <div className="max-w-5xl mx-auto space-y-6 pb-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Package
              className="h-7 w-7 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <div>
              <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
                Inventory
              </h1>
              <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
                Manage company assets, equipment, and supplies
              </p>
            </div>
          </div>
          {isAdmin && (
            <AppButton
              variant="primary"
              size="sm"
              onClick={() => setShowModal(true)}
            >
              <Plus className="h-4 w-4 mr-1" /> Add Item
            </AppButton>
          )}
        </div>

        {/* Summary cards */}
        {!isLoading && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <AppCard variant="flat">
              <div className="flex items-center gap-2 mb-1">
                <MapPin className="h-4 w-4 text-blue-600" />
                <p className="text-xs text-[var(--color-gray-500)]">
                  Locations
                </p>
              </div>
              <p className="text-xl font-bold text-[var(--color-gray-900)]">
                {locations.length}
              </p>
            </AppCard>
            <AppCard variant="flat">
              <div className="flex items-center gap-2 mb-1">
                <Tag className="h-4 w-4 text-violet-600" />
                <p className="text-xs text-[var(--color-gray-500)]">
                  Categories
                </p>
              </div>
              <p className="text-xl font-bold text-[var(--color-gray-900)]">
                {categories.length}
              </p>
            </AppCard>
            <AppCard variant="flat">
              <p className="text-xs text-[var(--color-gray-500)] mb-1">
                Total Items
              </p>
              <p className="text-xl font-bold text-[var(--color-gray-900)]">
                {items.length}
              </p>
            </AppCard>
            <AppCard variant="flat">
              <p className="text-xs text-[var(--color-gray-500)] mb-1">
                Available
              </p>
              <p className="text-xl font-bold text-emerald-600">
                {items.filter((i) => i.status === "available").length}
              </p>
            </AppCard>
          </div>
        )}

        {/* Filters */}
        <div className="flex gap-3 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <AppInput
              value={search}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setSearch(e.target.value)
              }
              placeholder="Search by name or SKU..."
            />
          </div>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="rounded-[8px] border px-3 py-2 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
          >
            <option value="">All Statuses</option>
            <option value="available">Available</option>
            <option value="issued">Issued</option>
            <option value="reserved">Reserved</option>
            <option value="maintenance">Maintenance</option>
            <option value="retired">Retired</option>
          </select>
        </div>

        {/* Items grid */}
        {isLoading ? (
          <CardsSkeleton />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Package className="h-12 w-12" aria-hidden="true" />}
            message={
              search || filterCategory || filterStatus
                ? "No matching items"
                : "No inventory items"
            }
            description={
              search
                ? "Try a different search."
                : "Add items to start managing your inventory."
            }
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((item) => (
              <AppCard key={item.id} variant="standard">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="text-sm font-semibold text-[var(--color-gray-900)] truncate">
                    {item.name}
                  </h3>
                  <StatusBadge status={item.status} />
                </div>
                <div className="space-y-1 text-xs text-[var(--color-gray-500)] mb-3">
                  {item.sku && <p>SKU: {item.sku}</p>}
                  {item.category_name && <p>Category: {item.category_name}</p>}
                  {item.location_name && <p>Location: {item.location_name}</p>}
                  {item.assigned_to_name && (
                    <p>Assigned to: {item.assigned_to_name}</p>
                  )}
                  {item.purchase_cost > 0 && (
                    <p>Value: {formatCurrency(item.purchase_cost)}</p>
                  )}
                </div>
                {isAdmin && (
                  <div className="flex gap-2">
                    {item.status === "available" && (
                      <AppButton
                        variant="primary"
                        size="sm"
                        onClick={() =>
                          setIssueTarget({ id: item.id, name: item.name })
                        }
                        className="flex-1"
                      >
                        Issue
                      </AppButton>
                    )}
                    {item.status === "issued" && (
                      <AppButton
                        variant="outlined"
                        size="sm"
                        onClick={() => handleReturn(item.id)}
                        className="flex-1"
                      >
                        Return
                      </AppButton>
                    )}
                  </div>
                )}
              </AppCard>
            ))}
          </div>
        )}

        <CreateItemModal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          onSuccess={fetchData}
          categories={categories}
          locations={locations}
        />

        <IssueItemModal
          isOpen={issueTarget !== null}
          onClose={() => setIssueTarget(null)}
          onSuccess={fetchData}
          itemId={issueTarget?.id ?? 0}
          itemName={issueTarget?.name ?? ""}
        />
      </div>
    </AdminGuard>
  );
}
