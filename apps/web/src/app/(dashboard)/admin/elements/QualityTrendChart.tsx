"use client";

import { AppCard } from "@/components/design-system";
import type { QASession } from "@/types/api";

/* ── Helpers ──────────────────────────────────────────────── */

function scoreColor(score: number): string {
  if (score >= 4) return "var(--color-risk-green)";
  if (score >= 2.5) return "var(--color-risk-amber)";
  return "var(--color-risk-red)";
}

const CHART_HEIGHT = 200;
const CHART_PADDING_TOP = 16;
const CHART_PADDING_BOTTOM = 40;
const CHART_PADDING_LEFT = 36;
const CHART_PADDING_RIGHT = 16;
const Y_MIN = 1;
const Y_MAX = 5;
const QUALITY_FLOOR = 3.5;

interface DataPoint {
  date: string;
  score: number;
  reviewer: string;
  conversationCount: number;
}

function toDataPoints(sessions: QASession[]): DataPoint[] {
  return sessions
    .filter((s) => s.status === "completed" && s.average_overall_score !== null)
    .sort(
      (a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    )
    .map((s) => ({
      date: new Date(s.created_at).toLocaleDateString("en-SG", {
        day: "2-digit",
        month: "short",
      }),
      score: s.average_overall_score as number,
      reviewer: s.reviewer_name,
      conversationCount: s.conversation_count,
    }));
}

/* ── Component ────────────────────────────────────────────── */

interface QualityTrendChartProps {
  sessions: QASession[];
}

export function QualityTrendChart({ sessions }: QualityTrendChartProps) {
  const data = toDataPoints(sessions);

  if (data.length === 0) {
    return (
      <AppCard
        variant="flat"
        header={
          <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Quality Score Trend
          </h4>
        }
      >
        <p className="text-sm text-[var(--color-gray-500)] text-center py-8">
          No completed sessions with scores yet.
        </p>
      </AppCard>
    );
  }

  const plotW =
    CHART_PADDING_LEFT + CHART_PADDING_RIGHT + Math.max(data.length * 60, 200);
  const plotH = CHART_HEIGHT;
  const drawW = plotW - CHART_PADDING_LEFT - CHART_PADDING_RIGHT;
  const drawH = plotH - CHART_PADDING_TOP - CHART_PADDING_BOTTOM;

  function yPos(score: number): number {
    const ratio = (score - Y_MIN) / (Y_MAX - Y_MIN);
    return CHART_PADDING_TOP + drawH - ratio * drawH;
  }

  function xPos(index: number): number {
    if (data.length === 1) return CHART_PADDING_LEFT + drawW / 2;
    return CHART_PADDING_LEFT + (index / (data.length - 1)) * drawW;
  }

  const floorY = yPos(QUALITY_FLOOR);

  /* Build polyline path */
  const polyline = data.map((d, i) => `${xPos(i)},${yPos(d.score)}`).join(" ");

  /* Y-axis ticks */
  const yTicks = [1, 2, 3, 4, 5];

  return (
    <AppCard
      variant="flat"
      header={
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Quality Score Trend
          </h4>
          <span className="text-xs text-[var(--color-gray-500)]">
            {data.length} completed session{data.length !== 1 ? "s" : ""}
          </span>
        </div>
      }
    >
      <div className="overflow-x-auto -mx-5 px-5">
        <svg
          viewBox={`0 0 ${plotW} ${plotH}`}
          className="w-full"
          style={{ minWidth: `${plotW}px`, maxHeight: `${plotH}px` }}
          role="img"
          aria-label="Quality score trend chart"
        >
          {/* Y-axis gridlines and labels */}
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

          {/* Quality floor reference line (3.5) */}
          <line
            x1={CHART_PADDING_LEFT}
            y1={floorY}
            x2={plotW - CHART_PADDING_RIGHT}
            y2={floorY}
            stroke="var(--color-risk-amber)"
            strokeWidth={1.5}
            strokeDasharray="6 4"
          />
          <text
            x={plotW - CHART_PADDING_RIGHT + 2}
            y={floorY - 4}
            fill="var(--color-risk-amber)"
            fontSize={10}
            fontWeight={500}
          >
            3.5
          </text>

          {/* Line connecting points */}
          {data.length > 1 && (
            <polyline
              points={polyline}
              fill="none"
              stroke="var(--color-primary)"
              strokeWidth={2}
              strokeLinejoin="round"
            />
          )}

          {/* Data points and X-axis labels */}
          {data.map((d, i) => (
            <g key={i}>
              {/* Circle */}
              <circle
                cx={xPos(i)}
                cy={yPos(d.score)}
                r={5}
                fill={scoreColor(d.score)}
                stroke="var(--color-surface-card)"
                strokeWidth={2}
              />
              {/* Tooltip via SVG title */}
              <title>
                {d.date} - Score: {d.score.toFixed(1)} - Reviewer: {d.reviewer}{" "}
                - {d.conversationCount} conversation
                {d.conversationCount !== 1 ? "s" : ""}
              </title>
              {/* X-axis label */}
              <text
                x={xPos(i)}
                y={plotH - CHART_PADDING_BOTTOM + 20}
                textAnchor="middle"
                fill="var(--color-gray-500)"
                fontSize={10}
              >
                {d.date}
              </text>
              {/* Score label above point */}
              <text
                x={xPos(i)}
                y={yPos(d.score) - 10}
                textAnchor="middle"
                fill={scoreColor(d.score)}
                fontSize={10}
                fontWeight={600}
              >
                {d.score.toFixed(1)}
              </text>
            </g>
          ))}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-3 text-xs text-[var(--color-gray-500)]">
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block w-4 h-0.5"
            style={{
              backgroundColor: "var(--color-primary)",
            }}
          />
          Overall score
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block w-4 border-t-2 border-dashed"
            style={{ borderColor: "var(--color-risk-amber)" }}
          />
          Quality floor (3.5)
        </div>
      </div>
    </AppCard>
  );
}
