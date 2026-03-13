"use client";

import { useState } from "react";
import { AppCard } from "@/components/design-system";
import { X } from "lucide-react";
import type {
  QAEvaluation,
  QAFailureCategoryValue,
  QAAffectedAgent,
  QAPatch,
} from "@/types/api";

/* ── Constants ────────────────────────────────────────────── */

const AGENTS: QAAffectedAgent[] = [
  "employment_act_specialist",
  "cpf_specialist",
  "foreign_manpower_specialist",
  "fair_employment_specialist",
  "tax_specialist",
  "wsh_specialist",
  "pdpa_specialist",
  "query_analyzer",
  "orchestrator",
  "response_synthesizer",
];

const CATEGORIES: QAFailureCategoryValue[] = [
  "wrong_law_cited",
  "correct_law_wrong_interpretation",
  "missed_critical_nuance",
  "ignored_company_context",
  "lost_conversation_context",
  "overly_generic",
  "wrong_domain_routing",
  "fabricated_citation",
  "other",
];

/** Human-readable short labels for agents */
const AGENT_LABELS: Record<QAAffectedAgent, string> = {
  employment_act_specialist: "Employment Act",
  cpf_specialist: "CPF",
  foreign_manpower_specialist: "Foreign Manpower",
  fair_employment_specialist: "Fair Employment",
  tax_specialist: "Tax",
  wsh_specialist: "WSH",
  pdpa_specialist: "PDPA",
  query_analyzer: "Query Analyzer",
  orchestrator: "Orchestrator",
  response_synthesizer: "Response Synth.",
};

/** Human-readable short labels for failure categories */
const CATEGORY_LABELS: Record<QAFailureCategoryValue, string> = {
  wrong_law_cited: "Wrong Law",
  correct_law_wrong_interpretation: "Wrong Interp.",
  missed_critical_nuance: "Missed Nuance",
  ignored_company_context: "No Context",
  lost_conversation_context: "Lost Context",
  overly_generic: "Too Generic",
  wrong_domain_routing: "Wrong Route",
  fabricated_citation: "Fabricated",
  other: "Other",
};

/* ── Helpers ──────────────────────────────────────────────── */

interface HeatmapData {
  grid: Record<string, Record<string, number>>;
  maxCount: number;
}

function buildHeatmap(evaluations: QAEvaluation[]): HeatmapData {
  const grid: Record<string, Record<string, number>> = {};
  let maxCount = 0;

  for (const agent of AGENTS) {
    grid[agent] = {};
    for (const cat of CATEGORIES) {
      grid[agent][cat] = 0;
    }
  }

  for (const ev of evaluations) {
    if (
      ev.has_material_correction &&
      ev.failure_category &&
      ev.affected_agent
    ) {
      const agent = ev.affected_agent as QAAffectedAgent;
      const cat = ev.failure_category as QAFailureCategoryValue;
      if (grid[agent] && grid[agent][cat] !== undefined) {
        grid[agent][cat] += 1;
        if (grid[agent][cat] > maxCount) {
          maxCount = grid[agent][cat];
        }
      }
    }
  }

  return { grid, maxCount };
}

function cellOpacity(count: number, max: number): number {
  if (max === 0 || count === 0) return 0;
  return 0.15 + (count / max) * 0.85;
}

/** Check if any open patches exist for a given agent+category */
function hasOpenPatch(
  patches: QAPatch[],
  agent: string,
  category: string,
): boolean {
  return patches.some(
    (p) =>
      p.affected_agent === agent &&
      p.failure_category === category &&
      (p.status === "proposed" || p.status === "approved"),
  );
}

/* ── Component ────────────────────────────────────────────── */

interface FailureHeatmapProps {
  evaluations: QAEvaluation[];
  patches: QAPatch[];
}

