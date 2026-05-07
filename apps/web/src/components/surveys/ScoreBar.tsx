"use client";

/**
 * Visual score bar for Likert / NPS / aggregate scores.
 * Round-5 P45 reusable pattern — extracted for shared use across
 * exit-interviews + engagement + appraisals.
 *
 * Round-2 L7 amendment: also exposes textual label for screen-reader
 * + colour-blind users (not colour-only encoding).
 */

interface ScoreBarProps {
  /** 0-100 percentage of the bar fill. */
  score: number;
  /** Override the colour band thresholds. */
  thresholds?: { high: number; medium: number };
  /** Show the numeric label inside / next to the bar. */
  showLabel?: boolean;
  /** Display as small/medium/large. */
  size?: "sm" | "md" | "lg";
}

export function ScoreBar({
  score,
  thresholds = { high: 70, medium: 40 },
  showLabel = true,
  size = "md",
}: ScoreBarProps) {
  const pct = Math.max(0, Math.min(100, score));
  const tier =
    pct >= thresholds.high
      ? "high"
      : pct >= thresholds.medium
        ? "medium"
        : "low";
  const label = tier === "high" ? "High" : tier === "medium" ? "Medium" : "Low";
  const colour =
    tier === "high"
      ? "var(--color-success)"
      : tier === "medium"
        ? "var(--color-warning)"
        : "var(--color-error)";
  const heights = { sm: "h-1.5", md: "h-2.5", lg: "h-4" };

  return (
    <div className="flex items-center gap-2">
      <div
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} score: ${pct.toFixed(0)} of 100`}
        className={`flex-1 bg-[var(--color-gray-100)] rounded-full overflow-hidden ${heights[size]}`}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: colour }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-[var(--color-gray-700)] min-w-[2rem] text-right">
          {pct.toFixed(0)}
        </span>
      )}
      <span className="sr-only">{label}</span>
    </div>
  );
}

/* ── Distribution bars — for aggregator views ─────────────────── */

interface LikertDistributionBarProps {
  /** {1: count, 2: count, ... 5: count} */
  distribution: Record<string | number, number>;
  /** Average score (1-5) */
  avg?: number | null;
  /** Total respondents */
  n?: number;
}

export function LikertDistributionBar({
  distribution,
  avg,
  n,
}: LikertDistributionBarProps) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0) || 1;
  const colours = [
    "var(--color-error)",
    "var(--color-warning)",
    "var(--color-gray-300)",
    "var(--color-success)",
    "var(--color-success)",
  ];
  return (
    <div>
      <div className="flex h-3 rounded-full overflow-hidden">
        {[1, 2, 3, 4, 5].map((bucket) => {
          const count =
            distribution[bucket] || distribution[String(bucket)] || 0;
          const pct = (count / total) * 100;
          if (pct === 0) return null;
          return (
            <div
              key={bucket}
              className="h-full"
              style={{
                width: `${pct}%`,
                backgroundColor: colours[bucket - 1],
              }}
              aria-label={`${bucket} stars: ${count} of ${total}`}
            />
          );
        })}
      </div>
      {(avg !== undefined && avg !== null) || n !== undefined ? (
        <div className="flex justify-between mt-1 text-xs text-[var(--color-gray-500)]">
          {avg !== undefined && avg !== null && (
            <span>Avg {avg.toFixed(1)} / 5</span>
          )}
          {n !== undefined && <span>n = {n}</span>}
        </div>
      ) : null}
    </div>
  );
}
