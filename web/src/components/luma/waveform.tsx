import { cn } from "@/lib/utils";
import { toneColor } from "@/luma/tokens";
import type { Tone } from "@/luma/types";

interface WaveformProps {
  bars?: number;
  tone?: Tone;
  active?: boolean;
  className?: string;
  barClassName?: string;
}

/** Animated audio bars — purely decorative voice visualization. */
export const Waveform = ({
  bars = 6,
  tone = "cyan",
  active = true,
  className,
  barClassName,
}: WaveformProps) => (
  <div aria-hidden className={cn("flex h-7 items-center justify-center gap-[3px]", className)}>
    {Array.from({ length: bars }).map((_, index) => {
      const peak = index % 2 === 0 ? 1 : 0.62;
      const height = (28 + ((index * 37) % 60)) * peak;
      return (
        <span
          key={index}
          className={cn("w-[2px] rounded-full", barClassName)}
          style={{
            height: `${Math.min(100, height)}%`,
            backgroundColor: toneColor(tone, active ? 0.85 : 0.4),
            transformOrigin: "center",
            animation: active
              ? `luma-wave ${(0.75 + ((index * 13) % 9) / 10).toFixed(2)}s ease-in-out ${(index * 70) % 420}ms infinite`
              : undefined,
            transform: active ? undefined : "scaleY(0.28)",
            boxShadow: active ? `0 0 8px ${toneColor(tone, 0.45)}` : undefined,
          }}
        />
      );
    })}
  </div>
);
