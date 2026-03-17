"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { ManagementShowcase } from "@/components/management/ManagementShowcase";

interface CompanySetupGuardProps {
  children: ReactNode;
}

/**
 * Wraps management pages that require a company.
 * If the user has no company_id, shows the feature showcase with setup CTA
 * instead of a raw 403 error.
 */
export function CompanySetupGuard({ children }: CompanySetupGuardProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user?.company_id) {
    return (
      <div className="p-6">
        <ManagementShowcase hasCompany={false} />
      </div>
    );
  }

  return <>{children}</>;
}
