"use client";

import { useState, useCallback } from "react";
import {
  GraduationCap,
  Search,
  Clock,
  DollarSign,
  Award,
  ExternalLink,
  X,
  CheckCircle,
  Filter,
} from "lucide-react";
import {
  AppCard,
  AppButton,
  LoadingState,
  ErrorState,
  EmptyState,
  toast,
} from "@/components/design-system";
import { useSkillsFutureCourses, useGrantCheck } from "@/hooks/api";
import type { SkillsFutureCourse } from "@/services/api/integrations";
import { AdminGuard } from "@/components/auth/AdminGuard";

/* ── Search Filters ──────────────────────────────────────── */

interface CourseFilters {
  query: string;
  topic: string;
  duration: string;
  funding: string;
}

const TOPIC_OPTIONS = [
  "",
  "Leadership",
  "Data Analytics",
  "Digital Marketing",
  "Project Management",
  "Cybersecurity",
  "Finance",
  "Human Resources",
  "Communication",
];

const DURATION_OPTIONS = ["", "1-day", "2-3 days", "1 week", "2+ weeks"];
const FUNDING_OPTIONS = ["", "sfc-eligible", "grant-eligible"];

function SearchBar({
  filters,
  onChange,
}: {
  filters: CourseFilters;
  onChange: (filters: CourseFilters) => void;
}) {
  const [showFilters, setShowFilters] = useState(false);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-gray-400)]"
            aria-hidden="true"
          />
          <input
            type="search"
            value={filters.query}
            onChange={(e) => onChange({ ...filters, query: e.target.value })}
            placeholder="Search courses by keyword..."
            className="w-full rounded-[8px] border px-3 py-2 pl-10 text-sm min-h-[44px]
              bg-[var(--color-surface-input)] text-[var(--foreground)]
              border-[var(--color-surface-input-border)]
              transition-colors
              focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
              focus:border-[var(--color-surface-input-focus)]"
          />
        </div>
        <AppButton
          variant="outlined"
          size="md"
          onClick={() => setShowFilters(!showFilters)}
        >
          <Filter className="h-4 w-4" aria-hidden="true" />
          Filters
        </AppButton>
      </div>

      {showFilters && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-[8px] bg-[var(--color-gray-50)] border border-[var(--color-gray-200)]">
          <div>
            <label
              htmlFor="topic-filter"
              className="block text-xs font-medium text-[var(--color-gray-500)] mb-1"
            >
              Topic
            </label>
            <select
              id="topic-filter"
              value={filters.topic}
              onChange={(e) => onChange({ ...filters, topic: e.target.value })}
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[36px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            >
              <option value="">All Topics</option>
              {TOPIC_OPTIONS.filter(Boolean).map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label
              htmlFor="duration-filter"
              className="block text-xs font-medium text-[var(--color-gray-500)] mb-1"
            >
              Duration
            </label>
            <select
              id="duration-filter"
              value={filters.duration}
              onChange={(e) =>
                onChange({ ...filters, duration: e.target.value })
              }
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[36px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            >
              <option value="">Any Duration</option>
              {DURATION_OPTIONS.filter(Boolean).map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label
              htmlFor="funding-filter"
              className="block text-xs font-medium text-[var(--color-gray-500)] mb-1"
            >
              Funding
            </label>
            <select
              id="funding-filter"
              value={filters.funding}
              onChange={(e) =>
                onChange({ ...filters, funding: e.target.value })
              }
              className="w-full rounded-[8px] border px-3 py-2 text-sm min-h-[36px]
                bg-[var(--color-surface-input)] text-[var(--foreground)]
                border-[var(--color-surface-input-border)]
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            >
              <option value="">Any Funding</option>
              <option value="sfc-eligible">SFC Eligible</option>
              <option value="grant-eligible">Grant Eligible</option>
            </select>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Course Card ─────────────────────────────────────────── */

function CourseCard({
  course,
  onViewDetail,
}: {
  course: SkillsFutureCourse;
  onViewDetail: () => void;
}) {
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat("en-SG", {
      style: "currency",
      currency: "SGD",
    }).format(amount);

  return (
    <AppCard
      variant="standard"
      className="hover:shadow-[var(--shadow-raised)] transition-shadow"
    >
      <div className="space-y-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)] line-clamp-2">
            {course.title}
          </h3>
          <p className="text-xs text-[var(--color-gray-500)] mt-1">
            {course.provider}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--color-gray-500)]">
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3 w-3" aria-hidden="true" />
            {course.duration}
          </span>
          <span className="inline-flex items-center gap-1">
            <DollarSign className="h-3 w-3" aria-hidden="true" />
            {formatCurrency(course.fee)}
          </span>
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-2">
          {course.grant_eligible && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--color-success-bg)] text-[var(--color-success)]">
              <Award className="h-3 w-3" aria-hidden="true" />
              Grant Eligible
              {course.grant_amount &&
                ` (${formatCurrency(course.grant_amount)})`}
            </span>
          )}
          {course.sfc_eligible && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--color-info-bg)] text-[var(--color-info)]">
              <CheckCircle className="h-3 w-3" aria-hidden="true" />
              SFC Credits
            </span>
          )}
        </div>

        {/* Topics */}
        {(course.topics?.length ?? 0) > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {(course.topics ?? []).slice(0, 3).map((topic) => (
              <span
                key={topic}
                className="px-2 py-0.5 rounded text-xs bg-[var(--color-gray-100)] text-[var(--color-gray-600)]"
              >
                {topic}
              </span>
            ))}
            {(course.topics?.length ?? 0) > 3 && (
              <span className="text-xs text-[var(--color-gray-400)]">
                +{(course.topics?.length ?? 0) - 3} more
              </span>
            )}
          </div>
        )}

        <AppButton variant="outlined" size="sm" onClick={onViewDetail}>
          View Details
        </AppButton>
      </div>
    </AppCard>
  );
}

