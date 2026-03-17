"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { AppCard } from "@/components/design-system";
import { apiClient } from "@/services/api/client";
import {
  Briefcase,
  CalendarDays,
  FileText,
  Palmtree,
  Thermometer,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";

/* -- Types --------------------------------------------------------- */

interface EmployeeDetails {
  id: number;
  name: string;
  email: string;
  department: string;
  job_title: string;
  start_date: string;
  employment_type: string;
}

/* -- Loading skeleton ---------------------------------------------- */

function CardSkeleton() {
  return (
    <AppCard variant="flat">
      <div className="animate-pulse space-y-3">
        <div className="h-3 w-24 bg-[var(--color-gray-200)] rounded" />
        <div className="h-5 w-32 bg-[var(--color-gray-200)] rounded" />
        <div className="h-3 w-40 bg-[var(--color-gray-100)] rounded" />
        <div className="h-3 w-36 bg-[var(--color-gray-100)] rounded" />
      </div>
    </AppCard>
  );
}

/* -- Employment Summary Card --------------------------------------- */

function EmploymentSummaryCard({
  employee,
  isLoading,
}: {
  employee: EmployeeDetails | null;
  isLoading: boolean;
}) {
  if (isLoading) return <CardSkeleton />;

  return (
    <AppCard variant="flat">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-[var(--color-primary-bg)] shrink-0">
          <Briefcase className="h-5 w-5 text-[var(--color-primary)]" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider mb-1">
            Employment Summary
          </p>
          <p className="text-base font-semibold text-[var(--color-gray-900)]">
            {employee?.job_title || "Employee"}
          </p>
          <div className="mt-2 space-y-1">
            <p className="text-sm text-[var(--color-gray-600)]">
              <span className="text-[var(--color-gray-500)]">Department:</span>{" "}
              {employee?.department || "Not assigned"}
            </p>
            <p className="text-sm text-[var(--color-gray-600)]">
              <span className="text-[var(--color-gray-500)]">Type:</span>{" "}
              {employee?.employment_type || "Full-time"}
            </p>
            <p className="text-sm text-[var(--color-gray-600)]">
              <span className="text-[var(--color-gray-500)]">Start Date:</span>{" "}
              {employee?.start_date
                ? new Date(employee.start_date).toLocaleDateString("en-SG", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })
                : "Not available"}
            </p>
          </div>
        </div>
      </div>
    </AppCard>
  );
}

/* -- Leave Balance Card -------------------------------------------- */

function LeaveBalanceCard() {
  const leaveData = [
    {
      type: "Annual Leave",
      used: 5,
      total: 14,
      icon: Palmtree,
      color: "text-emerald-600",
    },
    {
      type: "Sick Leave",
      used: 2,
      total: 14,
      icon: Thermometer,
      color: "text-amber-600",
    },
  ];

  return (
    <AppCard variant="flat">
      <div className="flex items-start gap-3 mb-3">
        <div className="p-2 rounded-lg bg-[var(--color-primary-bg)] shrink-0">
          <CalendarDays className="h-5 w-5 text-[var(--color-primary)]" />
        </div>
        <div>
          <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Leave Balance
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {leaveData.map((leave) => {
          const remaining = leave.total - leave.used;
          const percentage = (leave.used / leave.total) * 100;
          const Icon = leave.icon;

          return (
            <div key={leave.type}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Icon className={`h-4 w-4 ${leave.color}`} />
                  <span className="text-sm text-[var(--color-gray-700)]">
                    {leave.type}
                  </span>
                </div>
                <span className="text-sm font-medium text-[var(--color-gray-900)]">
                  {remaining} remaining
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 rounded-full bg-[var(--color-gray-100)] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-[var(--color-primary)] transition-all"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="text-xs text-[var(--color-gray-500)] w-16 text-right">
                  {leave.used}/{leave.total} used
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <Link
        href="/my-leave"
        className="mt-3 flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline"
      >
        View full leave details <ArrowRight className="h-3 w-3" />
      </Link>
    </AppCard>
  );
}

/* -- Company Policies Card ----------------------------------------- */

function CompanyPoliciesCard() {
  const policies = [
    { name: "Leave Policy", href: "/policies" },
    { name: "Flexible Work Arrangements", href: "/policies" },
    { name: "Employee Handbook", href: "/policies" },
  ];

  return (
    <AppCard variant="flat">
      <div className="flex items-start gap-3 mb-3">
        <div className="p-2 rounded-lg bg-[var(--color-primary-bg)] shrink-0">
          <FileText className="h-5 w-5 text-[var(--color-primary)]" />
        </div>
        <div>
          <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Company Policies
          </p>
        </div>
      </div>

      <div className="space-y-1">
        {policies.map((policy) => (
          <Link
            key={policy.name}
            href={policy.href}
            className="flex items-center justify-between p-2 -mx-2 rounded-lg hover:bg-[var(--color-gray-50)] transition-colors group"
          >
            <span className="text-sm text-[var(--color-gray-700)] group-hover:text-[var(--color-primary)]">
              {policy.name}
            </span>
            <ArrowRight className="h-3.5 w-3.5 text-[var(--color-gray-400)] group-hover:text-[var(--color-primary)]" />
          </Link>
        ))}
      </div>

      <Link
        href="/policies"
        className="mt-2 flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline"
      >
        View all policies <ArrowRight className="h-3 w-3" />
      </Link>
    </AppCard>
  );
}

/* -- Page ---------------------------------------------------------- */

export default function MyDashboardPage() {
  const { user } = useAuth();
  const firstName = user?.name?.split(" ")[0] ?? null;

  const [employee, setEmployee] = useState<EmployeeDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchEmployee() {
      try {
        const data = await apiClient.get<EmployeeDetails>("/employees/me");
        if (!cancelled) setEmployee(data);
      } catch {
        // Silently fall back to user context data
        if (!cancelled && user) {
          setEmployee({
            id: user.id,
            name: user.name,
            email: user.email,
            department: "Not assigned",
            job_title: "Employee",
            start_date: "",
            employment_type: "Full-time",
          });
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    fetchEmployee();
    return () => {
      cancelled = true;
    };
  }, [user]);

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Greeting */}
      <div>
        <h1 className="text-heading text-[var(--color-gray-900)]">
          {firstName ? `Welcome, ${firstName}` : "Welcome"}
        </h1>
        <p className="text-body text-[var(--color-gray-500)] mt-1">
          Here&apos;s your personal overview
        </p>
      </div>

      {/* 3-card responsive grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <EmploymentSummaryCard employee={employee} isLoading={isLoading} />
        <LeaveBalanceCard />
        <CompanyPoliciesCard />
      </div>
    </div>
  );
}
