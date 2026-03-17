"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  EmptyState,
  toast,
} from "@/components/design-system";
import { Users, Plus, Search, X, UserPlus } from "lucide-react";
import { employeesApi, type Employee } from "@/services/api/employees";

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
          <div className="h-5 w-16 bg-[var(--color-gray-200)] rounded-full ml-auto" />
        </div>
      ))}
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
  onSuccess: () => void;
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
      await employeesApi.invite({ email: email.trim(), role });
      toast.success("Invitation sent successfully");
      setEmail("");
      setRole("employee");
      onSuccess();
      onClose();
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

/* -- Page ---------------------------------------------------------- */

export default function EmployeesPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showInviteModal, setShowInviteModal] = useState(false);

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

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  const filteredEmployees = employees.filter(
    (emp) =>
      emp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.department.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
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
        <AppButton
          variant="primary"
          size="sm"
          onClick={() => setShowInviteModal(true)}
        >
          <Plus className="h-4 w-4 mr-1" />
          Invite Employee
        </AppButton>
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
                  <th className="text-center py-3 px-5 font-medium text-[var(--color-gray-500)]">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.map((emp) => (
                  <tr
                    key={emp.id}
                    className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
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
                    <td className="py-3 px-5 text-center">
                      <StatusBadge status={emp.status} />
                    </td>
                  </tr>
                ))}
                {filteredEmployees.length === 0 && employees.length > 0 && (
                  <tr>
                    <td
                      colSpan={4}
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

      {/* Invite modal */}
      <InviteEmployeeModal
        isOpen={showInviteModal}
        onClose={() => setShowInviteModal(false)}
        onSuccess={fetchEmployees}
      />
    </div>
  );
}
