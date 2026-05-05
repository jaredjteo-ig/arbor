"use client";

/* P1-6 (obayashi): cross-stage activity feed (last 14 days, capped 20).
   Sourced from EmploymentEvent + InterviewSchedule + OnboardingStepProgress
   + Appraisal in the strategy router.
*/

import {
  Calendar,
  UserPlus,
  CheckCircle2,
  TrendingUp,
  DoorOpen,
  Award,
  GraduationCap,
  type LucideIcon,
} from "lucide-react";
import type { ActivityRow } from "@/services/api/strategy";

const STAGE_ICON: Record<string, LucideIcon> = {
  strategy: Calendar,
  attract: UserPlus,
  recruit: UserPlus,
  onboard: CheckCircle2,
  lnd: GraduationCap,
  reward: Award,
  progression: TrendingUp,
  retain: DoorOpen,
};

function formatTime(ts: string | null): string {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return ts;
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.round(diffMs / 60000);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.round(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDay = Math.round(diffHr / 24);
    if (diffDay < 14) return `${diffDay}d ago`;
    return d.toLocaleDateString("en-SG", {
      day: "numeric",
      month: "short",
    });
  } catch {
    return ts;
  }
}

interface Props {
  activity: ActivityRow[];
}

export function ActivityFeed({ activity }: Props) {
  return (
    <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 sm:p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Calendar
          className="h-4 w-4 text-[var(--color-gray-500)]"
          aria-hidden="true"
        />
        <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
          Recent activity
        </h2>
        <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-400)]">
          Last 14 days
        </span>
      </div>

      {activity.length === 0 ? (
        <p className="text-xs text-[var(--color-gray-500)] text-center py-4">
          No activity yet. Hire your first employee or schedule an interview to
          see events here.
        </p>
      ) : (
        <ul className="space-y-3">
          {activity.map((row, idx) => {
            const Icon = STAGE_ICON[row.stage] ?? Calendar;
            return (
              <li
                key={`${row.ts}-${idx}`}
                className="flex items-start gap-3 text-xs"
              >
                <Icon
                  className="h-3.5 w-3.5 mt-0.5 text-[var(--color-gray-400)] shrink-0"
                  aria-hidden="true"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-[var(--color-gray-700)] truncate">
                    {row.summary}
                  </p>
                  <p className="text-[10px] text-[var(--color-gray-400)] mt-0.5">
                    {formatTime(row.ts)} · {row.stage}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
