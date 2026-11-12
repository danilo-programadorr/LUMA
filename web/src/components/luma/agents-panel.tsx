import { ArrowRight, Waypoints } from "lucide-react";

import { cn } from "@/lib/utils";
import { agents } from "@/data/luma-data";
import { Panel, PanelHeader, PanelLink } from "@/components/luma/panel";
import { AgentCard } from "@/components/luma/agent-card";
import { StatusDot } from "@/components/luma/status-indicator";

interface AgentsPanelProps {
  className?: string;
  compact?: boolean;
  limit?: number;
}

export const AgentsPanel = ({ className, compact = true, limit }: AgentsPanelProps) => {
  const list = limit ? agents.slice(0, limit) : agents;
  const online = agents.filter((agent) => agent.status !== "offline").length;

  return (
    <Panel className={cn("animate-fade-up", className)}>
      <PanelHeader
        icon={Waypoints}
        title="Agentes Ativos"
        hint="Papéis orquestrados pela LUMA"
        meta={
          <span className="inline-flex items-center gap-1.5 text-[10px] text-success">
            <StatusDot tone="green" />
            {online} online
          </span>
        }
        action={
          <PanelLink to="/agents">
            Ver todos
            <ArrowRight className="size-3" strokeWidth={2} />
          </PanelLink>
        }
      />
      <div
        className={cn(
          "grid gap-2.5 p-3.5",
          compact ? "grid-cols-1 sm:grid-cols-2 2xl:grid-cols-2" : "grid-cols-1 sm:grid-cols-2 xl:grid-cols-3",
        )}
      >
        {list.map((agent, index) => (
          <div
            key={agent.id}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 45 + 80}ms both` }}
          >
            <AgentCard agent={agent} variant={compact ? "compact" : "grid"} />
          </div>
        ))}
      </div>
    </Panel>
  );
};
