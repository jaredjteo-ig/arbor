"use client";

import { AppCard } from "@/components/design-system";
import { AlertTriangle } from "lucide-react";
import type { QAEvaluation, QAAffectedAgent } from "@/types/api";

/* ── Constants ────────────────────────────────────────────── */

const CITATION_THRESHOLD = 3.0;
const MIN_EVALUATIONS = 3;

/** Map agents to their domain */
const AGENT_DOMAIN: Record<string, string> = {
  employment_act_specialist: "Employment Act",
  cpf_specialist: "CPF",
  foreign_manpower_specialist: "Foreign Manpower",
  fair_employment_specialist: "Fair Employment",
  tax_specialist: "Tax",
  wsh_specialist: "WSH",
  pdpa_specialist: "PDPA",
  query_analyzer: "Query Analysis",
  orchestrator: "Orchestration",
  response_synthesizer: "Response Synthesis",
};

/* ── Gap detection logic ──────────────────────────────────── */

interface KBGap {
  domain: string;
  agent: QAAffectedAgent;
  avgCitationScore: number;
  evaluationCount: number;
}

function detectGaps(evaluations: QAEvaluation[]): KBGap[] {
  /* Group evaluations by affected_agent */
  const byAgent = new Map<string, number[]>();

  for (const ev of evaluations) {
    /* Count all evaluations with low citation quality, regardless of failure flag */
    const agent = ev.affected_agent;
    if (!agent) continue;

    if (!byAgent.has(agent)) {
      byAgent.set(agent, []);
    }
    byAgent.get(agent)!.push(ev.score_citation_quality);
  }

  const gaps: KBGap[] = [];

  for (const [agent, scores] of byAgent) {
    if (scores.length < MIN_EVALUATIONS) continue;

    const avg = scores.reduce((sum, s) => sum + s, 0) / scores.length;
    if (avg < CITATION_THRESHOLD) {
      gaps.push({
        domain: AGENT_DOMAIN[agent] ?? agent,
        agent: agent as QAAffectedAgent,
        avgCitationScore: avg,
        evaluationCount: scores.length,
      });
    }
  }

  /* Sort by avg score ascending (worst first) */
  gaps.sort((a, b) => a.avgCitationScore - b.avgCitationScore);

  return gaps;
}

/* ── Score colour helper ──────────────────────────────────── */

function citationColor(score: number): string {
  if (score < 2) return "var(--color-risk-red)";
  if (score < 3) return "var(--color-risk-amber)";
  return "var(--color-gray-700)";
}

/* ── Component ────────────────────────────────────────────── */

interface KBGapDetectorProps {
  evaluations: QAEvaluation[];
}

export function KBGapDetector({ evaluations }: KBGapDetectorProps) {
  const gaps = detectGaps(evaluations);

  return (
    <AppCard
      variant="flat"
      header={
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
            KB Gap Detector
          </h4>
          {gaps.length > 0 && (
            <span className="text-xs text-[var(--color-risk-amber)] font-medium">
              {gaps.length} gap{gaps.length !== 1 ? "s" : ""} found
            </span>
          )}
        </div>
      }
    >
      {gaps.length === 0 ? (
        <p className="text-sm text-[var(--color-gray-500)] text-center py-8">
          No knowledge base gaps detected. Citation quality is above{" "}
          {CITATION_THRESHOLD} across all agents with sufficient data.
        </p>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-[var(--color-gray-500)]">
            Agents where average citation quality falls below{" "}
            {CITATION_THRESHOLD} across {MIN_EVALUATIONS}+ evaluations. Consider
            adding provisions in KB Management.
          </p>

          {gaps.map((gap) => (
            <div
              key={gap.agent}
              className="flex items-start gap-3 p-3 rounded-lg border border-[var(--color-gray-200)] bg-[var(--color-gray-50)]"
            >
              <AlertTriangle
                className="h-4 w-4 shrink-0 mt-0.5"
                style={{ color: citationColor(gap.avgCitationScore) }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--color-gray-900)]">
                  {gap.domain}
                </p>
                <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                  {gap.agent.replace(/_/g, " ")}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p
                  className="text-sm font-semibold"
                  style={{ color: citationColor(gap.avgCitationScore) }}
                >
                  {gap.avgCitationScore.toFixed(1)}
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">
                  {gap.evaluationCount} evals
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </AppCard>
  );
}
