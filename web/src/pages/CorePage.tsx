import { runtimeRows, processes, collectionRows } from "@/data/page-data";
import { useEffect } from "react";
import {
  Activity,
  BrainCircuit,
  Cpu,
  Database,
  Layers,
  Sparkles,
  Terminal,
  Waypoints,
} from "lucide-react";

import { agents, coreStats, memoryStats, memoryRecords } from "@/data/luma-data";
import { useLuma } from "@/luma/luma-context";
import { PageHeader } from "@/components/luma/page-header";
import { LumaHero } from "@/components/luma/luma-hero";
import { MetricTile } from "@/components/luma/metric-tile";
import { Gauge, ProgressMeter } from "@/components/luma/gauge";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { ReadoutPanel, type ReadoutRow } from "@/components/luma/readout-panel";
import { FeedPanel } from "@/components/luma/feed-panel";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";
import { MemoryGraph } from "@/components/luma/memory-graph";







const CorePage = () => {
  const { setState } = useLuma();

  useEffect(() => {
    setState("executing");
  }, [setState]);

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow="Núcleo"
        icon={BrainCircuit}
        title="LUMA CORE"
        description="Cérebro visual da orquestradora: runtime, memória, modelos e processos ativos em um só lugar."
        meta={
          <>
            <ToneChip tone="cyan">
              <StatusDot tone="cyan" size="xs" />
              núcleo ativo
            </ToneChip>
            <ToneChip tone="green">
              <StatusDot tone="green" size="xs" />
              control plane saudável
            </ToneChip>
            <ToneChip tone="violet">Planejado</ToneChip>
          </>
        }
      />

      <LumaHero variant="core" />

      <div className="grid gap-3 lg:grid-cols-3">
        {coreStats.slice(0, 3).map((stat, index) => (
          <div
            key={stat.id}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 60}ms both` }}
          >
            <MetricTile
              icon={stat.icon}
              label={stat.label}
              value={stat.value}
              hint={stat.hint}
              tone={stat.tone}
            />
          </div>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.9fr)]">
        <ReadoutPanel
          icon={Terminal}
          title="Runtime e Orquestração"
          hint="Camada de execução"
          rows={runtimeRows}
          columns={1}
        />

        <Panel className="animate-fade-up">
          <PanelHeader
            icon={Cpu}
            title="Processos Ativos"
            hint="4 jobs em pipeline"
            meta={<span className="hud-numeric text-[10px] text-subtle">fila 4</span>}
          />
          <div className="space-y-2.5 p-3.5">
            {processes.map((process, index) => (
              <div key={process.id}>
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <span className="truncate text-[11px] text-foreground/90">{process.name}</span>
                  <span className="hud-label shrink-0 text-[8.5px] text-subtle">{process.state}</span>
                </div>
                <ProgressMeter value={process.progress} tone={process.tone} delay={180 + index * 90} />
              </div>
            ))}
            <div className="mt-3 grid grid-cols-3 gap-2 border-t border-hud-soft pt-3">
              {memoryStats.slice(0, 3).map((stat) => (
                <div key={stat.label} className="text-center">
                  <p className="hud-numeric text-[13px] font-semibold text-foreground">{stat.value}</p>
                  <p className="mt-0.5 text-[9px] text-subtle">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        <Panel className="animate-fade-up">
          <PanelHeader
            icon={Database}
            title="Memória Indexada"
            hint="12.4 GB em 6 coleções"
            meta={<span className="hud-numeric text-[10px] text-primary">48.210 vetores</span>}
          />
          <div className="flex flex-col items-center gap-3 p-3.5">
            <Gauge value={82} label="Uso de contexto" tone="violet" size={128} delay={200} />
            <div className="w-full space-y-2">
              {collectionRows.map((row, index) => (
                <div key={row.id} className="flex items-center gap-2">
                  <span className="hud-label w-20 shrink-0 text-[9px] text-subtle">{row.label}</span>
                  <ProgressMeter value={Number.parseInt(row.value, 10)} tone={row.tone} height="h-1" delay={220 + index * 80} />
                  <span className="hud-numeric w-8 shrink-0 text-right text-[10px] text-muted-foreground">
                    {row.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <MemoryGraph />
        <div className="space-y-3">
          <ReadoutPanel
            icon={Layers}
            title="Memórias Recentes"
            hint="Últimos registros indexados"
            tone="violet"
            rows={memoryRecords.slice(0, 4).map((record) => ({
              id: record.id,
              label: record.title,
              value: `${record.confidence}%`,
              tone: record.tone,
              icon: record.icon,
              hint: `${record.collection} · ${record.tokens} tokens · ${record.indexedAt}`,
            }))}
          />
          <Panel className="animate-fade-up">
            <PanelHeader
              icon={Waypoints}
              title="Agentes Conectados ao Núcleo"
              meta={<span className="hud-numeric text-[10px] text-success">{agents.length} registrados</span>}
            />
            <div className="flex flex-wrap gap-1.5 p-3.5">
              {agents.map((agent) => (
                <ToneChip key={agent.id} tone={agent.tone} className="text-[10px]">
                  <agent.icon className="size-3" strokeWidth={2} />
                  {agent.name}
                </ToneChip>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      <FeedPanel limit={6} />
    </div>
  );
};

export default CorePage;
