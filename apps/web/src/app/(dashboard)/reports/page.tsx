"use client";

import { useState } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  toast,
} from "@/components/design-system";
import {
  BarChart3,
  Users,
  Wallet,
  CalendarDays,
  Clock,
  Receipt,
  FolderKanban,
  ArrowLeft,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { reportsApi } from "@/services/api/reports";

/* ── Report definitions ───────────────────────────────────── */

interface ReportDef {
  id: string;
  title: string;
  description: string;
  icon: typeof BarChart3;
  color: string;
  bgColor: string;
  category: "workforce" | "financial" | "operational";
}

const REPORTS: ReportDef[] = [
  {
    id: "employees",
    title: "Employees",
    description: "Active and inactive employee details",
    icon: Users,
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    category: "workforce",
  },
  /* Turnover report disabled — no backend endpoint yet
  {
    id: "turnover",
    title: "Turnover Analysis",
    description: "Monthly hires, terminations, and turnover rates",
    icon: TrendingUp,
    color: "text-violet-600",
    bgColor: "bg-violet-50",
    category: "workforce",
  },
  */
  {
    id: "payroll",
    title: "Payroll Summary",
    description: "Gross, net, CPF, and SDL totals by period",
    icon: Wallet,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    category: "financial",
  },
  {
    id: "claims",
    title: "Claims Summary",
    description: "Claims by category with amounts and approval status",
    icon: Receipt,
    color: "text-orange-600",
    bgColor: "bg-orange-50",
    category: "financial",
  },
  {
    id: "projects",
    title: "Project Costs",
    description: "Budget vs actual cost analysis per project",
    icon: FolderKanban,
    color: "text-sky-600",
    bgColor: "bg-sky-50",
    category: "financial",
  },
  {
    id: "leave",
    title: "Leave Utilisation",
    description: "Leave applications and balances by type",
    icon: CalendarDays,
    color: "text-teal-600",
    bgColor: "bg-teal-50",
    category: "operational",
  },
  {
    id: "attendance",
    title: "Attendance",
    description: "Present, absent, late, and overtime by employee",
    icon: Clock,
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    category: "operational",
  },
];

const CATEGORIES = [
  { key: "workforce", label: "Workforce" },
  { key: "financial", label: "Financial" },
  { key: "operational", label: "Operational" },
];

/* ── Loading skeleton ─────────────────────────────────────── */

function TableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 5 }, (_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 px-5 border-b border-[var(--color-gray-100)] last:border-0"
        >
          <div className="h-4 w-28 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-20 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-24 bg-[var(--color-gray-200)] rounded" />
          <div className="h-4 w-16 bg-[var(--color-gray-200)] rounded ml-auto" />
        </div>
      ))}
    </div>
  );
}

/* ── Report Viewer ────────────────────────────────────────── */

