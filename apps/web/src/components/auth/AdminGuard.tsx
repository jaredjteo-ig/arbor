"use client";

import { type ReactNode } from "react";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

/**
 * AdminGuard — blocks employee access to admin-only pages.
 *
 * Usage: wrap the page content in <AdminGuard>...</AdminGuard>.
 * If the current user is an employee, it renders an "Access Denied" screen
 * with a link back to the employee dashboard. Owners and HR managers pass
 * through.
 */
export function AdminGuard({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();

  /* While auth is resolving, show nothing (ProtectedRoute handles the spinner). */
  if (isLoading || !user) {
    return null;
  }

  /* Employees are blocked — all other roles (owner, hr_manager) pass. */
  if (user.role === "employee") {
    return (
      <div className="max-w-lg mx-auto py-16 text-center">
        <ShieldAlert
          className="mx-auto h-12 w-12 text-[var(--color-gray-400)]"
          aria-hidden="true"
        />
        <h1 className="mt-4 text-xl font-semibold text-[var(--color-gray-900)]">
          Access Denied
        </h1>
        <p className="mt-2 text-[var(--color-gray-500)]">
          You do not have permission to view this page. This area is restricted
          to administrators.
        </p>
        <a
          href="/my-dashboard"
          className="inline-block mt-6 text-sm font-medium text-[var(--color-primary)] hover:underline"
        >
          Return to My Dashboard
        </a>
      </div>
    );
  }

  return <>{children}</>;
}
