"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Users,
  Plus,
  Search,
  Building2,
  ArrowUpDown,
  LayoutGrid,
  List,
  ChevronRight,
} from "lucide-react";
import {
  AppCard,
  AppButton,
  AppInput,
  RiskTierBadge,
  LoadingState,
  ErrorState,
  EmptyState,
  toast,
} from "@/components/design-system";
import type { RiskTierLevel } from "@/components/design-system";
import { clientsApi } from "@/services/api/clients";
import type { ClientCompany } from "@/types/api";

/* ── Types ────────────────────────────────────────────────── */

type SortField = keyof ClientCompany;

/* ── Page ──────────────────────────────────────────────────── */

export default function ClientsPage() {
  const [clients, setClients] = useState<ClientCompany[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("All Sectors");
  const [viewMode, setViewMode] = useState<"grid" | "table">("table");
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortAsc, setSortAsc] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [addingClient, setAddingClient] = useState(false);
  const [newClient, setNewClient] = useState({
    name: "",
    uen: "",
    sector: "Technology",
    employee_count: "",
  });

  const fetchClients = useCallback(() => {
    setLoading(true);
    setFetchError(null);
    clientsApi
      .list()
      .then((data) => {
        setClients(data.clients);
      })
      .catch((err) => {
        setFetchError(
          err instanceof Error ? err.message : "Failed to load clients",
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  /* Derive unique sectors from real data */
  const sectors = useMemo(() => {
    const unique = new Set(clients.map((c) => c.sector).filter(Boolean));
    return ["All Sectors", ...Array.from(unique).sort()];
  }, [clients]);

  const filtered = useMemo(() => {
    return clients
      .filter((c) => {
        const matchSearch =
          !search ||
          c.name.toLowerCase().includes(search.toLowerCase()) ||
          c.uen.toLowerCase().includes(search.toLowerCase());
        const matchSector =
          sectorFilter === "All Sectors" || c.sector === sectorFilter;
        return matchSearch && matchSector;
      })
      .sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        if (aVal == null && bVal == null) return 0;
        if (aVal == null) return 1;
        if (bVal == null) return -1;
        if (typeof aVal === "string" && typeof bVal === "string") {
          return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        }
        return sortAsc
          ? (aVal as number) - (bVal as number)
          : (bVal as number) - (aVal as number);
      });
  }, [clients, search, sectorFilter, sortField, sortAsc]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const handleAddClient = async () => {
    if (!newClient.name.trim()) {
      toast.error("Company name is required");
      return;
    }
    if (!newClient.uen.trim()) {
      toast.error("UEN is required");
      return;
    }

    setAddingClient(true);
    try {
      const created = await clientsApi.create({
        name: newClient.name.trim(),
        uen: newClient.uen.trim(),
        sector: newClient.sector,
        employee_count: parseInt(newClient.employee_count) || 0,
      });
      setClients((prev) => [...prev, created]);
      setShowAddForm(false);
      setNewClient({
        name: "",
        uen: "",
        sector: "Technology",
        employee_count: "",
      });
      toast.success("Client added successfully");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add client");
    } finally {
      setAddingClient(false);
    }
  };

  /* ── Metric calculations ── */
  const greenCount = clients.filter((c) => c.risk_tier === "green").length;
  const amberCount = clients.filter((c) => c.risk_tier === "amber").length;
  const redCount = clients.filter((c) => c.risk_tier === "red").length;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Clients
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Manage and switch between your client companies.
            </p>
          </div>
        </div>
        <AppButton onClick={() => setShowAddForm(true)}>
          <Plus className="h-4 w-4 mr-1.5" /> Add Client
        </AppButton>
      </div>

      {/* Add client form */}
      {showAddForm && (
        <AppCard variant="elevated">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-4">
            Add New Client
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AppInput
              label="Company Name"
              value={newClient.name}
              onChange={(e) =>
                setNewClient({ ...newClient, name: e.target.value })
              }
              placeholder="ABC Pte Ltd"
            />
            <AppInput
              label="UEN"
              value={newClient.uen}
              onChange={(e) =>
                setNewClient({ ...newClient, uen: e.target.value })
              }
              placeholder="202301234A"
            />
            <div>
              <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-1">
                Sector
              </label>
              <select
                value={newClient.sector}
                onChange={(e) =>
                  setNewClient({ ...newClient, sector: e.target.value })
                }
                className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-gray-200)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              >
                <option value="Technology">Technology</option>
                <option value="Manufacturing">Manufacturing</option>
                <option value="Healthcare">Healthcare</option>
                <option value="Finance">Finance</option>
                <option value="Food & Beverage">Food & Beverage</option>
                <option value="Retail">Retail</option>
                <option value="Construction">Construction</option>
                <option value="Logistics">Logistics</option>
                <option value="Services">Professional Services</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <AppInput
              label="Employee Count"
              value={newClient.employee_count}
              onChange={(e) =>
                setNewClient({ ...newClient, employee_count: e.target.value })
              }
              placeholder="50"
              variant="number"
            />
          </div>
          <div className="flex gap-2 mt-4">
            <AppButton onClick={handleAddClient} loading={addingClient}>
              Add Client
            </AppButton>
            <AppButton variant="text" onClick={() => setShowAddForm(false)}>
              Cancel
            </AppButton>
          </div>
        </AppCard>
      )}

      {/* Loading state */}
      {loading && <LoadingState variant="card" count={4} />}

      {/* Error state */}
      {!loading && fetchError && (
        <ErrorState
          variant="server"
          title="Failed to load clients"
          description={fetchError}
          onRetry={fetchClients}
        />
      )}

      {/* Empty state */}
      {!loading && !fetchError && clients.length === 0 && !showAddForm && (
        <EmptyState
          icon={
            <Users
              className="h-12 w-12 text-[var(--color-gray-400)]"
              aria-hidden="true"
            />
          }
          message="No clients yet"
          description="Add your first client company to get started with compliance management."
          action={
            <AppButton onClick={() => setShowAddForm(true)}>
              <Plus className="h-4 w-4 mr-1.5" /> Add Client
            </AppButton>
          }
        />
      )}

      {/* Content - only show when we have data */}
      {!loading && !fetchError && clients.length > 0 && (
        <>
          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
            <div className="flex gap-2 items-center flex-wrap">
              <div className="relative">
                <Search
                  className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-gray-400)]"
                  aria-hidden="true"
                />
                <input
                  type="text"
                  placeholder="Search clients..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 pr-3 py-2 text-sm rounded-lg border border-[var(--color-gray-200)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] min-w-[240px]"
                />
              </div>
              <select
                value={sectorFilter}
                onChange={(e) => setSectorFilter(e.target.value)}
                className="px-3 py-2 text-sm rounded-lg border border-[var(--color-gray-200)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              >
                {sectors.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-1">
              <button
                onClick={() => setViewMode("table")}
                className={`p-2 rounded-lg transition-colors ${viewMode === "table" ? "bg-[var(--color-primary-bg)] text-[var(--color-primary)]" : "text-[var(--color-gray-400)] hover:text-[var(--color-gray-600)]"}`}
                aria-label="Table view"
              >
                <List className="h-5 w-5" />
              </button>
              <button
                onClick={() => setViewMode("grid")}
                className={`p-2 rounded-lg transition-colors ${viewMode === "grid" ? "bg-[var(--color-primary-bg)] text-[var(--color-primary)]" : "text-[var(--color-gray-400)] hover:text-[var(--color-gray-600)]"}`}
                aria-label="Grid view"
              >
                <LayoutGrid className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard label="Total Clients" value={String(clients.length)} />
            <MetricCard
              label="Green"
              value={String(greenCount)}
              color="var(--color-risk-green)"
            />
            <MetricCard
              label="Amber"
              value={String(amberCount)}
              color="var(--color-risk-amber)"
            />
            <MetricCard
              label="Red"
              value={String(redCount)}
              color="var(--color-risk-red)"
            />
          </div>

          {/* Table view */}
          {viewMode === "table" && (
            <AppCard variant="standard">
              <div className="overflow-x-auto -mx-4 sm:mx-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--color-gray-200)]">
                      <SortableHeader
                        label="Company"
                        field="name"
                        currentField={sortField}
                        asc={sortAsc}
                        onClick={toggleSort}
                      />
                      <SortableHeader
                        label="Sector"
                        field="sector"
                        currentField={sortField}
                        asc={sortAsc}
                        onClick={toggleSort}
                      />
                      <SortableHeader
                        label="Employees"
                        field="employee_count"
                        currentField={sortField}
                        asc={sortAsc}
                        onClick={toggleSort}
                      />
                      <SortableHeader
                        label="Compliance"
                        field="compliance_score"
                        currentField={sortField}
                        asc={sortAsc}
                        onClick={toggleSort}
                      />
                      <SortableHeader
                        label="Last Activity"
                        field="last_activity"
                        currentField={sortField}
                        asc={sortAsc}
                        onClick={toggleSort}
                      />
                      <th className="px-4 py-3 text-right font-medium text-[var(--color-gray-500)]" />
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((client) => (
                      <tr
                        key={client.id}
                        className="border-b border-[var(--color-gray-100)] hover:bg-[var(--color-gray-50)] transition-colors cursor-pointer"
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg bg-[var(--color-primary-bg)] flex items-center justify-center">
                              <Building2 className="h-4 w-4 text-[var(--color-primary)]" />
                            </div>
                            <div>
                              <p className="font-medium text-[var(--color-gray-900)]">
                                {client.name}
                              </p>
                              <p className="text-xs text-[var(--color-gray-400)]">
                                {client.uen}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-[var(--color-gray-600)]">
                          {client.sector || "—"}
                        </td>
                        <td className="px-4 py-3 text-[var(--color-gray-600)]">
                          {client.employee_count}
                        </td>
                        <td className="px-4 py-3">
                          {client.compliance_score != null &&
                          client.risk_tier ? (
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-[var(--color-gray-900)]">
                                {client.compliance_score}
                              </span>
                              <RiskTierBadge
                                tier={client.risk_tier as RiskTierLevel}
                              />
                            </div>
                          ) : (
                            <span className="text-xs text-[var(--color-gray-400)]">
                              Not checked
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-[var(--color-gray-500)]">
                          {client.last_activity
                            ? new Date(client.last_activity).toLocaleDateString(
                                "en-SG",
                                {
                                  day: "numeric",
                                  month: "short",
                                  year: "numeric",
                                },
                              )
                            : "—"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button className="p-1 rounded hover:bg-[var(--color-gray-100)] text-[var(--color-gray-400)]">
                            <ChevronRight className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filtered.length === 0 && (
                <p className="text-center text-sm text-[var(--color-gray-400)] py-8">
                  No clients match your filters.
                </p>
              )}
            </AppCard>
          )}

          {/* Grid view */}
          {viewMode === "grid" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((client) => (
                <AppCard key={client.id} variant="standard">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-lg bg-[var(--color-primary-bg)] flex items-center justify-center">
                          <Building2 className="h-5 w-5 text-[var(--color-primary)]" />
                        </div>
                        <div>
                          <p className="font-medium text-[var(--color-gray-900)]">
                            {client.name}
                          </p>
                          <p className="text-xs text-[var(--color-gray-400)]">
                            {client.uen}
                          </p>
                        </div>
                      </div>
                      {client.risk_tier && (
                        <RiskTierBadge
                          tier={client.risk_tier as RiskTierLevel}
                        />
                      )}
                    </div>
                    <div className="flex gap-4 text-xs text-[var(--color-gray-500)]">
                      <span>{client.sector || "No sector"}</span>
                      <span>{client.employee_count} employees</span>
                    </div>
                    <div className="flex items-center justify-between pt-2 border-t border-[var(--color-gray-100)]">
                      {client.compliance_score != null ? (
                        <span className="text-sm font-medium text-[var(--color-gray-900)]">
                          Score: {client.compliance_score}/100
                        </span>
                      ) : (
                        <span className="text-xs text-[var(--color-gray-400)]">
                          No compliance check yet
                        </span>
                      )}
                      <AppButton variant="text" size="sm">
                        View <ChevronRight className="h-3 w-3 ml-1" />
                      </AppButton>
                    </div>
                  </div>
                </AppCard>
              ))}
              {filtered.length === 0 && (
                <p className="col-span-full text-center text-sm text-[var(--color-gray-400)] py-8">
                  No clients match your filters.
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── Helper components ────────────────────────────────────── */

function MetricCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <AppCard variant="flat">
      <div className="text-center">
        <p className="text-xs text-[var(--color-gray-500)]">{label}</p>
        <p
          className="text-2xl font-bold mt-1"
          style={{ color: color ?? "var(--color-gray-900)" }}
        >
          {value}
        </p>
      </div>
    </AppCard>
  );
}

function SortableHeader({
  label,
  field,
  currentField,
  asc,
  onClick,
}: {
  label: string;
  field: SortField;
  currentField: SortField;
  asc: boolean;
  onClick: (field: SortField) => void;
}) {
  const active = currentField === field;
  return (
    <th className="px-4 py-3 text-left font-medium text-[var(--color-gray-500)]">
      <button
        onClick={() => onClick(field)}
        className="flex items-center gap-1 hover:text-[var(--color-gray-700)] transition-colors"
      >
        {label}
        <ArrowUpDown
          className={`h-3 w-3 ${active ? "text-[var(--color-primary)]" : ""}`}
        />
        {active && (
          <span className="sr-only">{asc ? "ascending" : "descending"}</span>
        )}
      </button>
    </th>
  );
}
