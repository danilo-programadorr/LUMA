import { ArrowRight, Wrench } from "lucide-react";

import { cn } from "@/lib/utils";
import { tools } from "@/data/luma-data";
import { Panel, PanelHeader, PanelLink } from "@/components/luma/panel";
import { ToolStatusCard } from "@/components/luma/tool-status-card";

interface ToolsPanelProps {
  className?: string;
  limit?: number;
}

export const ToolsPanel = ({ className, limit }: ToolsPanelProps) => {
  const list = limit ? tools.slice(0, limit) : tools;

  return (
    <Panel className={cn("animate-fade-up", className)}>
      <PanelHeader
        icon={Wrench}
        title="Status dos Modelos e Ferramentas"
        hint="Integrações e modelos"
        meta={
          <span className="hud-numeric text-[10px] text-subtle">
            3 conectadas · 2 planejadas
          </span>
        }
        action={
          <PanelLink to="/tools">
            Ver todas
            <ArrowRight className="size-3" strokeWidth={2} />
          </PanelLink>
        }
      />
      <div className="grid gap-2 p-3.5 sm:grid-cols-2">
        {list.map((tool, index) => (
          <div
            key={tool.id}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 45 + 80}ms both` }}
          >
            <ToolStatusCard tool={tool} />
          </div>
        ))}
      </div>
    </Panel>
  );
};