function ReportViewer({
  report,
  onBack,
}: {
  report: ReportDef;
  onBack: () => void;
}) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [department, setDepartment] = useState("");
  const [data, setData] = useState<Record<string, unknown>[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const Icon = report.icon;

  async function handleGenerate() {
    setIsLoading(true);
    try {
      /* Map generic filter names to backend-specific query params.
         - payroll: period_start / period_end (required)
         - attendance: date_from / date_to (required)
         - leave/claims: year / status (optional, no date range)
         - employees/projects: no date range params */
      const params: Record<string, string> = {};
      if (report.id === "payroll") {
        if (startDate) params.period_start = startDate;
        if (endDate) params.period_end = endDate;
      } else if (report.id === "attendance") {
        if (startDate) params.date_from = startDate;
        if (endDate) params.date_to = endDate;
      } else {
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;
      }
      if (department) params.department = department;

      /* The backend returns domain-specific shapes. We extract the
         relevant array from each response for the generic table. */
      const apiMethodMap: Record<
        string,
        (p?: Record<string, string>) => Promise<unknown>
      > = {
        employees: reportsApi.employees,
        payroll: reportsApi.payrollSummary,
        leave: reportsApi.leaveUtilization,
        attendance: reportsApi.attendance,
        claims: reportsApi.claimsSummary,
        projects: reportsApi.projectCosts,
      };

      /* Keys in the response that contain the data array */
      const dataKeyMap: Record<string, string> = {
        employees: "employees",
        payroll: "runs",
        leave: "applications",
        attendance: "records",
        claims: "claims",
        projects: "projects",
      };

      const apiFn = apiMethodMap[report.id];
      if (apiFn) {
        const result = (await apiFn(params)) as Record<string, unknown>;
        const key = dataKeyMap[report.id] ?? "rows";
        const rows = result[key];
        setData(Array.isArray(rows) ? (rows as Record<string, unknown>[]) : []);
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to generate report";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <AppButton variant="outlined" size="sm" onClick={onBack}>
        <ArrowLeft className="h-4 w-4 mr-1" /> Back to Reports
      </AppButton>

      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${report.bgColor}`}>
          <Icon className={`h-6 w-6 ${report.color}`} />
        </div>
        <div>
          <h2 className="text-xl font-bold text-[var(--color-gray-900)]">
            {report.title}
          </h2>
          <p className="text-sm text-[var(--color-gray-500)]">
            {report.description}
          </p>
        </div>
      </div>

      {/* Filters */}
      <AppCard variant="flat">
        <div className="flex gap-3 flex-wrap items-end">
          <div className="flex-1 min-w-[150px]">
            <AppInput
              label="Start Date"
              variant="date"
              value={startDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setStartDate(e.target.value)
              }
            />
          </div>
          <div className="flex-1 min-w-[150px]">
            <AppInput
              label="End Date"
              variant="date"
              value={endDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setEndDate(e.target.value)
              }
            />
          </div>
          <div className="flex-1 min-w-[150px]">
            <AppInput
              label="Department"
              value={department}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setDepartment(e.target.value)
              }
              placeholder="Filter by department"
            />
          </div>
          <AppButton
            variant="primary"
            size="sm"
            onClick={handleGenerate}
            loading={isLoading}
          >
            Generate
          </AppButton>
        </div>
      </AppCard>

      {/* Results */}
      {isLoading ? (
        <AppCard variant="standard">
          <div className="-mx-5 -my-4">
            <TableSkeleton />
          </div>
        </AppCard>
      ) : data === null ? (
        <AppCard variant="standard">
          <div className="py-12 text-center">
            <Icon className="h-10 w-10 text-[var(--color-gray-300)] mx-auto mb-3" />
            <p className="text-sm text-[var(--color-gray-500)]">
              Set your filters and click Generate to view the report.
            </p>
          </div>
        </AppCard>
      ) : data.length === 0 ? (
        <AppCard variant="standard">
          <div className="py-8 text-center">
            <p className="text-sm text-[var(--color-gray-500)]">
              No data found for the selected filters.
            </p>
          </div>
        </AppCard>
      ) : (
        <AppCard variant="standard">
          <div className="overflow-x-auto -mx-5 -my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-gray-200)]">
                  {Object.keys(data[0]).map((key) => (
                    <th
                      key={key}
                      className="text-left py-3 px-4 font-medium text-[var(--color-gray-500)]"
                    >
                      {key
                        .replace(/_/g, " ")
                        .replace(/\b\w/g, (c) => c.toUpperCase())}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((row, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors"
                  >
                    {Object.values(row).map((val, colIdx) => (
                      <td
                        key={colIdx}
                        className="py-3 px-4 text-[var(--color-gray-700)]"
                      >
                        {typeof val === "number"
                          ? val % 1 === 0
                            ? val.toLocaleString("en-SG")
                            : val.toLocaleString("en-SG", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })
                          : String(val ?? "-")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AppCard>
      )}
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function ReportsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "hr_manager";
  const [selectedReport, setSelectedReport] = useState<ReportDef | null>(null);

  if (selectedReport) {
    return (
      <div className="max-w-5xl mx-auto space-y-6 pb-8">
        <ReportViewer
          report={selectedReport}
          onBack={() => setSelectedReport(null)}
        />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BarChart3
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Reports
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Workforce insights, financial summaries, and compliance checks
          </p>
        </div>
      </div>

      {/* Report categories */}
      {CATEGORIES.map((cat) => {
        const catReports = REPORTS.filter((r) => r.category === cat.key);
        if (catReports.length === 0) return null;
        return (
          <div key={cat.key}>
            <h2 className="text-sm font-semibold text-[var(--color-gray-500)] uppercase tracking-wider mb-3">
              {cat.label}
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {catReports.map((report) => {
                const Icon = report.icon;
                return (
                  <button
                    key={report.id}
                    type="button"
                    onClick={() => setSelectedReport(report)}
                    className="text-left rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-5 hover:border-[var(--color-primary)] hover:shadow-sm transition-all group"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <div
                        className={`p-2 rounded-lg ${report.bgColor} group-hover:scale-105 transition-transform`}
                      >
                        <Icon className={`h-5 w-5 ${report.color}`} />
                      </div>
                      <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
                        {report.title}
                      </h3>
                    </div>
                    <p className="text-xs text-[var(--color-gray-500)]">
                      {report.description}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
