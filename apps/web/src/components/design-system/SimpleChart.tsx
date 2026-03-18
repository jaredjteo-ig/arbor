"use client";

/* ── Pure CSS/HTML Chart Components ───────────────────────── */

interface BarChartProps {
  title: string;
  data: { label: string; value: number; color?: string }[];
  maxValue?: number;
  showValues?: boolean;
  height?: number;
}

export function BarChart({
  title,
  data,
  maxValue,
  showValues = true,
  height = 200,
}: BarChartProps) {
  const max = maxValue || Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
        {title}
      </h4>
      <div className="flex items-end gap-2" style={{ height }}>
        {data.map((item, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <div className="w-full relative" style={{ height }}>
              <div
                className="absolute bottom-0 w-full rounded-t-[4px] transition-all duration-500"
                style={{
                  height: `${(item.value / max) * 100}%`,
                  backgroundColor: item.color || "var(--color-primary)",
                  minHeight: item.value > 0 ? 4 : 0,
                }}
              />
            </div>
            {showValues && (
              <span className="text-xs font-medium text-[var(--color-gray-700)]">
                {item.value.toLocaleString()}
              </span>
            )}
            <span className="text-xs text-[var(--color-gray-500)] truncate max-w-full text-center">
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface DonutChartProps {
  title: string;
  data: { label: string; value: number; color: string }[];
  size?: number;
}

export function DonutChart({ title, data, size = 160 }: DonutChartProps) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  let cumulative = 0;

  const segments = data.map((item) => {
    const start = cumulative;
    cumulative += (item.value / total) * 360;
    return { ...item, start, end: cumulative };
  });

  // Build conic-gradient
  const gradient = segments
    .map((s) => `${s.color} ${s.start}deg ${s.end}deg`)
    .join(", ");

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
        {title}
      </h4>
      <div className="flex items-center gap-4">
        <div
          className="rounded-full shrink-0"
          style={{
            width: size,
            height: size,
            background:
              total > 0
                ? `conic-gradient(${gradient})`
                : "var(--color-gray-200)",
            mask: `radial-gradient(circle at center, transparent 40%, black 41%)`,
            WebkitMask: `radial-gradient(circle at center, transparent 40%, black 41%)`,
          }}
        />
        <div className="space-y-1.5">
          {data.map((item, i) => (
            <div key={i} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-sm shrink-0"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-xs text-[var(--color-gray-600)]">
                {item.label}: {item.value.toLocaleString()} (
                {total > 0 ? Math.round((item.value / total) * 100) : 0}%)
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface TrendLineProps {
  title: string;
  data: { label: string; value: number }[];
  color?: string;
  height?: number;
}

export function TrendLine({
  title,
  data,
  color = "var(--color-primary)",
  height = 120,
}: TrendLineProps) {
  if (data.length < 2) return null;
  const max = Math.max(...data.map((d) => d.value), 1);
  const min = Math.min(...data.map((d) => d.value), 0);
  const range = max - min || 1;

  const points = data.map((d, i) => ({
    x: (i / (data.length - 1)) * 100,
    y: 100 - ((d.value - min) / range) * 100,
  }));

  const pathD = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
    .join(" ");

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
        {title}
      </h4>
      <div style={{ height }}>
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="w-full h-full"
        >
          <path
            d={pathD}
            fill="none"
            stroke={color}
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      </div>
      <div className="flex justify-between">
        {data
          .filter((_, i) => i === 0 || i === data.length - 1)
          .map((d, i) => (
            <span key={i} className="text-xs text-[var(--color-gray-500)]">
              {d.label}
            </span>
          ))}
      </div>
    </div>
  );
}
