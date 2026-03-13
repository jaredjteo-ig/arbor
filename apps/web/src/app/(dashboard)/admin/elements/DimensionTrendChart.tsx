"use client";

import { useState } from "react";
import { AppCard } from "@/components/design-system";
import type { QASession, QADimensionScore } from "@/types/api";

/* ── Constants ────────────────────────────────────────────── */

const DIMENSIONS = [
  "Legal Accuracy",
  "Contextual Relevance",
  "Conversational Coherence",
  "Actionability",
  "Risk Awareness",
  "Citation Quality",
  "Language Understanding",
  "Completeness",
] as const;

type DimensionName = (typeof DIMENSIONS)[number];

const DIMENSION_COLORS: Record<DimensionName, string> = {
  "Legal Accuracy": "#3b82f6",
  "Contextual Relevance": "#8b5cf6",
  "Conversational Coherence": "#06b6d4",
  Actionability: "#10b981",
  "Risk Awareness": "#f59e0b",
  "Citation Quality": "#ef4444",
  "Language Understanding": "#ec4899",
  Completeness: "#6366f1",
};

const CHART_HEIGHT = 220;
const CHART_PADDING_TOP = 16;
const CHART_PADDING_BOTTOM = 40;
const CHART_PADDING_LEFT = 36;
const CHART_PADDING_RIGHT = 16;
const Y_MIN = 1;
const Y_MAX = 5;
const FLOOR = 3.5;

/* ── Data extraction ──────────────────────────────────────── */

interface SessionPoint {
  label: string;
  dimensionScores: Record<string, number>;
}

