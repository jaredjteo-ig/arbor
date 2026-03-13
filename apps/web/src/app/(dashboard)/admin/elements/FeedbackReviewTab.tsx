"use client";

import { useState } from "react";
import { AppButton, AppCard, AppInput } from "@/components/design-system";
import { ThumbsDown, ThumbsUp, AlertCircle } from "lucide-react";
import { useAdminFeedbackSummary } from "@/hooks/api/useAdmin";

/* ── Category badge ───────────────────────────────────────── */

type FeedbackCategory = "inaccurate" | "incomplete" | "unclear" | "other";

const CATEGORY_STYLES: Record<FeedbackCategory, string> = {
  inaccurate: "bg-red-50 text-red-700 border-red-200",
  incomplete: "bg-amber-50 text-amber-700 border-amber-200",
  unclear: "bg-blue-50 text-blue-700 border-blue-200",
  other:
    "bg-[var(--color-gray-100)] text-[var(--color-gray-700)] border-[var(--color-gray-300)]",
};

const CATEGORY_LABELS: Record<FeedbackCategory, string> = {
  inaccurate: "Inaccurate",
  incomplete: "Incomplete",
  unclear: "Unclear",
  other: "Other",
};

function CategoryBadge({ category }: { category: string }) {
  const cat = (category ?? "other") as FeedbackCategory;
  const style = CATEGORY_STYLES[cat] ?? CATEGORY_STYLES.other;
  const label = CATEGORY_LABELS[cat] ?? category;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${style}`}
    >
      {label}
    </span>
  );
}

/* ── Loading skeleton ─────────────────────────────────────── */

function TableSkeleton() {
  return (
    <AppCard variant="flat" className="overflow-hidden">
      <div className="animate-pulse space-y-4 py-4 px-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center gap-4">
            <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
            <div className="h-4 flex-1 bg-[var(--color-gray-200)] rounded" />
            <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded" />
            <div className="h-6 w-20 bg-[var(--color-gray-200)] rounded-full" />
          </div>
        ))}
      </div>
    </AppCard>
  );
}

/* ── Feedback Review Tab ──────────────────────────────────── */

export function FeedbackReviewTab() {
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const { data: summary, isLoading, error } = useAdminFeedbackSummary();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="animate-pulse h-5 w-40 bg-[var(--color-gray-200)] rounded" />
        <TableSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <AppCard
        variant="flat"
        className="border-l-4 border-l-[var(--color-risk-red)]"
      >
        <div className="flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-[var(--color-risk-red)]" />
          <div>
            <p className="text-sm font-medium text-[var(--color-gray-900)]">
              Failed to load feedback data
            </p>
            <p className="text-xs text-[var(--color-gray-500)]">
              {error.message}
            </p>
          </div>
        </div>
      </AppCard>
    );
  }

  if (!summary) return null;

  const recentItems = summary.recent ?? [];
  const filtered =
    categoryFilter === "all"
      ? recentItems
      : recentItems.filter((item) => item.category === categoryFilter);

  // Build category options from the breakdown
  const categoryOptions = [
    { value: "all", label: "All categories" },
    ...Object.entries(summary.category_breakdown ?? {}).map(([key, count]) => ({
      value: key,
      label: `${CATEGORY_LABELS[key as FeedbackCategory] ?? key} (${count})`,
    })),
  ];

  return (
    <div className="space-y-4">
      {/* Header with summary stats */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Feedback Review
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
            {summary.negative_count} negative, {summary.positive_count} positive
            of {summary.total_feedback} total (
            {Math.round(summary.positive_rate * 100)}% positive rate)
          </p>
        </div>
        <div className="w-48">
          <AppInput
            variant="select"
            value={categoryFilter}
            onChange={(e) =>
              setCategoryFilter((e.target as HTMLSelectElement).value)
            }
            options={categoryOptions}
          />
        </div>
      </div>

      {/* Category breakdown cards */}
      {Object.keys(summary.category_breakdown ?? {}).length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Object.entries(summary.category_breakdown).map(
            ([category, count]) => (
              <AppCard key={category} variant="flat">
                <div className="flex items-center justify-between">
                  <CategoryBadge category={category} />
                  <span className="text-lg font-bold text-[var(--color-gray-900)]">
                    {count}
                  </span>
                </div>
              </AppCard>
            ),
          )}
        </div>
      )}

      {/* Recent feedback table */}
      <AppCard variant="flat" className="overflow-hidden">
        <div className="overflow-x-auto -mx-5 -my-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-gray-100)]">
                <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                  Date
                </th>
                <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                  Query
                </th>
                <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                  Type
                </th>
                <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                  Category
                </th>
                <th className="text-left px-4 py-3 font-medium text-[var(--color-gray-700)]">
                  Domains
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr
                  key={item.feedback_id}
                  className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                >
                  <td className="px-4 py-3 text-[var(--color-gray-500)] whitespace-nowrap">
                    {new Date(item.recorded_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-[var(--color-gray-900)] max-w-xs truncate">
                    {item.query_snippet || "N/A"}
                  </td>
                  <td className="px-4 py-3">
                    {item.is_positive ? (
                      <span className="inline-flex items-center gap-1 text-[var(--color-risk-green)]">
                        <ThumbsUp className="h-3.5 w-3.5" />
                        <span className="text-xs">Positive</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[var(--color-risk-red)]">
                        <ThumbsDown className="h-3.5 w-3.5" />
                        <span className="text-xs">Negative</span>
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {item.category ? (
                      <CategoryBadge category={item.category} />
                    ) : (
                      <span className="text-xs text-[var(--color-gray-400)]">
                        --
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-[var(--color-gray-600)]">
                    {item.domains.length > 0 ? item.domains.join(", ") : "--"}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-sm text-[var(--color-gray-500)]"
                  >
                    No feedback items match the selected filter.
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
