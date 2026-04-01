"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { AppCard } from "@/components/design-system";
import { apiClient } from "@/services/api/client";
import { employeesApi, type LeaveBalance } from "@/services/api/employees";
import { policiesApi, type PolicyRecord } from "@/services/api/policies";
import {
  Briefcase,
  CalendarDays,
  FileText,
  Palmtree,
  Thermometer,
  ArrowRight,
  Info,
  AlertCircle,
  CheckCircle2,
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

/** Statutory defaults for Singapore Employment Act minimums */
const STATUTORY_LEAVE: LeaveDisplay[] = [
  {
    name: "Annual Leave",
    used: 0,
    total: 7,
    icon: Palmtree,
    color: "text-emerald-600",
  },
  {
    name: "Sick Leave",
    used: 0,
    total: 14,
    icon: Thermometer,
    color: "text-amber-600",
  },
];

interface LeaveDisplay {
  name: string;
  used: number;
  total: number;
  icon: typeof Palmtree;
  color: string;
}

const LEAVE_TYPE_LABELS: Record<string, string> = {
  annual: "Annual Leave",
  sick: "Sick Leave",
  hospitalization: "Hospitalization Leave",
};

const ICON_MAP: Record<string, { icon: typeof Palmtree; color: string }> = {
  annual: { icon: Palmtree, color: "text-emerald-600" },
  sick: { icon: Thermometer, color: "text-amber-600" },
};

const DEFAULT_LEAVE_ICON = { icon: CalendarDays, color: "text-blue-600" };

function mapBalanceToDisplay(balance: LeaveBalance): LeaveDisplay {
  const leaveType = balance.leave_type ?? "";
  const iconInfo = ICON_MAP[leaveType] ?? DEFAULT_LEAVE_ICON;
  const label =
    LEAVE_TYPE_LABELS[leaveType] ??
    leaveType.charAt(0).toUpperCase() + leaveType.slice(1);
  return {
    name: label,
    used: (balance.used_days ?? 0) + (balance.pending_days ?? 0),
    total: balance.entitlement_days ?? 0,
    icon: iconInfo.icon,
    color: iconInfo.color,
  };
}

function LeaveBalanceCard() {
  const [leaveData, setLeaveData] = useState<LeaveDisplay[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isStatutoryFallback, setIsStatutoryFallback] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchLeave() {
      try {
        const data = await employeesApi.leaveBalances();
        if (!cancelled && data.balances && data.balances.length > 0) {
          // Show at most 2 leave types in the dashboard card
          setLeaveData(data.balances.slice(0, 2).map(mapBalanceToDisplay));
          setIsStatutoryFallback(false);
        } else {
          if (!cancelled) {
            setLeaveData(STATUTORY_LEAVE);
            setIsStatutoryFallback(true);
          }
        }
      } catch {
        if (!cancelled) {
          setLeaveData(STATUTORY_LEAVE);
          setIsStatutoryFallback(true);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    fetchLeave();
    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) return <CardSkeleton />;

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
          const percentage =
            leave.total > 0 ? (leave.used / leave.total) * 100 : 0;
          const Icon = leave.icon;

          return (
            <div key={leave.name}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Icon className={`h-4 w-4 ${leave.color}`} />
                  <span className="text-sm text-[var(--color-gray-700)]">
                    {leave.name}
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

      {isStatutoryFallback && (
        <div className="mt-2 flex items-start gap-1.5">
          <Info className="h-3 w-3 text-[var(--color-gray-400)] mt-0.5 shrink-0" />
          <p className="text-[10px] text-[var(--color-gray-500)]">
            Statutory minimums shown. Contact HR for your actual balances.
          </p>
        </div>
      )}

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
  const [pendingPolicies, setPendingPolicies] = useState<PolicyRecord[]>([]);
  const [allPolicies, setAllPolicies] = useState<PolicyRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchPolicies() {
      try {
        const [allData, pendingData] = await Promise.all([
          policiesApi.list(),
          policiesApi.pendingAcknowledgments(),
        ]);

        if (cancelled) return;

        const active = (allData.policies ?? []).filter(
          (p) => p.status === "active",
        );
        setAllPolicies(active);
        setPendingPolicies(pendingData.pending_policies ?? []);
      } catch {
        if (!cancelled) {
          setAllPolicies([]);
          setPendingPolicies([]);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    fetchPolicies();
    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) return <CardSkeleton />;

  const hasPending = pendingPolicies.length > 0;

  return (
    <AppCard variant="flat">
      <div className="flex items-start gap-3 mb-3">
        <div
          className={`p-2 rounded-lg shrink-0 ${
            hasPending ? "bg-amber-50" : "bg-[var(--color-primary-bg)]"
          }`}
        >
          {hasPending ? (
            <AlertCircle className="h-5 w-5 text-amber-500" />
          ) : (
            <FileText className="h-5 w-5 text-[var(--color-primary)]" />
          )}
        </div>
        <div>
          <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
            Company Policies
          </p>
          {hasPending && (
            <p className="text-xs text-amber-600 mt-0.5">
              {pendingPolicies.length} pending acknowledgment
              {pendingPolicies.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>
      </div>

      {/* Pending policies shown first as action items */}
      {hasPending && (
        <div className="space-y-1 mb-2">
          {pendingPolicies.slice(0, 3).map((policy) => (
            <Link
              key={policy.id}
              href={`/policies/${policy.id}`}
              className="flex items-center justify-between p-2 -mx-2 rounded-lg bg-amber-50 hover:bg-amber-100 transition-colors group border border-amber-100"
            >
              <div className="flex items-center gap-2 min-w-0">
                <AlertCircle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                <span className="text-sm text-amber-800 group-hover:text-amber-900 truncate">
                  {policy.title}
                </span>
              </div>
              <span className="text-xs text-amber-600 shrink-0 ml-2">
                Review
              </span>
            </Link>
          ))}
          {pendingPolicies.length > 3 && (
            <Link
              href="/policies#pending-acknowledgments"
              className="flex items-center gap-1 px-2 text-xs text-amber-600 hover:underline"
            >
              +{pendingPolicies.length - 3} more{" "}
              <ArrowRight className="h-3 w-3" />
            </Link>
          )}
        </div>
      )}

      {/* Acknowledged / other active policies */}
      {!hasPending && allPolicies.length > 0 && (
        <div className="space-y-1">
          {allPolicies.slice(0, 3).map((policy) => (
            <Link
              key={policy.id}
              href={`/policies/${policy.id}`}
              className="flex items-center justify-between p-2 -mx-2 rounded-lg hover:bg-[var(--color-gray-50)] transition-colors group"
            >
              <span className="text-sm text-[var(--color-gray-700)] group-hover:text-[var(--color-primary)] truncate">
                {policy.title}
              </span>
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0 ml-2" />
            </Link>
          ))}
        </div>
      )}

      {allPolicies.length === 0 && !hasPending && (
        <p className="text-sm text-[var(--color-gray-500)]">
          No active policies yet
        </p>
      )}

      <Link
        href="/policies"
        className="mt-2 flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline"
      >
        View all policies <ArrowRight className="h-3 w-3" />
      </Link>
    </AppCard>
  );
}

/* -- Pending Acknowledgments Banner -------------------------------- */

function PendingAcknowledgmentsBanner() {
  const [pendingPolicies, setPendingPolicies] = useState<PolicyRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchPending() {
      try {
        const data = await policiesApi.pendingAcknowledgments();
        if (!cancelled) {
          setPendingPolicies(data.pending_policies ?? []);
        }
      } catch {
        if (!cancelled) setPendingPolicies([]);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    fetchPending();
    return () => {
      cancelled = true;
    };
  }, []);

  /* Do not render if still loading or nothing pending */
  if (isLoading || pendingPolicies.length === 0) return null;

  const CATEGORY_LABELS: Record<string, string> = {
    employment_terms: "Employment Terms",
    leave_absence: "Leave & Absence",
    compensation_benefits: "Compensation & Benefits",
    workplace_safety: "Workplace Safety",
    fair_employment: "Fair Employment",
    foreign_worker: "Foreign Worker",
    tax_filing: "Tax Filing",
    general_hr: "General HR",
    code_of_conduct: "Code of Conduct",
  };

  return (
    <AppCard variant="flat">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-amber-50 shrink-0">
          <AlertCircle className="h-5 w-5 text-amber-500" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-[var(--color-gray-900)]">
            You have {pendingPolicies.length} polic
            {pendingPolicies.length === 1 ? "y" : "ies"} to review and
            acknowledge
          </p>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            Please review the following company policies
          </p>

          <div className="mt-3 space-y-2">
            {pendingPolicies.map((policy) => (
              <Link
                key={policy.id}
                href={`/policies/${policy.id}`}
                className="flex items-center justify-between p-2.5 rounded-[8px] border border-amber-100 bg-amber-50 hover:bg-amber-100 transition-colors group"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[var(--color-gray-900)] group-hover:text-amber-900 truncate">
                    {policy.title}
                  </p>
                  <p className="text-xs text-[var(--color-gray-500)]">
                    {CATEGORY_LABELS[policy.category] ?? policy.category}
                  </p>
                </div>
                <span className="flex items-center gap-1 text-xs font-medium text-amber-600 group-hover:text-amber-700 shrink-0 ml-3">
                  Review <ArrowRight className="h-3 w-3" />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </div>
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

      {/* Pending policy acknowledgments nudge */}
      <PendingAcknowledgmentsBanner />

      {/* 3-card responsive grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <EmploymentSummaryCard employee={employee} isLoading={isLoading} />
        <LeaveBalanceCard />
        <CompanyPoliciesCard />
      </div>
    </div>
  );
}
