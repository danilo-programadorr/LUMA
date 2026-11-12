import { ChevronRight, Crown } from "lucide-react";

import { cn } from "@/lib/utils";
import { statusMeta, toneChip, toneText } from "@/luma/tokens";
import type { Agent } from "@/luma/types";
import { Panel } from "@/components/luma/panel";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";

interface AgentCardProps {
  agent: Agent;
  variant?: "grid" | "row" | "compact";
  className?: string;
}

export const AgentCard = ({ agent, variant = "grid", className }: AgentCardProps) => {
  const Icon = agent.icon;
  const meta = statusMeta[agent.status];

  if (variant === "compact") {
    return (
      <Panel
        interactive
        sheen={false}
        corners={agent.root}
        variant={agent.root ? "spotlight" : "default"}
        className={cn("group flex items-center gap-2.5 p-2.5", className)}
      >
        <span
          className={cn(
            "grid size-8 shrink-0 place-items-center rounded-md border transition-shadow duration-220 ease-hud group-hover:shadow-glow-sm",
            toneChip[agent.tone],
          )}
        >
          <Icon className="size-4" strokeWidth={1.8} />
        </span>
        <div className="min-w-0 flex-1">
          <p className={cn("truncate text-[11.5px] font-medium", agent.root ? toneText[agent.tone] : "text-foreground")}>
            {agent.name}
          </p>
          <p className="flex items-center gap-1.5 truncate text-[9.5px] text-subtle">
            <StatusDot status={agent.status} size="xs" />
            {meta.label}
          </p>
        </div>
        <span className="hud-numeric shrink-0 text-[10px] text-subtle">{agent.openTasks}</span>
      </Panel>
    );
  }

  if (variant === "row") {
    return (
      <Panel
        interactive
        sheen={false}
        className={cn("flex items-center gap-3 p-2.5", className)}
      >
        <span
          className={cn(
            "grid size-8 shrink-0 place-items-center rounded-md border",
            toneChip[agent.tone],
          )}
        >
          <Icon className="size-4" strokeWidth={1.8} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-[12px] font-medium text-foreground">{agent.name}</p>
            {agent.root && <Crown className="size-3 text-primary" strokeWidth={2} />}
          </div>
          <p className="truncate text-[10px] text-subtle">{agent.role}</p>
        </div>
        <StatusDot status={agent.status} />
        <ChevronRight className="size-3.5 text-subtle" strokeWidth={2} />
      </Panel>
    );
  }

  return (
    <Panel
      interactive
      corners={agent.root}
      variant={agent.root ? "spotlight" : "default"}
      className={cn("group flex flex-col gap-2.5 p-3", className)}
    >
      <div className="flex items-start justify-between gap-2">
        <span
          className={cn(
            "grid size-9 place-items-center rounded-lg border transition-shadow duration-220 ease-hud group-hover:shadow-glow-sm",
            toneChip[agent.tone],
          )}
        >
          <Icon className="size-[18px]" strokeWidth={1.7} />
        </span>
        <span className="inline-flex items-center gap-1.5 text-[10px] font-medium text-muted-foreground">
          <StatusDot status={agent.status} />
          {meta.label}
        </span>
      </div>

      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <p className={cn("truncate text-[13px] font-semibold", agent.root ? toneText[agent.tone] : "text-foreground")}>
            {agent.name}
          </p>
          {agent.root && (
            <ToneChip tone="cyan" className="px-1.5 py-0 text-[9px] tracking-[0.14em]">
              <Crown className="size-2.5" strokeWidth={2.2} />
              ROOT
            </ToneChip>
          )}
        </div>
        <p className="hud-label mt-1 text-[9px] text-subtle">{agent.role}</p>
      </div>

      <p className="line-clamp-2 text-[10.5px] leading-relaxed text-muted-foreground">
        {agent.description}
      </p>

      <div className="mt-auto flex items-center justify-between gap-2 border-t border-hud-soft pt-2 text-[10px] text-subtle">
        <span className="truncate">{agent.project}</span>
        <span className="hud-numeric shrink-0">
          <span className={toneText[agent.tone]}>{agent.openTasks}</span> abertas · {agent.completed}
        </span>
      </div>
    </Panel>
  );
};
