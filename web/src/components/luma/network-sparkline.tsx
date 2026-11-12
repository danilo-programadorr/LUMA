import { useEffect, useId, useState } from "react";

import { cn } from "@/lib/utils";
import { toneColor } from "@/luma/tokens";
import type { Tone } from "@/luma/types";

interface NetworkSparklineProps {
  series: number[];
  tone?: Tone;
  className?: string;
  height?: number;
  showAxis?: boolean;
}

const buildPath = (series: number[], width: number, height: number) => {
  if (series.length < 2) return { line: "", area: "" };
  const max = Math.max(...series) * 1.12;
  const step = width / (series.length - 1);
  const points = series.map((value, index) => {
    const x = index * step;
    const y = height - (value / max) * height * 0.92 - height * 0.04;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  return {
    line: `M ${points.join(" L ")}`,
    area: `M 0,${height} L ${points.join(" L ")} L ${width},${height} Z`,
  };
};

export const NetworkSparkline = ({
  series,
  tone = "cyan",
  className,
  height = 72,
  showAxis = true,
}: NetworkSparklineProps) => {
  const gradientId = useId();
  const [drawn, setDrawn] = useState(false);
  const width = 100;
  const { line, area } = buildPath(series, width, 100);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDrawn(true), 220);
    return () => window.clearTimeout(timeout);
  }, []);

  return (
    <div className={cn("relative w-full", className)} style={{ height }}>
      <svg
        viewBox={`0 0 ${width} 100`}
        preserveAspectRatio="none"
        className="size-full overflow-visible"
        aria-hidden
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={toneColor(tone, 0.42)} />
            <stop offset="100%" stopColor={toneColor(tone, 0)} />
          </linearGradient>
        </defs>

        {showAxis &&
          [20, 40, 60, 80].map((y) => (
            <line
              key={y}
              x1="0"
              x2={width}
              y1={y}
              y2={y}
              stroke="hsl(var(--border))"
              strokeWidth="0.3"
              strokeDasharray="2 4"
            />
          ))}

        <path d={area} fill={`url(#${gradientId})`} opacity={drawn ? 1 : 0} className="transition-opacity duration-700 ease-hud" />
        <path
          d={line}
          fill="none"
          stroke={toneColor(tone, 0.95)}
          strokeWidth="1.1"
          vectorEffect="non-scaling-stroke"
          strokeLinecap="round"
          style={{
            strokeDasharray: 260,
            strokeDashoffset: drawn ? 0 : 260,
            transition: "stroke-dashoffset 1.3s cubic-bezier(0.22,1,0.36,1)",
            filter: `drop-shadow(0 0 4px ${toneColor(tone, 0.6)})`,
          }}
        />
      </svg>
    </div>
  );
};
