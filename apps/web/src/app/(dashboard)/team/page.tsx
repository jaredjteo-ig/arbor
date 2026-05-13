"use client";

/* ── /team — Line-manager dashboard ──────────────────────────
 *
 * Surface for any authenticated user with ≥1 direct report
 * (derived from Employee.reporting_manager_id). The sidebar
 * surfaces the entry conditionally; this page renders 4 cards:
 *
 *  1. Pending approvals  — leave + claims + timesheets counts
 *  2. On leave today      — direct reports out, with return date
 *  3. Upcoming leave      — next 14 days, capacity planning
 *  4. Team members        — flat roster
 *
 * Empty-state (team_size === 0) renders a benign "You don't have
 * any direct reports" panel rather than 404 — handles the case
 * where the sidebar caches a stale team_size or HR rearranges
 * the org chart mid-session.
 *
 * Origin: workspaces/obayashi/04-validate/09-redteam-roles-2026-05-12.md
 * finding P1-A. P4-MG-3 in todos/active/P4-MG-manager-role.md.
 */

import Link from "next/link";
import {
  Users,
  CalendarCheck,
  CalendarClock,
  Inbox,
  ArrowRight,
  Receipt,
  Timer,
  CalendarDays,
} from "lucide-react";
import { useTeamDashboard } from "@/hooks/api";
import { AppCard } from "@/components/design-system";

function formatDate(iso: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-SG", {
      day: "numeric",
      month: "short",
    });
  } catch {
    return iso;
  }
}

/* ── Loading skeleton ────────────────────────────────────── */

function TeamSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 bg-[var(--color-gray-200)] rounded animate-pulse" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-32 bg-[var(--color-gray-100)] rounded-2xl animate-pulse"
          />
        ))}
      </div>
      <div className="h-64 bg-[var(--color-gray-100)] rounded-2xl animate-pulse" />
    </div>
  );
}

/* ── Empty state ─────────────────────────────────────────── */