function extractSessionPoints(sessions: QASession[]): SessionPoint[] {
  return sessions
    .filter(
      (s) =>
        s.status === "completed" &&
        s.dimension_scores &&
        s.dimension_scores.length > 0,
    )
    .sort(
      (a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    )
    .map((s) => {
      const scoreMap: Record<string, number> = {};
      for (const ds of s.dimension_scores as QADimensionScore[]) {
        scoreMap[ds.dimension] = ds.average_score;
      }
      return {
        label: new Date(s.created_at).toLocaleDateString("en-SG", {
          day: "2-digit",
          month: "short",
        }),
        dimensionScores: scoreMap,
      };
    });
}

/* ── Component ────────────────────────────────────────────── */

interface DimensionTrendChartProps {
  sessions: QASession[];
}

export function DimensionTrendChart({ sessions }: DimensionTrendChartProps) {
  const [visible, setVisible] = useState<Set<DimensionName>>(
    () => new Set(DIMENSIONS),
  );

  const points = extractSessionPoints(sessions);

  function toggleDimension(dim: DimensionName) {
    setVisible((prev) => {
      const next = new Set(prev);
      if (next.has(dim)) {
        next.delete(dim);
      } else {
        next.add(dim);
      }
      return next;
    });
  }

  if (points.length === 0) {
    return (
      <AppCard
        variant="flat"
        header={
          <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Dimension Trends
          </h4>
        }
      >
        <p className="text-sm text-[var(--color-gray-500)] text-center py-8">
          No completed sessions with dimension scores yet.
        </p>
      </AppCard>
    );
  }

  const plotW =
    CHART_PADDING_LEFT +
    CHART_PADDING_RIGHT +
    Math.max(points.length * 60, 200);
  const plotH = CHART_HEIGHT;
  const drawW = plotW - CHART_PADDING_LEFT - CHART_PADDING_RIGHT;
  const drawH = plotH - CHART_PADDING_TOP - CHART_PADDING_BOTTOM;

  function yPos(score: number): number {
    const ratio = (score - Y_MIN) / (Y_MAX - Y_MIN);
    return CHART_PADDING_TOP + drawH - ratio * drawH;
  }

  function xPos(index: number): number {
    if (points.length === 1) return CHART_PADDING_LEFT + drawW / 2;
    return CHART_PADDING_LEFT + (index / (points.length - 1)) * drawW;
  }

  const yTicks = [1, 2, 3, 4, 5];
  const floorY = yPos(FLOOR);

  return (
    <AppCard
      variant="flat"
      header={
        <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
          Dimension Trends
        </h4>
      }
    >
      {/* Dimension toggles */}
      <div className="flex flex-wrap gap-2 mb-4">
        {DIMENSIONS.map((dim) => {
          const isActive = visible.has(dim);
          const color = DIMENSION_COLORS[dim];
          /* Find latest score for badge coloring */
          const latestPoint = points[points.length - 1];
          const latestScore = latestPoint?.dimensionScores[dim] ?? null;
          const isBelowFloor = latestScore !== null && latestScore < FLOOR;

          return (
            <button
              key={dim}
              type="button"
              onClick={() => toggleDimension(dim)}
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border transition-colors ${
                isActive
                  ? "border-current"
                  : "border-[var(--color-gray-200)] text-[var(--color-gray-400)]"
              }`}
              style={isActive ? { color, borderColor: color } : undefined}
            >
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{
                  backgroundColor: isActive ? color : "var(--color-gray-300)",
                }}
              />
              {dim}
              {isBelowFloor && isActive && (
                <span className="ml-0.5 text-[var(--color-risk-amber)]">!</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Chart */}
      <div className="overflow-x-auto -mx-5 px-5">
        <svg
          viewBox={`0 0 ${plotW} ${plotH}`}
          className="w-full"
          style={{ minWidth: `${plotW}px`, maxHeight: `${plotH}px` }}
          role="img"
          aria-label="Dimension trend chart"
        >
          {/* Y-axis gridlines */}
          {yTicks.map((tick) => (
            <g key={tick}>
              <line
                x1={CHART_PADDING_LEFT}
                y1={yPos(tick)}
                x2={plotW - CHART_PADDING_RIGHT}
                y2={yPos(tick)}
                stroke="var(--color-gray-200)"
                strokeWidth={1}
              />
              <text
                x={CHART_PADDING_LEFT - 8}
                y={yPos(tick) + 4}
                textAnchor="end"
                fill="var(--color-gray-500)"
                fontSize={11}
              >
                {tick}
              </text>
            </g>
          ))}

          {/* Quality floor */}
          <line
            x1={CHART_PADDING_LEFT}
            y1={floorY}
            x2={plotW - CHART_PADDING_RIGHT}
            y2={floorY}
            stroke="var(--color-risk-amber)"
            strokeWidth={1}
            strokeDasharray="4 3"
            opacity={0.6}
          />

          {/* X-axis labels */}
          {points.map((pt, i) => (
            <text
              key={i}
              x={xPos(i)}
              y={plotH - CHART_PADDING_BOTTOM + 20}
              textAnchor="middle"
              fill="var(--color-gray-500)"
              fontSize={10}
            >
              {pt.label}
            </text>
          ))}

          {/* Dimension lines */}
          {DIMENSIONS.filter((dim) => visible.has(dim)).map((dim) => {
            const color = DIMENSION_COLORS[dim];
            const linePoints = points
              .map((pt, i) => {
                const score = pt.dimensionScores[dim];
                if (score === undefined) return null;
                return `${xPos(i)},${yPos(score)}`;
              })
              .filter(Boolean)
              .join(" ");

            return (
              <g key={dim}>
                {linePoints && (
                  <polyline
                    points={linePoints}
                    fill="none"
                    stroke={color}
                    strokeWidth={1.5}
                    strokeLinejoin="round"
                    opacity={0.85}
                  />
                )}
                {points.map((pt, i) => {
                  const score = pt.dimensionScores[dim];
                  if (score === undefined) return null;
                  return (
                    <circle
                      key={i}
                      cx={xPos(i)}
                      cy={yPos(score)}
                      r={3}
                      fill={color}
                      stroke="var(--color-surface-card)"
                      strokeWidth={1.5}
                    >
                      <title>
                        {dim}: {score.toFixed(1)} ({pt.label})
                      </title>
                    </circle>
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>
    </AppCard>
  );
}
