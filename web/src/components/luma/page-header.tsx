import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { toneChip } from "@/luma/tokens";
import type { Tone } from "@/luma/types";
import { Panel } from "@/components/luma/panel";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description?: string;
  icon: LucideIcon;
  tone?: Tone;
  meta?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

/** Shared module header used by every non-dashboard screen. */
export const PageHeader = ({
  eyebrow,
  title,
  description,
  icon: Icon,
  tone = "cyan",
  meta,
  actions,
  className,
}: PageHeaderProps) => (
  <Panel
    variant="spotlight"
    corners
    className={cn("animate-fade-up p-3.5 sm:p-4", className)}
  >
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <span className={cn("grid size-10 shrink-0 place-items-center rounded-lg border", toneChip[tone])}>
          <Icon className="size-5" strokeWidth={1.8} />
        </span>
        <div className="min-w-0">
          <p className="hud-label text-[9.5px] text-muted-foreground">{eyebrow}</p>
          <h1 className="hud-title mt-1 text-[22px] leading-none text-foreground text-glow-soft sm:text-[26px]">
            {title}
          </h1>
          {description && (
            <p className="mt-1.5 max-w-2xl text-[11.5px] leading-relaxed text-muted-foreground">
              {description}
            </p>
          )}
        </div>
      </div>

      {(meta || actions) && (
        <div className="flex shrink-0 flex-col gap-2 lg:items-end">
          {meta && <div className="flex flex-wrap items-center gap-1.5">{meta}</div>}
          {actions && <div className="flex flex-wrap items-center gap-1.5">{actions}</div>}
        </div>
      )}
    </div>
  </Panel>
);

interface SectionHeadingProps {
  title: string;
  icon?: LucideIcon;
  hint?: string;
  tone?: Tone;
  action?: ReactNode;
  className?: string;
}

export const SectionHeading = ({
  title,
  icon: Icon,
  hint,
  tone = "cyan",
  action,
  className,
}: SectionHeadingProps) => (
  <div className={cn("mb-2.5 flex items-center gap-2", className)}>
    {Icon && (
      <span className={cn("grid size-6 place-items-center rounded-md border", toneChip[tone])}>
        <Icon className="size-3.5" strokeWidth={1.9} />
      </span>
    )}
    <h2 className="hud-label text-[10.5px] text-foreground/90">{title}</h2>
    {hint && <span className="hidden truncate text-[10px] text-subtle sm:inline">{hint}</span>}
    {action && <div className="ml-auto">{action}</div>}
  </div>
);