function NoTeamPanel() {
  return (
    <div className="max-w-md mx-auto py-16 text-center">
      <Users className="mx-auto h-10 w-10 text-[var(--color-gray-400)]" />
      <h1 className="mt-4 text-xl font-semibold text-[var(--color-gray-900)]">
        No direct reports
      </h1>
      <p className="mt-2 text-sm text-[var(--color-gray-500)]">
        This page appears for managers with at least one direct report. If
        you’ve recently been assigned a team, please check back after
        refreshing.
      </p>
      <Link
        href="/my-dashboard"
        className="inline-block mt-6 text-sm font-medium text-[var(--color-primary)] hover:underline"
      >
        Return to My Dashboard
      </Link>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────── */

export default function TeamPage() {
  const { data, isLoading, error } = useTeamDashboard();

  if (isLoading) return <TeamSkeleton />;
  if (error) {
    return (
      <div className="max-w-md mx-auto py-16 text-center">
        <p className="text-sm text-red-600">
          Couldn’t load your team data. Try again.
        </p>
      </div>
    );
  }
  if (!data || data.team_size === 0) return <NoTeamPanel />;

  const { pending_approvals, on_leave_today, upcoming_leave, team_members } =
    data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
          Your team
        </h1>
        <p className="text-sm text-[var(--color-gray-500)] mt-1">
          {data.team_size}{" "}
          {data.team_size === 1 ? "direct report" : "direct reports"}.
          Approvals, leave coverage and your team roster.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Pending approvals */}
        <AppCard variant="standard">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center shrink-0">
              <Inbox className="h-5 w-5 text-amber-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
                Pending approvals
              </p>
              <p className="text-3xl font-bold text-[var(--color-gray-900)] mt-1 leading-none">
                {pending_approvals.total}
              </p>
              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--color-gray-500)]">
                <span className="inline-flex items-center gap-1">
                  <CalendarDays className="h-3 w-3" />
                  {pending_approvals.leave} leave
                </span>
                <span className="inline-flex items-center gap-1">
                  <Receipt className="h-3 w-3" />
                  {pending_approvals.claims} claims
                </span>
                <span className="inline-flex items-center gap-1">
                  <Timer className="h-3 w-3" />
                  {pending_approvals.timesheets} timesheets
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <Link
                  href="/leave"
                  className="text-[var(--color-primary)] font-medium hover:underline"
                >
                  Review leave →
                </Link>
                <Link
                  href="/claims"
                  className="text-[var(--color-primary)] font-medium hover:underline"
                >
                  Review claims →
                </Link>
              </div>
            </div>
          </div>
        </AppCard>

        {/* On leave today */}
        <AppCard variant="standard">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
              <CalendarCheck className="h-5 w-5 text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
                On leave today
              </p>
              <p className="text-3xl font-bold text-[var(--color-gray-900)] mt-1 leading-none">
                {on_leave_today.length}
              </p>
              {on_leave_today.length === 0 ? (
                <p className="text-xs text-[var(--color-gray-500)] mt-3">
                  Everyone on the team is at work today.
                </p>
              ) : (
                <ul className="mt-3 space-y-1.5 text-xs text-[var(--color-gray-700)]">
                  {on_leave_today.slice(0, 4).map((entry) => (
                    <li
                      key={`${entry.employee_id}-${entry.start_date}`}
                      className="flex items-center justify-between gap-2"
                    >
                      <span className="font-medium">{entry.employee_name}</span>
                      <span className="text-[var(--color-gray-500)]">
                        back {formatDate(entry.return_date)}
                      </span>
                    </li>
                  ))}
                  {on_leave_today.length > 4 && (
                    <li className="text-[var(--color-gray-500)]">
                      …and {on_leave_today.length - 4} more
                    </li>
                  )}
                </ul>
              )}
            </div>
          </div>
        </AppCard>

        {/* Upcoming leave (next 14d) */}
        <AppCard variant="standard">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-violet-50 flex items-center justify-center shrink-0">
              <CalendarClock className="h-5 w-5 text-violet-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wider">
                Upcoming (14 days)
              </p>
              <p className="text-3xl font-bold text-[var(--color-gray-900)] mt-1 leading-none">
                {upcoming_leave.length}
              </p>
              {upcoming_leave.length === 0 ? (
                <p className="text-xs text-[var(--color-gray-500)] mt-3">
                  No approved leave coming up.
                </p>
              ) : (
                <ul className="mt-3 space-y-1.5 text-xs text-[var(--color-gray-700)]">
                  {upcoming_leave.slice(0, 4).map((entry) => (
                    <li
                      key={`${entry.employee_id}-${entry.start_date}`}
                      className="flex items-center justify-between gap-2"
                    >
                      <span className="font-medium">{entry.employee_name}</span>
                      <span className="text-[var(--color-gray-500)]">
                        {formatDate(entry.start_date)} –{" "}
                        {formatDate(entry.end_date)}
                      </span>
                    </li>
                  ))}
                  {upcoming_leave.length > 4 && (
                    <li className="text-[var(--color-gray-500)]">
                      …and {upcoming_leave.length - 4} more
                    </li>
                  )}
                </ul>
              )}
            </div>
          </div>
        </AppCard>
      </div>

      {/* Team roster */}
      <AppCard variant="standard">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
              Direct reports
            </h2>
            <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
              {team_members.length}{" "}
              {team_members.length === 1 ? "person" : "people"}
            </p>
          </div>
          <Link
            href="/employees"
            className="text-xs font-medium text-[var(--color-primary)] hover:underline inline-flex items-center gap-1"
          >
            All employees
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-gray-200)] text-left">
                <th className="py-2 px-3 font-medium text-[var(--color-gray-500)] text-xs uppercase tracking-wider">
                  Name
                </th>
                <th className="py-2 px-3 font-medium text-[var(--color-gray-500)] text-xs uppercase tracking-wider">
                  Designation
                </th>
                <th className="py-2 px-3 font-medium text-[var(--color-gray-500)] text-xs uppercase tracking-wider">
                  Department
                </th>
                <th className="py-2 px-3 font-medium text-[var(--color-gray-500)] text-xs uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {team_members.map((member) => (
                <tr
                  key={member.id}
                  className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)]"
                >
                  <td className="py-3 px-3">
                    <div className="font-medium text-[var(--color-gray-900)]">
                      {member.name || "—"}
                    </div>
                    <div className="text-xs text-[var(--color-gray-500)]">
                      {member.email}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-700)]">
                    {member.designation || "—"}
                  </td>
                  <td className="py-3 px-3 text-[var(--color-gray-700)]">
                    {member.department || "—"}
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={
                        member.confirmation_status === "confirmed"
                          ? "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700"
                          : member.confirmation_status === "on_probation"
                            ? "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700"
                            : "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--color-gray-100)] text-[var(--color-gray-700)]"
                      }
                    >
                      {member.confirmation_status === "confirmed"
                        ? "Confirmed"
                        : member.confirmation_status === "on_probation"
                          ? "On probation"
                          : member.confirmation_status || "—"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AppCard>
    </div>
  );
}
