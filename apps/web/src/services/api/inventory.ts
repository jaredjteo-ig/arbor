/* ── Inventory API Service ────────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface InventoryLocation {
  id: number;
  company_id: number;
  name: string;
  address: string;
  is_default: boolean;
  item_count?: number;
}

export interface InventoryCategory {
  id: number;
  company_id: number;
  name: string;
  description: string;
  parent_id: number | null;
  item_count?: number;
}

export interface InventoryItem {
  id: number;
  company_id: number;
  name: string;
  sku: string;
  category_id: number;
  category_name?: string;
  location_id: number;
  location_name?: string;
  status: "available" | "reserved" | "issued" | "maintenance" | "retired";
  serial_number: string;
  purchase_date: string;
  purchase_cost: number;
  assigned_to?: number;
  assigned_to_name?: string;
  description: string;
  quantity: number;
}

export interface InventoryMovement {
  id: number;
  item_id: number;
  item_name?: string;
  movement_type: "issue" | "return" | "transfer" | "reserve" | "maintenance";
  from_location_id: number | null;
  to_location_id: number | null;
  employee_id: number | null;
  employee_name?: string;
  quantity: number;
  notes: string;
  created_at: string;
}

export interface InventoryRequest {
  id: number;
  employee_id: number;
  employee_name?: string;
  item_id: number | null;
  item_name?: string;
  category_id: number | null;
  category_name?: string;
  description: string;
  status: "pending" | "approved" | "issued" | "rejected";
  notes: string;
  created_at: string;
}

/* ── API ──────────────────────────────────────────────────── */

export const inventoryApi = {
  /* Locations */
  listLocations: () =>
    apiClient.get<{ locations: InventoryLocation[]; count: number }>(
      "/inventory/locations",
    ),
  createLocation: (data: Partial<InventoryLocation>) =>
    apiClient.post<InventoryLocation>("/inventory/locations", data),

  /* Categories */
  listCategories: () =>
    apiClient.get<{ categories: InventoryCategory[]; count: number }>(
      "/inventory/categories",
    ),
  createCategory: (data: Partial<InventoryCategory>) =>
    apiClient.post<InventoryCategory>("/inventory/categories", data),

  /* Items */
  listItems: (params?: Record<string, string>) =>
    apiClient.get<{ items: InventoryItem[]; count: number }>(
      "/inventory/items",
      params,
    ),
  getItem: async (id: number): Promise<InventoryItem> => {
    const resp = await apiClient.get<{ items: InventoryItem[]; count: number }>(
      "/inventory/items",
    );
    const items =
      (resp as { items: InventoryItem[]; count: number }).items ?? [];
    const found = items.find((i) => i.id === id);
    if (!found) throw new Error(`Item ${id} not found`);
    return found;
  },
  createItem: (data: Partial<InventoryItem>) =>
    apiClient.post<InventoryItem>("/inventory/items", data),
  updateItem: (id: number, data: Partial<InventoryItem>) =>
    apiClient.patch<InventoryItem>(`/inventory/items/${id}`, data),

  /* Lifecycle actions */
  issueItem: (id: number, data: { employee_id: number; notes?: string }) =>
    apiClient.post<{ message: string }>(`/inventory/items/${id}/issue`, data),
  reserveItem: (id: number, data: { employee_id: number; notes?: string }) =>
    apiClient.post<{ message: string }>(`/inventory/items/${id}/reserve`, data),
  returnItem: (id: number, data: { notes?: string }) =>
    apiClient.post<{ message: string }>(`/inventory/items/${id}/return`, data),

  /* Movements */
  listMovements: (itemId?: number) =>
    itemId
      ? apiClient.get<{ movements: InventoryMovement[]; count: number }>(
          `/inventory/items/${itemId}/history`,
        )
      : Promise.resolve({ movements: [], count: 0 }),

  /* Requests */
  listRequests: () =>
    apiClient.get<{ requests: InventoryRequest[]; count: number }>(
      "/inventory/requests",
    ),
  createRequest: (
    data: Omit<Partial<InventoryRequest>, "item_id"> & { item_name: string },
  ) => apiClient.post<InventoryRequest>("/inventory/requests", data),
  approveRequest: (id: number) =>
    apiClient.put<{ message: string }>(`/inventory/requests/${id}/approve`),
  rejectRequest: (id: number, reason: string) =>
    apiClient.put<{ message: string }>(`/inventory/requests/${id}/deny`, {
      reason,
    }),

  /* My Items (employee self-service) */
  listMyItems: () =>
    apiClient.get<{ items: InventoryItem[]; count: number }>(
      "/inventory/items/me",
    ),
  acknowledgeReceipt: (itemId: number) =>
    apiClient.post<{ message: string }>(
      `/inventory/items/${itemId}/acknowledge`,
    ),
};
