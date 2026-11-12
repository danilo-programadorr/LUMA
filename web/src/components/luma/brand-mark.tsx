import { cn } from "@/lib/utils";

interface LumaBrandMarkProps {
  className?: string;
  animated?: boolean;
}

/** Abstract LUMA symbol — concentric orbits around a pulsing core. */
export const LumaBrandMark = ({ className, animated = true }: LumaBrandMarkProps) => (
  <svg viewBox="0 0 44 44" className={cn("overflow-visible", className)} aria-hidden>
    <defs>
      <linearGradient id="luma-mark-gradient" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="hsl(210 100% 54%)" />
        <stop offset="52%" stopColor="hsl(186 100% 50%)" />
        <stop offset="100%" stopColor="hsl(183 100% 59%)" />
      </linearGradient>
    </defs>

    <circle
      cx="22"
      cy="22"
      r="19.4"
      fill="none"
      stroke="url(#luma-mark-gradient)"
      strokeWidth="0.8"
      opacity="0.32"
    />

    <g className={animated ? "animate-orbit-slow" : undefined} style={{ transformOrigin: "22px 22px" }}>
      <circle
        cx="22"
        cy="22"
        r="15"
        fill="none"
        stroke="url(#luma-mark-gradient)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeDasharray="30 12"
      />
    </g>

    <ellipse
      cx="22"
      cy="22"
      rx="19"
      ry="6.4"
      fill="none"
      stroke="url(#luma-mark-gradient)"
      strokeWidth="0.85"
      opacity="0.55"
      transform="rotate(-28 22 22)"
    />
    <ellipse
      cx="22"
      cy="22"
      rx="6.4"
      ry="19"
      fill="none"
      stroke="hsl(186 100% 50%)"
      strokeWidth="0.6"
      opacity="0.3"
    />

    <circle cx="22" cy="22" r="8.4" fill="none" stroke="hsl(186 100% 50%)" strokeWidth="0.7" opacity="0.45" />
    <circle cx="22" cy="22" r="4.3" fill="url(#luma-mark-gradient)" />
    <circle cx="22" cy="22" r="2" fill="hsl(203 100% 96%)" opacity="0.9" />

    <circle cx="41.2" cy="22" r="1.7" fill="hsl(183 100% 59%)" />
    <circle cx="22" cy="2.8" r="1.1" fill="hsl(186 100% 50%)" opacity="0.75" />
    <circle cx="6.4" cy="34" r="0.9" fill="hsl(210 100% 54%)" opacity="0.6" />
  </svg>
);

interface LumaWordmarkProps {
  className?: string;
  subtitle?: string;
  compact?: boolean;
}

export const LumaWordmark = ({ className, subtitle = "CENTRO DE COMANDO", compact = false }: LumaWordmarkProps) => (
  <div className={cn("min-w-0", className)}>
    <div
      className={cn(
        "hud-title pl-[0.24em] leading-none tracking-[0.24em] text-foreground text-glow-soft",
        compact ? "text-[19px]" : "text-[23px]",
      )}
    >
      LUMA
    </div>
    {!compact && (
      <div className="hud-label mt-1.5 pl-[0.24em] text-[8.5px] tracking-[0.28em] text-muted-foreground">
        {subtitle}
      </div>
    )}
  </div>
);
