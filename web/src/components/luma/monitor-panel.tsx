import { DEMO } from '@/data/mode';
import { ArrowDown, ArrowUp, Gauge as GaugeIcon, Activity } from "lucide-react";

import { cn } from "@/lib/utils";
import { systemMonitor } from "@/data/luma-data";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { Gauge } from "@/components/luma/gauge";
import { NetworkSparkline } from "@/components/luma/network-sparkline";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";

interface MonitorPanelProps {
  className?: string;
}

export const MonitorPanel = ({ className }: MonitorPanelProps) => (
  <Panel className={cn("animate-fade-up", className)}>
    <PanelHeader
      icon={GaugeIcon}
      title="Monitor do Sistema"
      hint="PC Principal"
      meta={
        <span className="inline-flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <StatusDot status="offline" />
          Local Runtime
        </span>
      }
      action={
        <span className="hud-numeric text-[10px] text-subtle">
          uptime indisponível
        </span>
      }
    />

    <div className="grid gap-3.5 p-3.5 xl:grid-cols-[minmax(0,auto)_minmax(0,1fr)]">
      <div className="flex items-center justify-center gap-1.5">
        {systemMonitor.gauges.map((gauge, index) => (
          <Gauge
            key={gauge.id}
            value={gauge.value}
            label={gauge.label}
            tone={gauge.tone}
            size={104}
            delay={160 + index * 140}
          />
        ))}
      </div>

      <div className="rounded-md border border-hud-soft bg-void/40 p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1.5">
            <Activity className="size-3.5 text-primary" strokeWidth={2} />
            <span className="hud-label text-[9.5px] text-muted-foreground">Rede</span>
          </span>
          <ToneChip tone="green" className="text-[9.5px]">
            Indisponível
          </ToneChip>
        </div>

        <div className="mt-2.5 grid grid-cols-3 gap-2 text-[10px]">
          <div>
            <p className="flex items-center gap-1 text-subtle">
              <ArrowDown className="size-2.5 text-primary" strokeWidth={2.6} />
              download
            </p>
            <p className="hud-numeric mt-0.5 text-[12.5px] font-semibold text-foreground">
              {DEMO ? systemMonitor.network.download : "—"}
              <span className="text-[9px] text-muted-foreground"> Mbps</span>
            </p>
          </div>
          <div>
            <p className="flex items-center gap-1 text-subtle">
              <ArrowUp className="size-2.5 text-violet" strokeWidth={2.6} />
              upload
            </p>
            <p className="hud-numeric mt-0.5 text-[12.5px] font-semibold text-foreground">
              {DEMO ? systemMonitor.network.upload : "—"}
              <span className="text-[9px] text-muted-foreground"> Mbps</span>
            </p>
          </div>
          <div>
            <p className="text-subtle">latência</p>
            <p className="hud-numeric mt-0.5 text-[12.5px] font-semibold text-foreground">
              {DEMO ? systemMonitor.network.latency : "—"}
              <span className="text-[9px] text-muted-foreground"> ms</span>
            </p>
          </div>
        </div>

        <NetworkSparkline series={systemMonitor.network.series} className="mt-2.5" height={66} />
      </div>
    </div>
  </Panel>
);
