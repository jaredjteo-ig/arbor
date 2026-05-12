"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

/**
 * AdminGuard — redirects employees away from admin-only pages.
 *
 * Usage: wrap the page content in <AdminGuard>...</AdminGuard>.
 * Owners and HR managers pass through. Employees hitting an admin page
 * (via bookmark, deep link, stale URL, or manual navigation) are silently
 * redirected to /my-dashboard — they shouldn't see a red error page when
 * they're just trying to use their own tool. The redirect uses
 * router.replace so the admin URL doesn't sit in browser history.
 */
export function AdminGuard({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user?.role === "employee") {
      router.replace("/my-dashboard");
    }
  }, [isLoading, user, router]);

  /* While auth is resolving OR while the redirect is in flight, render
     nothing. ProtectedRoute handles the loading spinner; employees should
     not see admin content flash before the redirect. */
  if (isLoading || !user || user.role === "employee") {
    return null;
  }

  return <>{children}</>;
}
