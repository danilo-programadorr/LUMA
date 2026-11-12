import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";
import { toneChip, toolStatusMeta } from "@/luma/tokens";
import type { Tool } from "@/luma/types";
import { Panel } from "@/components/luma/panel";
import { ToneChip } from "@/components/luma/status-indicator";

interface ToolStatusCardProps {
  tool: Tool;
  variant?: "row" | "tile";
  className?: string;
}

export const ToolStatusCard = ({ tool, variant = "row", className }: ToolStatusCardProps) => {
  const Icon = tool.icon;
  const meta = toolStatusMeta[tool.status];
  const muted = tool.status === "planned" || tool.status === "disabled";

  if (variant === "tile") {
    return (
      <Panel interactive sheen={false} className={cn("group flex flex-col gap-2.5 p-3", className)}>
        <div className="flex items-start justify-between gap-2">
          <span className={cn("grid size-9 place-items-center rounded-lg border", toneChip[muted ? "slate" : tool.tone])}>
            <Icon className="size-[18px]" strokeWidth={1.8} />
          </span>
          <ToneChip tone={meta.tone} className="text-[9.5px]">
            <span className="size-1.5 rounded-full bg-current" />
            {meta.label}
          </ToneChip>
        </div>
        <div>
          <p className={cn("text-[12.5px] font-semibold", muted ? "text-muted-foreground" : "text-foreground")}>
            {tool.name}
          </p>
          <p className="hud-label mt-1 text-[9px] text-subtle">{tool.category}</p>
        </div>
        <p className="mt-auto border-t border-hud-soft pt-2 text-[10px] text-muted-foreground">
          {tool.detail}
        </p>
      </Panel>
    );
  }

  return (
    <Panel interactive sheen={false} className={cn("group flex items-center gap-2.5 p-2.5", className)}>
      <span className={cn("grid size-7 shrink-0 place-items-center rounded-md border", toneChip[muted ? "slate" : tool.tone])}>
        <Icon className="size-3.5" strokeWidth={1.9} />
      </span>
      <div className="min-w-0 flex-1">
        <p className={cn("truncate text-[11.5px] font-medium", muted ? "text-muted-foreground" : "text-foreground")}>
          {tool.name}
        </p>
        <p className="truncate text-[9.5px] text-subtle">{tool.category}</p>
      </div>
      <ToneChip tone={meta.tone} className="shrink-0 text-[9.5px]">
        <span className="size-1.5 rounded-full bg-current" />
        {meta.label}
      </ToneChip>
      <ChevronRight className="size-3.5 shrink-0 text-subtle transition-transform duration-220 ease-hud group-hover:translate-x-0.5" strokeWidth={2} />
    </Panel>
  );
};
