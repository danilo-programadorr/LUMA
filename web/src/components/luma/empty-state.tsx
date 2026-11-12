import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import { toneChip } from "@/luma/tokens";
import type { Tone } from "@/luma/types";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  tone?: Tone;
  action?: ReactNode;
  className?: string;
  compact?: boolean;
}

export const EmptyState = ({
  title,
  description,
  icon: Icon = Sparkles,
  tone = "cyan",
  action,
  className,
  compact = false,
}: EmptyStateProps) => (
  <div
    className={cn(
      "flex flex-col items-center justify-center gap-2.5 rounded-lg border border-dashed border-hud-line bg-void/30 text-center",
      compact ? "px-4 py-6" : "px-6 py-12",
      className,
    )}
  >
    <span
      className={cn(
        "grid size-10 place-items-center rounded-full border",
        toneChip[tone],
      )}
    >
      <Icon className="size-4" strokeWidth={1.7} />
    </span>
    <p className="text-[12.5px] font-medium text-foreground/90">{title}</p>
    {description && (
      <p className="max-w-xs text-[10.5px] leading-relaxed text-muted-foreground">{description}</p>
    )}
    {action && <div className="mt-1">{action}</div>}
  </div>
);
