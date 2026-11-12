import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { toneChip, toneText } from "@/luma/tokens";
import type { StatusKey, Tone } from "@/luma/types";
import { Panel } from "@/components/luma/panel";
import { StatusDot } from "@/components/luma/status-indicator";

interface MetricTileProps {
  icon: LucideIcon;
  label: string;
  value: string;
  hint?: string;
  tone?: Tone;
  status?: StatusKey;
  className?: string;
}

/** Compact inventory tile — used for VISÃO DO NÚCLEO style readouts. */
export const MetricTile = ({
  icon: Icon,
  label,
  value,
  hint,
  tone = "cyan",
  status,
  className,
}: MetricTileProps) => (
  <Panel
    interactive
    sheen={false}
    corners={false}
    className={cn("group p-2.5", className)}
  >
    <div className="flex items-start gap-2.5">
      <span
        className={cn(
          "grid size-8 shrink-0 place-items-center rounded-md border transition-shadow duration-220 ease-hud group-hover:shadow-glow-sm",
          toneChip[tone],
        )}
      >
        <Icon className="size-4" strokeWidth={1.8} />
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-[11.5px] font-medium text-foreground/90">{label}</p>
          {status && <StatusDot status={status} size="xs" />}
        </div>
        <p className={cn("hud-numeric mt-0.5 text-[13px] font-semibold", toneText[tone])}>
          {value}
        </p>
        {hint && <p className="mt-0.5 truncate text-[10px] text-subtle">{hint}</p>}
      </div>
    </div>
  </Panel>
);

interface StatReadoutProps {
  label: string;
  value: string;
  icon?: LucideIcon;
  tone?: Tone;
  className?: string;
}

export const StatReadout = ({ label, value, icon: Icon, tone = "cyan", className }: StatReadoutProps) => (
  <div className={cn("rounded-md border border-hud-soft bg-void/40 px-3 py-2", className)}>
    <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.16em] text-subtle">
      {Icon && <Icon className={cn("size-3", toneText[tone])} strokeWidth={2} />}
      <span className="font-display font-semibold">{label}</span>
    </div>
    <p className={cn("hud-numeric mt-1 text-[15px] font-semibold", toneText[tone])}>{value}</p>
  </div>
);
