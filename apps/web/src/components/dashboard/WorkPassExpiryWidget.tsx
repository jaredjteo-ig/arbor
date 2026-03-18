"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { AppCard, AppButton } from "@/components/design-system";
import { Shield, ArrowRight, User } from "lucide-react";
import { employeesApi, type Employee } from "@/services/api/employees";

/* ── Types ──────────────────────────────────────────────────── */

interface ExpiringPass {
  employee: Employee;
  daysLeft: number;
  passType: string;
  expiryDate: string;
}

/* ── Urgency color ──────────────────────────────────────────── */

function getUrgencyStyle(daysLeft: number): {
  badge: string;
  dot: string;
} {
  if (daysLeft < 0)
    return { badge: "bg-red-100 text-red-700", dot: "bg-red-500" };
  if (daysLeft < 30)
    return { badge: "bg-red-100 text-red-700", dot: "bg-red-500" };
  if (daysLeft < 60)
    return { badge: "bg-amber-100 text-amber-700", dot: "bg-amber-500" };
  return { badge: "bg-emerald-100 text-emerald-700", dot: "bg-emerald-500" };
}

/* ── Skeleton ───────────────────────────────────────────────── */

function WidgetSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="flex items-center gap-3 py-2">
          <div className="h-8 w-8 bg-[var(--color-gray-200)] rounded-full" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3.5 w-32 bg-[var(--color-gray-200)] rounded" />
            <div className="h-3 w-20 bg-[var(--color-gray-100)] rounded" />
          </div>
          <div className="h-5 w-14 bg-[var(--color-gray-200)] rounded-full" />
        </div>
      ))}
    </div>
  );
}

/* ── Widget ─────────────────────────────────────────────────── */

export function WorkPassExpiryWidget() {
  const router = useRouter();
  const [expiringPasses, setExpiringPasses] = useState<ExpiringPass[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { employees } = await employeesApi.list();
      const now = Date.now();
      const results: ExpiringPass[] = [];

      for (const emp of employees) {
        // We need to fetch full detail for work_pass_expiry
        try {
          const detail = await employeesApi.getEmployee(emp.id);
          if (detail.work_pass_expiry) {
            const expiryTime = new Date(detail.work_pass_expiry).getTime();
            const daysLeft = Math.ceil((expiryTime - now) / 86400000);
            if (daysLeft <= 90) {
              results.push({
                employee: emp,
                daysLeft,
                passType: detail.pass_type || "Unknown",
                expiryDate: detail.work_pass_expiry,
              });
            }
          }
        } catch {
          // Skip employees where detail fetch fails
        }
      }

      // Sort by urgency (most urgent first)
      results.sort((a, b) => a.daysLeft - b.daysLeft);
      setExpiringPasses(results);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load employee data.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <AppCard variant="standard">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Work Passes Expiring Soon
          </h3>
          {!isLoading && expiringPasses.length > 0 && (
            <span className="text-xs font-medium text-[var(--color-gray-400)] bg-[var(--color-gray-100)] rounded-full px-2 py-0.5">
              {expiringPasses.length}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => router.push("/employees")}
          className="text-xs text-[var(--color-primary)] hover:underline flex items-center gap-1"
        >
          View All <ArrowRight className="h-3 w-3" />
        </button>
      </div>

      {isLoading ? (
        <WidgetSkeleton />
      ) : error ? (
        <div className="py-4 text-center">
          <p className="text-sm text-[var(--color-error)] mb-2">{error}</p>
          <AppButton variant="outlined" size="sm" onClick={fetchData}>
            Try again
          </AppButton>
        </div>
      ) : expiringPasses.length === 0 ? (
        <div className="py-6 text-center">
          <Shield className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2" />
          <p className="text-sm text-[var(--color-gray-500)]">
            No work passes expiring in the next 90 days.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {expiringPasses.map((item) => {
            const urgency = getUrgencyStyle(item.daysLeft);
            return (
              <button
                key={item.employee.id}
                type="button"
                onClick={() => router.push(`/employees/${item.employee.id}`)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-[var(--color-gray-200)] bg-white hover:border-[var(--color-primary)] transition-colors text-left"
              >
                <div className="w-8 h-8 rounded-full bg-[var(--color-primary-bg)] flex items-center justify-center shrink-0">
                  <User className="h-4 w-4 text-[var(--color-primary)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                    {item.employee.name}
                  </p>
                  <p className="text-xs text-[var(--color-gray-500)]">
                    {item.passType.toUpperCase()} &middot; Expires{" "}
                    {item.expiryDate}
                  </p>
                </div>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${urgency.badge}`}
                >
                  {item.daysLeft < 0
                    ? "Expired"
                    : item.daysLeft === 0
                      ? "Today"
                      : `${item.daysLeft}d left`}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </AppCard>
  );
}
