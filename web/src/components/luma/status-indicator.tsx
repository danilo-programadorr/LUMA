import * as React from "react";

import { cn } from "@/lib/utils";
import { statusMeta, toneChip, toneText } from "@/luma/tokens";
import type { StatusKey, Tone } from "@/luma/types";

const toneDot: Record<Tone, string> = {
  cyan: "bg-primary text-primary",
  blue: "bg-accent text-accent",
  violet: "bg-violet text-violet",
  green: "bg-success text-success",
  amber: "bg-warning text-warning",
  red: "bg-destructive text-destructive",
  slate: "bg-subtle text-subtle",
};

interface StatusDotProps {
  /** Explicit color tone. When omitted, derives from `status`. */
  tone?: Tone;
  status?: StatusKey;
  pulse?: boolean;
  size?: "xs" | "sm" | "md";
  className?: string;
}

export const StatusDot = ({
  tone,
  status,
  pulse = true,
  size = "sm",
  className,
}: StatusDotProps) => {
  const resolved = tone ?? (status ? statusMeta[status].tone : "cyan");
  const sizes = {
    xs: "size-1",
    sm: "size-1.5",
    md: "size-2",
  };

  return (
    <span
      aria-hidden
      className={cn(
        "inline-block shrink-0 rounded-full",
        sizes[size],
        toneDot[resolved],
        pulse && "animate-pulse-dot",
        className,
      )}
    />
  );
};

interface StatusBadgeProps {
  status: StatusKey;
  label?: string;
  className?: string;
  compact?: boolean;
}

export const StatusBadge = ({ status, label, className, compact }: StatusBadgeProps) => {
  const meta = statusMeta[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10.5px] font-medium",
        toneChip[meta.tone],
        className,
      )}
    >
      <StatusDot tone={meta.tone} />
      {!compact && <span>{label ?? meta.label}</span>}
    </span>
  );
};

interface ToneChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
  icon?: React.ElementType;
  glow?: boolean;
}

export const ToneChip = ({
  tone = "cyan",
  icon: Icon,
  glow = false,
  children,
  className,
  ...props
}: ToneChipProps) => (
  <span
    className={cn(
      "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10.5px] font-medium",
      toneChip[tone],
      className,
    )}
    {...props}
  >
    {Icon && <Icon className="size-3" strokeWidth={2} />}
    {children}
  </span>
);

interface ToneIconProps {
  icon: React.ElementType;
  tone?: Tone;
  className?: string;
}

/** Square HUD icon tile used across cards and lists. */
export const ToneIcon = ({ icon: Icon, tone = "cyan", className }: ToneIconProps) => (
  <span
    className={cn(
      "grid size-8 shrink-0 place-items-center rounded-md border",
      toneChip[tone],
      className,
    )}
  >
    <Icon className="size-4" strokeWidth={1.8} />
  </span>
);

export const ToneLabel = ({ tone, children, className }: { tone: Tone; children: React.ReactNode; className?: string }) => (
  <span className={cn("text-[10.5px] font-semibold", toneText[tone], className)}>{children}</span>
);
