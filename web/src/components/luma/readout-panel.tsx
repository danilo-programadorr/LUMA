import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { toneChip, toneText } from "@/luma/tokens";
import type { Tone } from "@/luma/types";
import { Panel, PanelHeader } from "@/components/luma/panel";

export interface ReadoutRow {
  id: string;
  label: string;
  value: string;
  tone?: Tone;
  icon?: LucideIcon;
  hint?: string;
}

interface ReadoutPanelProps {
  title: string;
  icon?: LucideIcon;
  tone?: Tone;
  hint?: string;
  action?: ReactNode;
  rows: ReadoutRow[];
  className?: string;
  columns?: 1 | 2;
}

/** Dense label/value panel reused across every module screen. */
export const ReadoutPanel = ({
  title,
  icon,
  tone = "cyan",
  hint,
  action,
  rows,
  className,
  columns = 1,
}: ReadoutPanelProps) => (
  <Panel className={cn("animate-fade-up", className)}>
    <PanelHeader icon={icon} tone={tone} title={title} hint={hint} action={action} />
    <dl className={cn("grid gap-1.5 p-3.5", columns === 2 ? "sm:grid-cols-2" : "")}>
      {rows.map((row) => (
        <div
          key={row.id}
          className="flex items-center gap-2 rounded-md border border-hud-soft bg-void/35 px-2.5 py-1.5 transition-colors duration-150 ease-hud hover:border-primary/40"
        >
          {row.icon && (
            <span className={cn("grid size-6 shrink-0 place-items-center rounded border", toneChip[row.tone ?? tone])}>
              <row.icon className="size-3" strokeWidth={2} />
            </span>
          )}
          <dt className="min-w-0 flex-1">
            <span className="block truncate text-[11px] text-muted-foreground">{row.label}</span>
            {row.hint && <span className="block truncate text-[9.5px] text-subtle">{row.hint}</span>}
          </dt>
          <dd className={cn("hud-numeric shrink-0 text-[11.5px] font-medium", toneText[row.tone ?? tone])}>
            {row.value}
          </dd>
        </div>
      ))}
    </dl>
  </Panel>
);
