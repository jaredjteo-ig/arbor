"use client";

/* P1-2 / P1-4 (obayashi): 8-stage card grid + health pills.
   Spec: workspaces/obayashi/02-plans/02-lifecycle-dashboard-spec.md
   - Default: 4×2 card grid at ≥1024px (Option A).
   - Mobile: vertical list at <1024px (Option C).
   - Health pill: dot + word + Lucide icon (NEVER colour-only).
*/

import {
  Lightbulb,
  Magnet,
  UserPlus,
  Briefcase,
  GraduationCap,
  Award,
  TrendingUp,
  DoorOpen,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  type LucideIcon,
} from "lucide-react";
import type {
  LifecycleStageKey,
  StageHealth,
  HealthPill,
} from "@/services/api/strategy";

interface StageMeta {
  number: number;
  key: LifecycleStageKey;
  name: string;
  icon: LucideIcon;
  describe: (kpi: Record<string, unknown>) => string;
}

const STAGES: StageMeta[] = [
  {
    number: 1,
    key: "strategy",
    name: "Strategy",
    icon: Lightbulb,
    describe: (k) => {
      const delta = (k.delta as number) ?? 0;
      const target = (k.target as number) ?? 0;
      if (delta === 0) return `On plan · target ${target}`;
      return delta > 0
        ? `+${delta} vs target ${target}`
        : `${delta} vs target ${target}`;
    },
  },
  {
    number: 2,
    key: "attract",
    name: "Attract",
    icon: Magnet,
    describe: (k) => {
      const a = (k.applies_30d as number) ?? 0;
      const s = (k.sources as number) ?? 0;
      return a === 0 ? "No applies in 30d" : `${a} applies · ${s} sources`;
    },
  },
  {
    number: 3,
    key: "recruit",
    name: "Recruit",
    icon: UserPlus,
    describe: (k) => {
      const j = (k.active_jobs as number) ?? 0;
      const stale = (k.stale as number) ?? 0;
      if (j === 0) return "No open jobs";
      return stale > 0 ? `${j} jobs · ${stale} stale` : `${j} active jobs`;
    },
  },
  {
    number: 4,
    key: "onboard",
    name: "Onboard",
    icon: Briefcase,
    describe: (k) => {
      const c = (k.avg_completion as number) ?? 0;
      const o = (k.overdue as number) ?? 0;
      if ((k.active as number) === 0) return "No active onboarding";
      const pct = `${Math.round(c * 100)}%`;
      return o > 0 ? `${pct} avg · ${o} overdue` : `${pct} avg completion`;
    },
  },
  {
    number: 5,
    key: "lnd",
    name: "Learning",
    icon: GraduationCap,
    describe: (k) => {
      if (k.data_missing) return "No training records yet";
      const h = (k.avg_hours_per_employee as number) ?? 0;
      return `${h.toFixed(1)} hrs/employee/yr`;
    },
  },
  {
    number: 6,
    key: "reward",
    name: "Reward",
    icon: Award,
    describe: (k) => {
      const lp = (k.last_payroll as string) ?? "—";
      const r = (k.recognitions_30d as number) ?? 0;
      return `Payroll ${lp} · ${r} kudos 30d`;
    },
  },
  {
    number: 7,
    key: "progression",
    name: "Progression",
    icon: TrendingUp,
    describe: (k) => {
      const due = (k.due_reviews as number) ?? 0;
      const done = (k.completed as number) ?? 0;
      return `${due} in flight · ${done} signed off`;
    },
  },
  {
    number: 8,
    key: "retain",
    name: "Retain",
    icon: DoorOpen,
    describe: (k) => {
      const c = (k.churn_ytd as number) ?? 0;
      const yoy = (k.yoy_delta_ppt as number) ?? 0;
      const yoyStr =
        yoy === 0
          ? "flat YoY"
          : yoy > 0
            ? `+${yoy.toFixed(1)} ppt YoY`
            : `${yoy.toFixed(1)} ppt YoY`;
      return `${c.toFixed(1)}% churn · ${yoyStr}`;
    },
  },
];

const HEALTH_STYLES: Record<
  HealthPill,
  { bg: string; text: string; dot: string; word: string; Icon: LucideIcon }
> = {
  green: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    dot: "bg-emerald-500",
    word: "Healthy",
    Icon: CheckCircle2,
  },
  amber: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    dot: "bg-amber-500",
    word: "Attention",
    Icon: AlertTriangle,
  },
  red: {
    bg: "bg-red-50",
    text: "text-red-700",
    dot: "bg-red-500",
    word: "Action",
    Icon: AlertOctagon,
  },
};

interface StageGridProps {
  stages: Record<LifecycleStageKey, StageHealth>;
  activeStage: LifecycleStageKey | null;
  onSelect: (stage: LifecycleStageKey) => void;
}

export function StageGrid({ stages, activeStage, onSelect }: StageGridProps) {
  return (
    <div
      className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"
      role="list"
      aria-label="Employee lifecycle stages"
    >
      {STAGES.map((meta) => {
        const stage = stages[meta.key];
        const health = stage?.health ?? "amber";
        const style = HEALTH_STYLES[health];
        const isActive = activeStage === meta.key;
        const HealthIcon = style.Icon;
        const StageIcon = meta.icon;
        return (
          <button
            key={meta.key}
            type="button"
            onClick={() => onSelect(meta.key)}
            className={`group text-left rounded-xl border p-4 sm:p-5 transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] hover:-translate-y-0.5 hover:shadow-md ${
              isActive
                ? "border-[var(--color-primary)] ring-2 ring-[var(--color-primary-100)] bg-white"
                : "border-[var(--color-gray-200)] bg-white"
            }`}
            aria-label={`${meta.name} stage — ${style.word.toLowerCase()}`}
            aria-current={isActive ? "true" : undefined}
            role="listitem"
          >
            <div className="flex items-start justify-between gap-2 mb-3">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-semibold text-[var(--color-gray-400)]">
                  {meta.number.toString().padStart(2, "0")}
                </span>
                <StageIcon
                  className="h-4 w-4 text-[var(--color-gray-500)]"
                  aria-hidden="true"
                />
              </div>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${style.bg} ${style.text}`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${style.dot}`}
                  aria-hidden="true"
                />
                <HealthIcon className="h-3 w-3" aria-hidden="true" />
                {style.word}
              </span>
            </div>
            <h3 className="text-base font-semibold text-[var(--color-gray-900)] mb-1">
              {meta.name}
            </h3>
            <p className="text-xs text-[var(--color-gray-600)] line-clamp-2 min-h-[2rem]">
              {stage ? meta.describe(stage.kpi) : "—"}
            </p>
            <p className="mt-3 text-[11px] font-medium text-[var(--color-primary)] group-hover:underline">
              View {meta.name.toLowerCase()} →
            </p>
          </button>
        );
      })}
    </div>
  );
}

export const STAGE_META = STAGES;
