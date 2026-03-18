"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { AppCard, AppButton } from "@/components/design-system";
import { FileText, AlertTriangle, ArrowRight } from "lucide-react";
import {
  employeesApi,
  type Employee,
  type EmployeeDocument,
} from "@/services/api/employees";

/* ── Types ──────────────────────────────────────────────────── */

interface ExpiringDoc {
  employeeId: number;
  employeeName: string;
  document: EmployeeDocument;
  daysLeft: number;
}

/* ── Urgency color ──────────────────────────────────────────── */

function getUrgencyStyle(daysLeft: number): string {
  if (daysLeft < 0) return "bg-red-100 text-red-700";
  if (daysLeft < 30) return "bg-red-100 text-red-700";
  if (daysLeft < 60) return "bg-amber-100 text-amber-700";
  return "bg-emerald-100 text-emerald-700";
}

/* ── Skeleton ───────────────────────────────────────────────── */

function WidgetSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="flex items-center gap-3 py-2">
          <div className="h-4 w-4 bg-[var(--color-gray-200)] rounded" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3.5 w-40 bg-[var(--color-gray-200)] rounded" />
            <div className="h-3 w-24 bg-[var(--color-gray-100)] rounded" />
          </div>
          <div className="h-5 w-14 bg-[var(--color-gray-200)] rounded-full" />
        </div>
      ))}
    </div>
  );
}

/* ── Widget ─────────────────────────────────────────────────── */

export function ExpiringDocumentsWidget() {
  const router = useRouter();
  const [expiringDocs, setExpiringDocs] = useState<ExpiringDoc[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { employees } = await employeesApi.list();
      const now = Date.now();
      const ninetyDaysMs = 90 * 86400000;
      const results: ExpiringDoc[] = [];

      // Fetch documents for each employee and check for expiring ones
      const docPromises = employees.map(async (emp: Employee) => {
        try {
          const { documents } = await employeesApi.listDocuments(emp.id);
          for (const doc of documents) {
            if (doc.expiry_date) {
              const expiryTime = new Date(doc.expiry_date).getTime();
              const daysLeft = Math.ceil((expiryTime - now) / 86400000);
              if (daysLeft <= 90) {
                results.push({
                  employeeId: emp.id,
                  employeeName: emp.name,
                  document: doc,
                  daysLeft,
                });
              }
            }
          }
        } catch {
          // Skip employees where document fetch fails
        }
      });

      await Promise.all(docPromises);

      // Sort by urgency (most urgent first)
      results.sort((a, b) => a.daysLeft - b.daysLeft);
      setExpiringDocs(results);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Unable to load document data.";
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
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Documents Expiring Soon
          </h3>
          {!isLoading && expiringDocs.length > 0 && (
            <span className="text-xs font-medium text-[var(--color-gray-400)] bg-[var(--color-gray-100)] rounded-full px-2 py-0.5">
              {expiringDocs.length}
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
      ) : expiringDocs.length === 0 ? (
        <div className="py-6 text-center">
          <FileText className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2" />
          <p className="text-sm text-[var(--color-gray-500)]">
            No documents expiring in the next 90 days.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {expiringDocs.slice(0, 5).map((item, idx) => (
            <button
              key={`${item.document.id}-${idx}`}
              type="button"
              onClick={() => router.push(`/employees/${item.employeeId}`)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-[var(--color-gray-200)] bg-white hover:border-[var(--color-primary)] transition-colors text-left"
            >
              <FileText className="h-4 w-4 text-[var(--color-gray-400)] shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                  {item.document.file_name}
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">
                  {item.employeeName} &middot;{" "}
                  {item.document.document_type.replace(/_/g, " ")}
                </p>
              </div>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${getUrgencyStyle(item.daysLeft)}`}
              >
                {item.daysLeft < 0
                  ? "Expired"
                  : item.daysLeft === 0
                    ? "Today"
                    : `${item.daysLeft}d left`}
              </span>
            </button>
          ))}
          {expiringDocs.length > 5 && (
            <p className="text-xs text-[var(--color-gray-500)] text-center pt-1">
              +{expiringDocs.length - 5} more
            </p>
          )}
        </div>
      )}
    </AppCard>
  );
}
