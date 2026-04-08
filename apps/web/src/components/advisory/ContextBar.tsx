"use client";

import { useState } from "react";
import clsx from "clsx";
import { Building2, ChevronDown, ChevronUp, Users } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useCompanyProfile } from "@/hooks/api/useProfile";

interface ContextBarProps {
  className?: string;
}

export function ContextBar({ className }: ContextBarProps) {
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "hr_manager";
  const companyId = isAdmin ? (user?.company_id ?? 0) : 0;
  const { data: profile } = useCompanyProfile(companyId);
  const [expanded, setExpanded] = useState(false);

  // Employees don't need the company profile context bar
  if (!isAdmin || !profile) return null;

  return (
    <div
      className={clsx(
        "border-b border-[var(--color-gray-200)] bg-[var(--color-surface-card)]",
        className,
      )}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-[var(--color-gray-50)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-[var(--color-primary)]" />
          <span className="text-sm font-medium text-[var(--color-gray-900)]">
            {profile.name}
          </span>
          <span className="text-xs text-[var(--color-gray-500)]">
            {profile.sector}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-[var(--color-gray-400)]" />
        ) : (
          <ChevronDown className="h-4 w-4 text-[var(--color-gray-400)]" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-3 grid grid-cols-2 gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-[var(--color-gray-600)]">
            <Users className="h-3.5 w-3.5" />
            <span>{profile.total_headcount} employees</span>
          </div>
          <div className="text-[var(--color-gray-600)]">UEN: {profile.uen}</div>
        </div>
      )}
    </div>
  );
}
