import { ArrowRight, MonitorSmartphone } from "lucide-react";

import { cn } from "@/lib/utils";
import { devices } from "@/data/luma-data";
import { Panel, PanelHeader, PanelLink } from "@/components/luma/panel";
import { DeviceCard } from "@/components/luma/device-card";
import { StatusDot } from "@/components/luma/status-indicator";

interface DevicesPanelProps {
  className?: string;
  variant?: "rail" | "full";
  headline?: string;
}

export const DevicesPanel = ({
  className,
  variant = "rail",
  headline = "Dispositivos",
}: DevicesPanelProps) => (
  <Panel className={cn("animate-fade-up", className)}>
    <PanelHeader
      icon={MonitorSmartphone}
      title={headline}
      hint="Máquinas sob orquestração"
      meta={
        <span className="inline-flex items-center gap-1.5 text-[10px] text-success">
          <StatusDot tone="green" />
          Não conectado
        </span>
      }
      action={
        <PanelLink to="/devices">
          Ver todos
          <ArrowRight className="size-3" strokeWidth={2} />
        </PanelLink>
      }
    />
    <div className="grid gap-2.5 p-3.5">
      {devices.slice(0, 2).map((device, index) => (
        <div
          key={device.id}
          style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 70 + 80}ms both` }}
        >
          <DeviceCard device={device} variant={variant} />
        </div>
      ))}
    </div>
  </Panel>
);
