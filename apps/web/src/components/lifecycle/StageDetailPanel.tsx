"use client";

/* P1-3 (obayashi): per-stage detail panel.
   8 panels — each surfaces 3 KPIs + a stage-specific micro-viz +
   a row of quick-action deep links into the underlying module.
*/

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type {
  LifecycleStageKey,
  StageHealth,
  LifecycleHero,
} from "@/services/api/strategy";

interface PanelProps {
  stageKey: LifecycleStageKey;
  stage: StageHealth;
  hero: LifecycleHero;
}

interface QuickAction {
  label: string;
  href: string;
}

interface PanelSpec {
  title: string;
  blurb: string;
  kpis: Array<{ label: string; value: string }>;
  actions: QuickAction[];
}

function buildSpec(
  key: LifecycleStageKey,
  stage: StageHealth,
  hero: LifecycleHero,
): PanelSpec {
  const kpi = stage.kpi as Record<string, unknown>;

  switch (key) {
    case "strategy":
      return {
        title: "Strategy",
        blurb:
          "Workforce-plan vs actuals across the 8 lifecycle stages. The plan-authoring hub itself ships in a later release; this card surfaces what's already trackable today.",
        kpis: [
          {
            label: "Headcount actual",
            value: String(kpi.actual ?? hero.headcount_actual),
          },
          {
            label: "Headcount target",
            value: String(kpi.target ?? hero.headcount_target),
          },
          {
            label: "Delta",
            value: ((kpi.delta as number) ?? 0).toString(),
          },
        ],
        actions: [
          { label: "Employees directory", href: "/employees" },
          { label: "Reports", href: "/reports" },
        ],
      };

    case "attract":
      return {
        title: "Attract",
        blurb:
          "Top-of-funnel demand signal. Tracks new applies and how many distinct sources brought them in over the last 30 days.",
        kpis: [
          {
            label: "Applies (30d)",
            value: String(kpi.applies_30d ?? 0),
          },
          {
            label: "Active sources",
            value: String(kpi.sources ?? 0),
          },
          {
            label: "Open jobs",
            value: String(hero.open_jobs ?? 0),
          },
        ],
        actions: [
          { label: "Recruitment dashboard", href: "/recruitment" },
          { label: "Job listings", href: "/recruitment?tab=jobs" },
        ],
      };

    case "recruit":
      return {
        title: "Recruit",
        blurb:
          "In-cycle pipeline health. Stale = an open job that hasn't seen a candidate touch in ≥14 days.",
        kpis: [
          {
            label: "Active jobs",
            value: String(kpi.active_jobs ?? 0),
          },
          {
            label: "Stale jobs",
            value: String(kpi.stale ?? 0),
          },
          {
            label: "Candidates",
            value: String(kpi.candidates ?? 0),
          },
        ],
        actions: [
          { label: "Pipeline kanban", href: "/recruitment?tab=candidates" },
          { label: "Interviews", href: "/recruitment?tab=interviews" },
          { label: "New job", href: "/recruitment?tab=jobs" },
        ],
      };

    case "onboard":
      return {
        title: "Onboard",
        blurb:
          "Active assignments only. Avg completion is across in-progress + overdue rows; reaching 100% closes the assignment automatically.",
        kpis: [
          {
            label: "Active",
            value: String(kpi.active ?? 0),
          },
          {
            label: "Avg completion",
            value: `${Math.round(((kpi.avg_completion as number) ?? 0) * 100)}%`,
          },
          {
            label: "Overdue",
            value: String(kpi.overdue ?? 0),
          },
        ],
        actions: [
          { label: "Onboarding tab", href: "/employees?tab=onboarding" },
          { label: "Templates", href: "/employees?tab=onboarding" },
        ],
      };

    case "lnd":
      return {
        title: "Learning & Development",
        blurb:
          "Training records and certifications. Foundation lands in Phase 2 (P2-LD); this card shows current state plus the SkillsFuture catalogue link.",
        kpis: [
          {
            label: "Records",
            value: String(kpi.records ?? 0),
          },
          {
            label: "Avg hrs/employee/yr",
            value: ((kpi.avg_hours_per_employee as number) ?? 0).toFixed(1),
          },
          {
            label: "Data gap",
            value: kpi.data_missing ? "Yes" : "No",
          },
        ],
        actions: [
          { label: "SkillsFuture catalogue", href: "/training/skillsfuture" },
        ],
      };

    case "reward":
      return {
        title: "Reward · Recognition · Benefits",
        blurb:
          "Payroll on time + recognition signal in the last 30d. Recognition module ships in P2-RC; until then 'kudos 30d' will read 0.",
        kpis: [
          {
            label: "Last payroll",
            value: String(kpi.last_payroll ?? "—"),
          },
          {
            label: "Recognitions (30d)",
            value: String(kpi.recognitions_30d ?? 0),
          },
          {
            label: "Last period",
            value: String(kpi.last_payroll_period_end ?? "—"),
          },
        ],
        actions: [
          { label: "Payroll", href: "/payroll" },
          { label: "Claims", href: "/claims" },
          { label: "Leave", href: "/leave" },
        ],
      };

    case "progression":
      return {
        title: "Progression & Performance",
        blurb:
          "In-flight appraisal reviews vs signed-off. Goals/OKR layer arrives in P2-GO; for now this is appraisal-only.",
        kpis: [
          {
            label: "In flight",
            value: String(kpi.in_flight ?? 0),
          },
          {
            label: "Signed off",
            value: String(kpi.completed ?? 0),
          },
          {
            label: "Due",
            value: String(kpi.due_reviews ?? 0),
          },
        ],
        actions: [{ label: "Appraisals", href: "/appraisals" }],
      };

    case "retain":
      return {
        title: "Retain · Exit",
        blurb:
          "YTD churn vs same period last year. Exit interview workflow arrives in P2-EX; this card uses EmploymentEvent only for now.",
        kpis: [
          {
            label: "Churn YTD",
            value: `${((kpi.churn_ytd as number) ?? 0).toFixed(1)}%`,
          },
          {
            label: "YoY delta",
            value: `${((kpi.yoy_delta_ppt as number) ?? 0).toFixed(1)} ppt`,
          },
          {
            label: "Exits YTD",
            value: String(kpi.exits_ytd ?? 0),
          },
        ],
        actions: [
          { label: "Employees", href: "/employees" },
          { label: "Reports", href: "/reports" },
        ],
      };
  }
}

export function StageDetailPanel({ stageKey, stage, hero }: PanelProps) {
  const spec = buildSpec(stageKey, stage, hero);

  return (
    <div className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 sm:p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
            {spec.title}
          </h2>
          <p className="mt-1 text-xs text-[var(--color-gray-500)] max-w-2xl leading-relaxed">
            {spec.blurb}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-5">
        {spec.kpis.map((k) => (
          <div
            key={k.label}
            className="rounded-lg bg-[var(--color-surface-page)] px-3 py-2.5"
          >
            <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-gray-500)]">
              {k.label}
            </p>
            <p className="mt-0.5 text-lg font-bold text-[var(--color-gray-900)] tabular-nums">
              {k.value}
            </p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        {spec.actions.map((a) => (
          <Link
            key={a.href + a.label}
            href={a.href}
            className="inline-flex items-center gap-1 rounded-lg border border-[var(--color-gray-200)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--color-gray-700)] hover:bg-[var(--color-gray-50)] hover:border-[var(--color-gray-300)] transition-colors"
          >
            {a.label}
            <ArrowRight className="h-3 w-3" aria-hidden="true" />
          </Link>
        ))}
      </div>
    </div>
  );
}
