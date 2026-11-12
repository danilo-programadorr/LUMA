import { Orbit, Radio } from "lucide-react";

import { cn } from "@/lib/utils";
import { coreStats } from "@/data/luma-data";
import { Panel, PanelHeader, PanelLink } from "@/components/luma/panel";
import { MetricTile } from "@/components/luma/metric-tile";
import { StatusDot } from "@/components/luma/status-indicator";

interface CoreVisionPanelProps {
  className?: string;
}

export const CoreVisionPanel = ({ className }: CoreVisionPanelProps) => (
  <Panel className={cn("animate-fade-up", className)}>
    <PanelHeader
      icon={Orbit}
      title="Visão do Núcleo"
      hint="Estado consolidado da orquestradora"
      meta={
        <span className="inline-flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <StatusDot status="offline" />
          Local Runtime
        </span>
      }
      action={
        <PanelLink to="/core">
          <Radio className="size-3" strokeWidth={2.2} />
          Núcleo
        </PanelLink>
      }
    />
    <div className="grid grid-cols-1 gap-2.5 p-3.5 sm:grid-cols-2">
      {coreStats.map((stat, index) => (
        <div
          key={stat.id}
          style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 60 + 80}ms both` }}
        >
          <MetricTile
            icon={stat.icon}
            label={stat.label}
            value={stat.value}
            hint={stat.hint}
            tone={stat.tone}
            status={index === 0 ? "offline" : undefined}
          />
        </div>
      ))}
    </div>
  </Panel>
);
