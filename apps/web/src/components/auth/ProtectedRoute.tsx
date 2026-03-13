"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import type { User } from "@/services/api/auth";

/* ── Types ────────────────────────────────────────────────── */

interface ProtectedRouteProps {
  children: ReactNode;
  /** If provided, only users with one of these roles may access the content */
  requiredRoles?: User["role"][];
}

/* ── Loading Spinner ──────────────────────────────────────── */

function AuthLoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-screen bg-[var(--background)]">
      <div className="flex flex-col items-center gap-4">
        <div
          className="h-10 w-10 animate-spin rounded-full border-4 border-[var(--color-gray-200)] border-t-[var(--color-primary)]"
          role="status"
        >
          <span className="sr-only">Checking authentication...</span>
        </div>
        <p className="text-sm text-[var(--color-gray-500)]">Loading...</p>
      </div>
    </div>
  );
}

/* ── Component ────────────────────────────────────────────── */

export function ProtectedRoute({
  children,
  requiredRoles,
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }

    if (requiredRoles && user && !requiredRoles.includes(user.role)) {
      /* User is authenticated but lacks the required role */
      router.replace("/");
    }
  }, [isAuthenticated, isLoading, user, requiredRoles, router]);

  if (isLoading) {
    return <AuthLoadingSpinner />;
  }

  if (!isAuthenticated) {
    return <AuthLoadingSpinner />;
  }

  if (requiredRoles && user && !requiredRoles.includes(user.role)) {
    return <AuthLoadingSpinner />;
  }

  return <>{children}</>;
}