/* ── Course Detail Modal ─────────────────────────────────── */

function CourseDetailModal({
  course,
  onClose,
}: {
  course: SkillsFutureCourse;
  onClose: () => void;
}) {
  const { data: grantData, isPending: grantLoading } = useGrantCheck(course.id);

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat("en-SG", {
      style: "currency",
      currency: "SGD",
    }).format(amount);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="fixed inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="course-detail-title"
        className="relative bg-[var(--color-surface-card)] rounded-[12px] shadow-[var(--shadow-modal)]
          border border-[var(--color-gray-200)] max-w-2xl w-full max-h-[85vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="sticky top-0 bg-[var(--color-surface-card)] border-b border-[var(--color-gray-200)] px-6 py-4 flex items-start justify-between z-10">
          <div className="flex-1 pr-4">
            <h2
              id="course-detail-title"
              className="text-lg font-semibold text-[var(--color-gray-900)]"
            >
              {course.title}
            </h2>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              {course.provider}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex items-center justify-center rounded-lg p-2 min-h-[36px] min-w-[36px]
              text-[var(--color-gray-500)] hover:bg-[var(--color-gray-100)] transition-colors
              focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            aria-label="Close"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-6">
          {/* Quick info */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg bg-[var(--color-gray-50)] p-3 text-center">
              <p className="text-xs text-[var(--color-gray-500)]">Fee</p>
              <p className="text-sm font-semibold text-[var(--color-gray-900)]">
                {formatCurrency(course.fee)}
              </p>
            </div>
            <div className="rounded-lg bg-[var(--color-gray-50)] p-3 text-center">
              <p className="text-xs text-[var(--color-gray-500)]">Duration</p>
              <p className="text-sm font-semibold text-[var(--color-gray-900)]">
                {course.duration}
              </p>
            </div>
            <div className="rounded-lg bg-[var(--color-gray-50)] p-3 text-center">
              <p className="text-xs text-[var(--color-gray-500)]">Grant</p>
              <p className="text-sm font-semibold text-[var(--color-gray-900)]">
                {course.grant_eligible ? "Yes" : "No"}
              </p>
            </div>
            <div className="rounded-lg bg-[var(--color-gray-50)] p-3 text-center">
              <p className="text-xs text-[var(--color-gray-500)]">SFC</p>
              <p className="text-sm font-semibold text-[var(--color-gray-900)]">
                {course.sfc_eligible ? "Eligible" : "N/A"}
              </p>
            </div>
          </div>

          {/* Description */}
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-2">
              Description
            </h3>
            <p className="text-sm text-[var(--color-gray-600)] whitespace-pre-line">
              {course.description}
            </p>
          </div>

          {/* Schedule */}
          {course.schedule && (
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-2">
                Schedule
              </h3>
              <p className="text-sm text-[var(--color-gray-600)]">
                {course.schedule}
              </p>
            </div>
          )}

          {/* Topics */}
          {(course.topics?.length ?? 0) > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-2">
                Topics Covered
              </h3>
              <div className="flex flex-wrap gap-2">
                {(course.topics ?? []).map((topic) => (
                  <span
                    key={topic}
                    className="px-2.5 py-1 rounded-full text-xs bg-[var(--color-gray-100)] text-[var(--color-gray-600)]"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Grant Check Result */}
          {grantLoading && (
            <div className="rounded-lg bg-[var(--color-gray-50)] p-4 text-center">
              <p className="text-sm text-[var(--color-gray-500)]">
                Checking your grant eligibility...
              </p>
            </div>
          )}
          {grantData && (
            <div
              className={`rounded-lg border p-4 ${
                grantData.eligible
                  ? "bg-[var(--color-success-bg)] border-[var(--color-risk-green-border)]"
                  : "bg-[var(--color-gray-50)] border-[var(--color-gray-200)]"
              }`}
            >
              <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-1">
                Grant Eligibility
              </h3>
              <p className="text-sm text-[var(--color-gray-600)]">
                {grantData.message}
              </p>
              {grantData.eligible && (
                <div className="flex gap-4 mt-2 text-sm">
                  <span>
                    Grant: {formatCurrency(grantData.grant_amount ?? 0)}
                  </span>
                  <span>
                    SFC Balance: {formatCurrency(grantData.sfc_balance ?? 0)}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-[var(--color-surface-card)] border-t border-[var(--color-gray-200)] px-6 py-4 flex items-center justify-between gap-3">
          <AppButton variant="outlined" size="md" onClick={onClose}>
            Close
          </AppButton>
          <div className="flex items-center gap-2">
            {course.sfc_eligible && (
              <AppButton variant="secondary" size="md">
                <Award className="h-4 w-4" aria-hidden="true" />
                Use SFC Credits
              </AppButton>
            )}
            {course.url && (
              <a href={course.url} target="_blank" rel="noopener noreferrer">
                <AppButton variant="primary" size="md">
                  View on SkillsFuture
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                </AppButton>
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function SkillsFutureBrowserPage() {
  const [filters, setFilters] = useState<CourseFilters>({
    query: "",
    topic: "",
    duration: "",
    funding: "",
  });
  const [selectedCourse, setSelectedCourse] =
    useState<SkillsFutureCourse | null>(null);

  const debouncedFilters = filters;
  const { data, isPending, error, refetch } =
    useSkillsFutureCourses(debouncedFilters);

  return (
    <AdminGuard>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <GraduationCap
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              SkillsFuture Courses
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              Browse and enroll in government-supported training programmes for
              your team.
            </p>
          </div>
        </div>

        {/* Search */}
        <SearchBar filters={filters} onChange={setFilters} />

        {/* Content */}
        {isPending && <LoadingState variant="card" count={6} />}

        {error && (
          <ErrorState
            variant="server"
            title="Could not load courses"
            description="We had trouble connecting to the SkillsFuture directory."
            onRetry={() => refetch()}
          />
        )}

        {data && (data.courses?.length ?? 0) === 0 && (
          <EmptyState
            message="No courses found"
            description="Try adjusting your search filters to find relevant courses."
          />
        )}

        {data && (data.courses?.length ?? 0) > 0 && (
          <>
            <p className="text-sm text-[var(--color-gray-500)]">
              {data.total ?? 0} course{(data.total ?? 0) !== 1 ? "s" : ""} found
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {(data.courses ?? []).map((course) => (
                <CourseCard
                  key={course.id}
                  course={course}
                  onViewDetail={() => setSelectedCourse(course)}
                />
              ))}
            </div>
          </>
        )}

        {/* Detail Modal */}
        {selectedCourse && (
          <CourseDetailModal
            course={selectedCourse}
            onClose={() => setSelectedCourse(null)}
          />
        )}
      </div>
    </AdminGuard>
  );
}
