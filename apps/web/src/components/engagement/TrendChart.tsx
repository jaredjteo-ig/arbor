"use client";

/**
 * Simple 6-point line chart for the engagement trend hero.
 * Built with raw SVG to avoid pulling chart libraries.
 */

import type { TrendPoint } from "@/services/api/engagement";

interface TrendChartProps {
  points: TrendPoint[];
}

export function TrendChart({ points }: TrendChartProps) {
  const W = 720;
  const H = 180;
  const PAD_X = 40;
  const PAD_Y = 24;
  const innerW = W - PAD_X * 2;
  const innerH = H - PAD_Y * 2;

  const xs = points.map((_, i) =>
    points.length === 1
      ? PAD_X + innerW / 2
      : PAD_X + (i / (points.length - 1)) * innerW,
  );
  const ys = points.map((p) => {
    const v = p.avg_likert ?? 3;
    return PAD_Y + (1 - (v - 1) / 4) * innerH;
  });

  const path = points.length
    ? xs
        .map(
          (x, i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${ys[i].toFixed(1)}`,
        )
        .join(" ")
    : "";

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid meet"
      className="w-full h-44"
      role="img"
      aria-label={`Trend chart with ${points.length} pulse${points.length === 1 ? "" : "s"}`}
    >
      {/* Y-axis grid lines at 1, 2, 3, 4, 5 */}
      {[1, 2, 3, 4, 5].map((y) => {
        const yy = PAD_Y + (1 - (y - 1) / 4) * innerH;
        return (
          <g key={y}>
            <line
              x1={PAD_X}
              y1={yy}
              x2={W - PAD_X}
              y2={yy}
              stroke="var(--color-gray-100)"
              strokeWidth={1}
            />
            <text
              x={PAD_X - 8}
              y={yy + 3}
              textAnchor="end"
              fontSize="10"
              fill="var(--color-gray-400)"
            >
              {y}
            </text>
          </g>
        );
      })}

      {/* Line */}
      {points.length > 1 && (
        <path
          d={path}
          fill="none"
          stroke="rgb(225 29 72)"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

      {/* Points */}
      {points.map((p, i) => (
        <g key={p.survey_id}>
          <circle
            cx={xs[i]}
            cy={ys[i]}
            r={4.5}
            fill={
              p.is_anonymity_safe ? "rgb(225 29 72)" : "var(--color-gray-300)"
            }
            stroke="white"
            strokeWidth={2}
          >
            <title>
              {p.name}: {p.avg_likert?.toFixed(1) ?? "—"} / 5 (n={p.n})
              {!p.is_anonymity_safe && " — suppressed (n<5)"}
            </title>
          </circle>
          <text
            x={xs[i]}
            y={H - 6}
            textAnchor="middle"
            fontSize="10"
            fill="var(--color-gray-500)"
          >
            {p.closed_at?.slice(0, 10) ?? ""}
          </text>
        </g>
      ))}
    </svg>
  );
}
