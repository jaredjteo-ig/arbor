"use client";

import { useState } from "react";
import { AppCard, AppButton } from "@/components/design-system";
import { Users, Plus, Search } from "lucide-react";

/* -- Types --------------------------------------------------------- */

interface Employee {
  id: number;
  name: string;
  email: string;
  department: string;
  status: "active" | "invited" | "inactive";
}

/* -- Placeholder data ---------------------------------------------- */

const PLACEHOLDER_EMPLOYEES: Employee[] = [
  {
    id: 1,
    name: "Sarah Tan",
    email: "sarah.tan@example.com",
    department: "Operations",
    status: "active",
  },
  {
    id: 2,
    name: "Raj Kumar",
    email: "raj.kumar@example.com",
    department: "Engineering",
    status: "active",
  },
  {
    id: 3,
    name: "Li Wei",
    email: "li.wei@example.com",
    department: "Marketing",
    status: "active",
  },
  {
    id: 4,
    name: "Aisha Binte Ahmad",
    email: "aisha.ahmad@example.com",
    department: "Finance",
    status: "invited",
  },
  {
    id: 5,
    name: "John Lee",
    email: "john.lee@example.com",
    department: "Operations",
    status: "inactive",
  },
];

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

/* -- Page ---------------------------------------------------------- */

export default function EmployeesPage() {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredEmployees = PLACEHOLDER_EMPLOYEES.filter(
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
        <AppButton variant="primary" size="sm">
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

      {/* Employee table */}
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
              {filteredEmployees.length === 0 && (
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
    </div>
  );
}