export function FailureHeatmap({ evaluations, patches }: FailureHeatmapProps) {
  const { grid, maxCount } = buildHeatmap(evaluations);
  const [drillDown, setDrillDown] = useState<{
    agent: QAAffectedAgent;
    category: QAFailureCategoryValue;
  } | null>(null);

  /* Evaluations matching the drilldown selection */
  const drillDownEvals = drillDown
    ? evaluations.filter(
        (ev) =>
          ev.affected_agent === drillDown.agent &&
          ev.failure_category === drillDown.category &&
          ev.has_material_correction,
      )
    : [];

  const totalFailures = evaluations.filter(
    (ev) => ev.has_material_correction && ev.failure_category,
  ).length;

  return (
    <AppCard
      variant="flat"
      header={
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Failure Heatmap
          </h4>
          <span className="text-xs text-[var(--color-gray-500)]">
            {totalFailures} failure{totalFailures !== 1 ? "s" : ""} total
          </span>
        </div>
      }
    >
      {totalFailures === 0 ? (
        <p className="text-sm text-[var(--color-gray-500)] text-center py-8">
          No failure patterns recorded yet.
        </p>
      ) : (
        <>
          {/* Heatmap grid */}
          <div className="overflow-x-auto -mx-5 px-5">
            <table
              className="w-full text-xs border-collapse"
              style={{ minWidth: "700px" }}
            >
              <thead>
                <tr>
                  <th className="text-left px-2 py-1.5 font-medium text-[var(--color-gray-700)] sticky left-0 bg-[var(--color-surface-card)]">
                    Agent
                  </th>
                  {CATEGORIES.map((cat) => (
                    <th
                      key={cat}
                      className="px-1.5 py-1.5 font-medium text-[var(--color-gray-600)] text-center"
                      style={{ writingMode: "vertical-lr", minWidth: "36px" }}
                    >
                      {CATEGORY_LABELS[cat]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {AGENTS.map((agent) => (
                  <tr key={agent}>
                    <td className="px-2 py-1 text-[var(--color-gray-700)] font-medium whitespace-nowrap sticky left-0 bg-[var(--color-surface-card)]">
                      {AGENT_LABELS[agent]}
                    </td>
                    {CATEGORIES.map((cat) => {
                      const count = grid[agent][cat];
                      const hasPatch = hasOpenPatch(patches, agent, cat);

                      return (
                        <td key={cat} className="p-0.5 text-center">
                          <button
                            type="button"
                            disabled={count === 0}
                            onClick={() =>
                              count > 0 &&
                              setDrillDown({ agent, category: cat })
                            }
                            className={`relative w-full aspect-square rounded transition-colors ${
                              count > 0
                                ? "cursor-pointer hover:ring-2 hover:ring-[var(--color-primary)] hover:ring-offset-1"
                                : "cursor-default"
                            }`}
                            style={{
                              backgroundColor:
                                count > 0
                                  ? `rgba(239, 68, 68, ${cellOpacity(count, maxCount)})`
                                  : "var(--color-gray-50)",
                              minHeight: "28px",
                            }}
                            title={`${AGENT_LABELS[agent]} / ${CATEGORY_LABELS[cat]}: ${count}`}
                          >
                            {count > 0 && (
                              <span className="text-[10px] font-semibold text-white mix-blend-difference">
                                {count}
                              </span>
                            )}
                            {hasPatch && (
                              <span
                                className="absolute top-0 right-0 w-2.5 h-2.5 rounded-full border border-white"
                                style={{
                                  backgroundColor: "var(--color-risk-amber)",
                                }}
                                title="Open patch"
                              />
                            )}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Drill-down panel */}
          {drillDown && drillDownEvals.length > 0 && (
            <div className="mt-4 border border-[var(--color-gray-200)] rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-[var(--color-gray-900)]">
                  {AGENT_LABELS[drillDown.agent]} /{" "}
                  {CATEGORY_LABELS[drillDown.category]}
                  <span className="font-normal text-[var(--color-gray-500)] ml-1.5">
                    ({drillDownEvals.length} evaluation
                    {drillDownEvals.length !== 1 ? "s" : ""})
                  </span>
                </p>
                <button
                  type="button"
                  onClick={() => setDrillDown(null)}
                  className="text-[var(--color-gray-400)] hover:text-[var(--color-gray-600)]"
                  aria-label="Close drill-down"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {drillDownEvals.map((ev) => (
                  <div
                    key={ev.id}
                    className="flex items-start gap-3 text-xs border-b border-[var(--color-gray-100)] pb-2 last:border-0"
                  >
                    <span className="text-[var(--color-gray-500)] whitespace-nowrap">
                      #{ev.id}
                    </span>
                    <span className="text-[var(--color-gray-700)] flex-1">
                      Conv. {ev.conversation_id}, Turn {ev.turn_number}
                      {ev.correction_text && (
                        <span className="block text-[var(--color-gray-500)] mt-0.5 line-clamp-2">
                          {ev.correction_text}
                        </span>
                      )}
                    </span>
                    <span className="text-[var(--color-gray-500)] whitespace-nowrap">
                      {new Date(ev.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </AppCard>
  );
}
