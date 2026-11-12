import { Battery, Clock, Cpu, MonitorSmartphone, Power, Radio } from "lucide-react";

import { cn } from "@/lib/utils";
import { statusMeta, toneChip } from "@/luma/tokens";
import type { Device, Tone } from "@/luma/types";
import { Panel } from "@/components/luma/panel";
import { SegmentBar } from "@/components/luma/gauge";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";
import { Button } from "@/components/ui/button";

const metricTone: Record<string, Tone> = {
  CPU: "cyan",
  RAM: "violet",
  Disco: "cyan",
  Bateria: "green",
};

interface DeviceCardProps {
  device: Device;
  variant?: "rail" | "full";
  className?: string;
}

export const DeviceCard = ({ device, variant = "rail", className }: DeviceCardProps) => {
  const Icon = device.icon;
  const meta = statusMeta[device.status];

  return (
    <Panel
      interactive
      sheen={false}
      corners={variant === "full"}
      className={cn("p-3", className)}
    >
      <div className="flex items-start gap-3">
        <span className={cn("grid size-9 shrink-0 place-items-center rounded-lg border", toneChip[device.status === "offline" ? "slate" : "cyan"])}>
          <Icon className="size-[18px]" strokeWidth={1.8} />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-[12.5px] font-medium text-foreground">{device.name}</p>
            <span className="inline-flex shrink-0 items-center gap-1.5 text-[10px] text-muted-foreground">
              <StatusDot status={device.status} />
              {meta.label}
            </span>
          </div>
          <p className="mt-0.5 truncate text-[10px] text-subtle">
            {device.platform} · {device.detail}
          </p>
        </div>
      </div>

      <div className="mt-2.5 grid gap-1.5">
        {device.metrics.map((metric) => (
          <div key={metric.label} className="flex items-center gap-2">
            <span className="hud-label w-11 shrink-0 text-[9px] text-subtle">{metric.label}</span>
            <div className="min-w-0 flex-1">
              <SegmentBar value={metric.value} tone={metricTone[metric.label] ?? "cyan"} />
            </div>
            <span className="hud-numeric w-9 shrink-0 text-right text-[10.5px] text-foreground/90">
              {metric.value}%
            </span>
          </div>
        ))}
      </div>

      {variant === "full" && (
        <>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {device.capabilities.map((capability) => (
              <ToneChip key={capability} tone="slate" className="text-[9.5px]">
                {capability}
              </ToneChip>
            ))}
            {device.battery !== undefined && (
              <ToneChip tone="green" className="text-[9.5px]">
                <Battery className="size-2.5" strokeWidth={2} />
                {device.battery}%
              </ToneChip>
            )}
          </div>

          <div className="mt-3 flex items-center gap-2 border-t border-hud-soft pt-2.5">
            <span className="inline-flex items-center gap-1 text-[9.5px] text-subtle">
              <Clock className="size-2.5" strokeWidth={2.2} />
              {device.lastSeen}
            </span>
            <span className="inline-flex items-center gap-1 text-[9.5px] text-subtle">
              <Radio className="size-2.5" strokeWidth={2.2} />
              heartbeat indisponível
            </span>
            <div className="ml-auto flex gap-1.5">
              <Button size="sm" variant="subtle">
                <MonitorSmartphone className="size-3" strokeWidth={2.2} />
                Detalhes
              </Button>
              <Button size="sm" variant="outline" disabled={device.status === "offline"}>
                <Power className="size-3" strokeWidth={2.2} />
                Acessar
              </Button>
            </div>
          </div>
        </>
      )}

      {variant === "rail" && (
        <div className="mt-2.5 flex items-center gap-2 border-t border-hud-soft pt-2 text-[9.5px] text-subtle">
          <span className="inline-flex items-center gap-1">
            <Cpu className="size-2.5" strokeWidth={2.2} />
            Executor pronto
          </span>
          <span className="ml-auto hud-numeric">{device.lastSeen}</span>
        </div>
      )}
    </Panel>
  );
};
