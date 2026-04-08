"use client";

import { useState, useEffect } from "react";
import {
  AppCard,
  AppButton,
  AppInput,
  DatePicker,
  BarChart,
  DonutChart,
  toast,
} from "@/components/design-system";
import { employeesApi, type Employee } from "@/services/api/employees";
import {
  BarChart3,
  Users,
  Wallet,
  CalendarDays,
  Clock,
  Receipt,
  FolderKanban,
  TrendingUp,
  ArrowLeft,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { AdminGuard } from "@/components/auth/AdminGuard";
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
  comingSoon?: boolean;
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
  {
    id: "turnover",
    title: "Turnover Analysis",
    description: "Monthly hires, terminations, and turnover rates",
    icon: TrendingUp,
    color: "text-violet-600",
    bgColor: "bg-violet-50",
    category: "workforce",
    comingSoon: true,
  },
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

/* ── Dashboard Charts (data-driven) ──────────────────────── */

const DEPT_COLORS = [
  "#3b82f6",
  "#8b5cf6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#06b6d4",
  "#ec4899",
  "#84cc16",
  "#f97316",
  "#6366f1",
];

const EMPLOYMENT_TYPE_LABELS: Record<string, string> = {
  full_time: "Full-time",
  part_time: "Part-time",
  contract: "Contract",
  intern: "Intern",
};

const EMPLOYMENT_TYPE_COLORS: Record<string, string> = {
  full_time: "#3b82f6",
  part_time: "#10b981",
  contract: "#f59e0b",
  intern: "#8b5cf6",
};

function ReportsDashboardCharts() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    employeesApi
      .list()
      .then((data) => {
        if (!cancelled) setEmployees(data.employees || []);
      })
      .catch(() => {
        /* Graceful -- charts will show empty state */
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) {
    return (
      <div>
        <h2 className="text-sm font-semibold text-[var(--color-gray-500)] uppercase tracking-wider mb-3">
          Dashboard
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((n) => (
            <AppCard key={n} variant="flat">
              <div className="animate-pulse">
                <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded mb-4" />
                <div className="h-[160px] bg-[var(--color-gray-100)] rounded" />
              </div>
            </AppCard>
          ))}
        </div>
      </div>
    );
  }

  const activeEmployees = employees.filter((e) => e.status !== "inactive");

  /* Headcount by department */
  const deptCounts: Record<string, number> = {};
  for (const e of activeEmployees) {
    const dept = e.department || "Unassigned";
    deptCounts[dept] = (deptCounts[dept] || 0) + 1;
  }
  const deptChartData = Object.entries(deptCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([label, value], i) => ({
      label,
      value,
      color: DEPT_COLORS[i % DEPT_COLORS.length],
    }));

  /* Employment type breakdown */
  const empTypeCounts: Record<string, number> = {};
  for (const e of activeEmployees) {
    const empType = (e.employment_type || "unknown").toLowerCase();
    empTypeCounts[empType] = (empTypeCounts[empType] || 0) + 1;
  }
  const empTypeData = Object.entries(empTypeCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([key, value]) => ({
      label:
        EMPLOYMENT_TYPE_LABELS[key] ||
        key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      value,
      color: EMPLOYMENT_TYPE_COLORS[key] || "#9ca3af",
    }));

  const hasData = activeEmployees.length > 0;

  return (
    <div>
      <h2 className="text-sm font-semibold text-[var(--color-gray-500)] uppercase tracking-wider mb-3">
        Dashboard
      </h2>
      {!hasData ? (
        <AppCard variant="flat">
          <div className="py-8 text-center">
            <BarChart3 className="h-10 w-10 text-[var(--color-gray-300)] mx-auto mb-3" />
            <p className="text-sm text-[var(--color-gray-500)]">
              Add employees to see workforce analytics here.
            </p>
          </div>
        </AppCard>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <AppCard variant="flat">
            <BarChart
              title="Headcount by Department"
              data={deptChartData}
              height={160}
            />
          </AppCard>
          <AppCard variant="flat">
            <DonutChart
              title="Employment Type Breakdown"
              data={empTypeData}
              size={130}
            />
          </AppCard>
          <AppCard variant="flat">
            <div className="py-6 text-center">
              <CalendarDays className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2" />
              <p className="text-xs font-medium text-[var(--color-gray-500)] mb-1">
                Leave Utilisation
              </p>
              <p className="text-xs text-[var(--color-gray-400)]">
                Generate a Leave report to view utilisation data.
              </p>
            </div>
          </AppCard>
          <AppCard variant="flat">
            <div className="py-6 text-center">
              <Wallet className="h-8 w-8 text-[var(--color-gray-300)] mx-auto mb-2" />
              <p className="text-xs font-medium text-[var(--color-gray-500)] mb-1">
                Payroll Cost Trend
              </p>
              <p className="text-xs text-[var(--color-gray-400)]">
                Run a payroll period to see cost trends here.
              </p>
            </div>
          </AppCard>
        </div>
      )}
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
  const [employeeMap, setEmployeeMap] = useState<Record<number, string>>({});
  const Icon = report.icon;

  // Fetch employee name lookup on mount
  useEffect(() => {
    employeesApi
      .list()
      .then((res) => {
        const map: Record<number, string> = {};
        for (const e of res.employees ?? []) {
          if (e.id && e.name) map[e.id] = e.name;
        }
        setEmployeeMap(map);
      })
      .catch(() => {});
  }, []);

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
        turnover: reportsApi.turnover,
        payroll: reportsApi.payrollSummary,
        leave: reportsApi.leaveUtilization,
        attendance: reportsApi.attendance,
        claims: reportsApi.claimsSummary,
        projects: reportsApi.projectCosts,
      };

      /* Keys in the response that contain the data array */
      const dataKeyMap: Record<string, string> = {
        employees: "employees",
        turnover: "rows",
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
        let tableRows = Array.isArray(rows)
          ? (rows as Record<string, unknown>[])
          : [];
        if (
          tableRows.length > 0 &&
          report.id !== "payroll" &&
          report.id !== "projects"
        ) {
          /* Inject employee name from lookup map.
             - "employees" report has `id` as the employee ID
             - other reports have `employee_id` */
          tableRows = tableRows.map((row) => {
            const empId = (
              report.id === "employees" ? row.id : row.employee_id
            ) as number | undefined;
            const empName = empId ? employeeMap[empId] : undefined;
            if (empName) {
              const { id, employee_id, ...rest } = row as Record<
                string,
                unknown
              > & { id?: unknown; employee_id?: unknown };
              return { name: empName, ...rest };
            }
            return row;
          });
          /* Sort alphabetically by name */
          if (tableRows[0]?.name) {
            tableRows = [...tableRows].sort((a, b) =>
              String(a.name ?? "").localeCompare(String(b.name ?? "")),
            );
          }
        }
        setData(tableRows);
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
            <DatePicker
              label="Start Date"
              value={startDate}
              onChange={setStartDate}
            />
          </div>
          <div className="flex-1 min-w-[150px]">
            <DatePicker
              label="End Date"
              value={endDate}
              onChange={setEndDate}
              min={startDate}
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
      <AdminGuard>
        <div className="max-w-5xl mx-auto space-y-6 pb-8">
          <ReportViewer
            report={selectedReport}
            onBack={() => setSelectedReport(null)}
          />
        </div>
      </AdminGuard>
    );
  }

  return (
    <AdminGuard>
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

        {/* Dashboard Charts */}
        <ReportsDashboardCharts />

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
                      onClick={() =>
                        !report.comingSoon && setSelectedReport(report)
                      }
                      disabled={report.comingSoon}
                      className={`text-left rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-5 transition-all group ${
                        report.comingSoon
                          ? "opacity-60 cursor-not-allowed"
                          : "hover:border-[var(--color-primary)] hover:shadow-sm"
                      }`}
                    >
                      <div className="flex items-center gap-3 mb-2">
                        <div
                          className={`p-2 rounded-lg ${report.bgColor} ${!report.comingSoon ? "group-hover:scale-105" : ""} transition-transform`}
                        >
                          <Icon className={`h-5 w-5 ${report.color}`} />
                        </div>
                        <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
                          {report.title}
                        </h3>
                        {report.comingSoon && (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-500)] border border-[var(--color-gray-200)]">
                            Coming Soon
                          </span>
                        )}
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
    </AdminGuard>
  );
}
