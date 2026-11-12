import { heartbeats } from "@/data/page-data";
import { useEffect } from "react";
import { Cpu, MonitorSmartphone, Radio, Server, ShieldCheck, Wifi } from "lucide-react";

import { devices } from "@/data/luma-data";
import { useLuma } from "@/luma/luma-context";
import { PageHeader } from "@/components/luma/page-header";
import { DeviceCard } from "@/components/luma/device-card";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { Gauge } from "@/components/luma/gauge";
import { NetworkSparkline } from "@/components/luma/network-sparkline";
import { ReadoutPanel } from "@/components/luma/readout-panel";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";



const DevicesPage = () => {
  const { setState } = useLuma();

  useEffect(() => {
    setState("idle");
  }, [setState]);

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow="Infraestrutura"
        icon={MonitorSmartphone}
        title="Dispositivos"
        description="Máquinas pareadas com a LUMA, capacidades declaradas, heartbeat e acesso remoto. Controle real será conectado em etapa posterior."
        meta={
          <>
            <ToneChip tone="green">
              <StatusDot tone="green" size="xs" />
              Não conectado
            </ToneChip>
            <ToneChip tone="cyan">
              <Cpu className="size-3" strokeWidth={2.2} />
              executor do PC pronto
            </ToneChip>
            <ToneChip tone="slate">
              <Radio className="size-3" strokeWidth={2.2} />
              heartbeat 12 s
            </ToneChip>
          </>
        }
      />

      <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
        {devices.map((device, index) => (
          <div
            key={device.id}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 70}ms both` }}
          >
            <DeviceCard device={device} variant="full" />
          </div>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <Panel className="animate-fade-up">
          <PanelHeader
            icon={Cpu}
            title="Desempenho do PC Principal"
            hint="Windows 11 · Local Runtime v1.4"
            meta={<span className="hud-numeric text-[10px] text-subtle">atualizado agora</span>}
          />
          <div className="grid gap-3.5 p-3.5 sm:grid-cols-[minmax(0,auto)_minmax(0,1fr)]">
            <div className="flex items-center justify-center gap-2">
              <Gauge value={18} label="CPU" tone="cyan" size={104} delay={140} />
              <Gauge value={42} label="RAM" tone="violet" size={104} delay={260} />
              <Gauge value={36} label="DISCO" tone="cyan" size={104} delay={380} />
            </div>
            <div className="rounded-md border border-hud-soft bg-void/40 p-3">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 text-[10px] text-muted-foreground">
                  <Wifi className="size-3 text-primary" strokeWidth={2} />
                  Throughput local
                </span>
                <ToneChip tone="green" className="text-[9.5px]">
                  estável
                </ToneChip>
              </div>
              <NetworkSparkline
                series={[14, 22, 19, 28, 24, 36, 30, 44, 38, 46, 40, 52]}
                className="mt-2.5"
                height={72}
              />
              <p className="hud-numeric mt-2 text-[10px] text-subtle">
                42.6 Mbps download · 8.4 Mbps upload · 12 ms
              </p>
            </div>
          </div>
        </Panel>

        <div className="space-y-3">
          <Panel className="animate-fade-up">
            <PanelHeader icon={Radio} title="Heartbeat" hint="Último sinal de cada dispositivo" tone="green" />
            <div className="space-y-2 p-3.5">
              {heartbeats.map((beat) => (
                <div
                  key={beat.id}
                  className="flex items-center gap-2.5 rounded-md border border-hud-soft bg-void/40 px-2.5 py-2"
                >
                  <StatusDot tone={beat.tone} />
                  <span className="min-w-0 flex-1 truncate text-[11px] text-foreground/90">{beat.device}</span>
                  <span className="hud-numeric text-[10px] text-muted-foreground">{beat.interval}</span>
                  <span className="hud-label text-[8.5px] text-subtle">{beat.status}</span>
                </div>
              ))}
            </div>
          </Panel>

          <ReadoutPanel
            icon={ShieldCheck}
            tone="violet"
            title="Capacidades Declaradas"
            hint="O que cada máquina pode executar"
            rows={devices.flatMap((device) =>
              device.capabilities.slice(0, 2).map((capability, index) => ({
                id: `${device.id}-${index}`,
                label: capability,
                value: device.name,
                tone: device.status === "offline" ? ("slate" as const) : ("cyan" as const),
                icon: Server,
              })),
            )}
          />
        </div>
      </div>
    </div>
  );
};

export default DevicesPage;
