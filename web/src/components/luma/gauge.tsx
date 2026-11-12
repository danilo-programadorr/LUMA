import { useId } from "react";

import { cn } from "@/lib/utils";
import { toneColor, toneHsl } from "@/luma/tokens";
import type { Tone } from "@/luma/types";
import { useCountUp } from "@/luma/use-count-up";

interface GaugeProps {
  value: number;
  label: string;
  tone?: Tone;
  size?: number;
  decimals?: number;
  suffix?: string;
  delay?: number;
  className?: string;
}

const RADIUS = 40;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const SWEEP = 0.75;
const TRACK = CIRCUMFERENCE * SWEEP;

/** Circular HUD gauge that fills from 0 → value on mount. */
export const Gauge = ({
  value,
  label,
  tone = "cyan",
  size = 132,
  decimals = 0,
  suffix = "%",
  delay = 160,
  className,
}: GaugeProps) => {
  const gradientId = useId();
  const glowId = useId();
  const animated = useCountUp(value, { duration: 1200, delay, decimals: 0 });
  const progress = Math.min(1, animated / 100);
  const [h, s, l] = toneHsl[tone].split(", ");

  return (
    <div
      className={cn("relative grid place-items-center", className)}
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 100 100" className="size-full -rotate-[135deg]">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={`hsl(${h}, ${s}, ${l})`} />
            <stop offset="100%" stopColor={toneColor(tone, 0.55)} />
          </linearGradient>
          <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <circle
          cx="50"
          cy="50"
          r={RADIUS}
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth={7}
          strokeLinecap="round"
          strokeDasharray={`${TRACK} ${CIRCUMFERENCE}`}
        />
        <circle
          cx="50"
          cy="50"
          r={RADIUS}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={7}
          strokeLinecap="round"
          strokeDasharray={`${TRACK * progress} ${CIRCUMFERENCE}`}
          filter={`url(#${glowId})`}
          className="transition-none"
        />
        <circle
          cx="50"
          cy="50"
          r={RADIUS - 9}
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth={0.7}
          strokeDasharray="1.6 3.4"
          opacity={0.75}
        />
      </svg>

      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          <div className="hud-numeric text-[19px] font-semibold leading-none text-foreground">
            {Math.round(animated)}
            <span className="text-[11px] text-muted-foreground">{suffix}</span>
          </div>
          <div className="hud-label mt-1 text-[9px] text-muted-foreground">{label}</div>
        </div>
      </div>
    </div>
  );
};

interface ProgressMeterProps {
  value: number;
  tone?: Tone;
  className?: string;
  height?: string;
  delay?: number;
  animated?: boolean;
  segments?: number;
}

/** Linear progress meter with HUD glow. */
export const ProgressMeter = ({
  value,
  tone = "cyan",
  className,
  height = "h-1.5",
  delay = 220,
  animated = true,
  segments,
}: ProgressMeterProps) => {
  const counted = useCountUp(value, { duration: 1100, delay });
  const width = animated ? counted : value;
  const [h, s, l] = toneHsl[tone].split(", ");

  return (
    <div
      className={cn(
        "relative w-full overflow-hidden rounded-full border border-hud-soft bg-void/70",
        height,
        className,
      )}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full transition-[width] duration-300 ease-hud"
        style={{
          width: `${Math.min(100, width)}%`,
          backgroundImage: `linear-gradient(90deg, hsla(${h}, ${s}, ${l}, 0.55), hsl(${h}, ${s}, ${l}))`,
          boxShadow: `0 0 14px -2px ${toneColor(tone, 0.75)}`,
        }}
      />
      {segments ? (
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            backgroundImage:
              "repeating-linear-gradient(90deg, transparent 0, transparent 6px, rgba(2,10,18,0.85) 6px, rgba(2,10,18,0.85) 8px)",
          }}
        />
      ) : null}
    </div>
  );
};

interface SegmentBarProps {
  value: number;
  tone?: Tone;
  className?: string;
}

/** Compact tooltip-free bar used inside dense device rows. */
export const SegmentBar = ({ value, tone = "cyan", className }: SegmentBarProps) => (
  <ProgressMeter
    value={value}
    tone={tone}
    height="h-1"
    delay={260}
    className={cn("opacity-90", className)}
  />
);
