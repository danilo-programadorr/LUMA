import { collections } from "@/data/page-data";
import { useEffect } from "react";
import { Database, FileStack, Layers, Radar, Sparkles } from "lucide-react";

import { memoryRecords, memoryStats } from "@/data/luma-data";
import { toneChip, toneColor, toneText } from "@/luma/tokens";
import { useLuma } from "@/luma/luma-context";
import { PageHeader } from "@/components/luma/page-header";
import { MetricTile } from "@/components/luma/metric-tile";
import { MemoryGraph } from "@/components/luma/memory-graph";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { ReadoutPanel } from "@/components/luma/readout-panel";
import { ProgressMeter } from "@/components/luma/gauge";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";



const MemoryPage = () => {
  const { setState } = useLuma();

  useEffect(() => {
    setState("thinking");
  }, [setState]);

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow="Contexto"
        icon={Radar}
        tone="violet"
        title="Memória"
        description="Visão do contexto indexado pela LUMA: coleções, conexões semânticas e registros mais recentes. Memória real será conectada posteriormente."
        meta={
          <>
            <ToneChip tone="violet">
              <Database className="size-3" strokeWidth={2.2} />
              12.4 GB indexados
            </ToneChip>
            <ToneChip tone="cyan">
              <Layers className="size-3" strokeWidth={2.2} />
              6 coleções
            </ToneChip>
            <ToneChip tone="green">
              <Sparkles className="size-3" strokeWidth={2.2} />
              94% de precisão média
            </ToneChip>
          </>
        }
        actions={
          <Button variant="outline" size="sm">
            <FileStack className="size-3" strokeWidth={2.2} />
            Indexar documento
          </Button>
        }
      />

      <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
        {memoryStats.map((stat, index) => (
          <div
            key={stat.label}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 55}ms both` }}
          >
            <MetricTile icon={stat.icon} label={stat.label} value={stat.value} tone={stat.tone} hint="ciclo atual" />
          </div>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <MemoryGraph />

        <div className="space-y-3">
          <Panel className="animate-fade-up">
            <PanelHeader
              icon={Layers}
              title="Coleções"
              hint="Distribuição do contexto"
              tone="violet"
              meta={<span className="hud-numeric text-[10px] text-subtle">908 documentos</span>}
            />
            <div className="space-y-2.5 p-3.5">
              {collections.map((collection, index) => (
                <div key={collection.id}>
                  <div className="mb-1.5 flex items-center justify-between gap-2 text-[10.5px]">
                    <span className="inline-flex items-center gap-1.5 text-foreground/90">
                      <span
                      className="size-1.5 rounded-full"
                      style={{ backgroundColor: toneColor(collection.tone, 0.9) }}
                    />
                      {collection.name}
                    </span>
                    <span className="hud-numeric text-muted-foreground">
                      {collection.documents} docs · {collection.weight}%
                    </span>
                  </div>
                  <ProgressMeter value={collection.weight * 2} tone={collection.tone} height="h-1" delay={160 + index * 70} />
                </div>
              ))}
            </div>
          </Panel>

          <ReadoutPanel
            icon={Database}
            title="Índice Técnico"
            hint="Parâmetros de armazenamento"
            rows={[
              { id: "i1", label: "Modelo de embeddings", value: "text-004", tone: "cyan" },
              { id: "i2", label: "Dimensionalidade", value: "1536", tone: "cyan" },
              { id: "i3", label: "Última compactação", value: "há 4 h", tone: "green" },
              { id: "i4", label: "Política de retenção", value: "permanente", tone: "violet" },
            ]}
          />
        </div>
      </div>

      <Panel className="animate-fade-up">
        <PanelHeader
          icon={FileStack}
          title="Memórias Recentes"
          hint="Registros indexados nos últimos ciclos"
          meta={
            <span className="inline-flex items-center gap-1.5 text-[10px] text-success">
              <StatusDot tone="green" />
              indexação ativa
            </span>
          }
        />
        <div className="grid gap-2.5 p-3.5 lg:grid-cols-2">
          {memoryRecords.map((record, index) => (
            <Panel
              key={record.id}
              interactive
              sheen={false}
              className="group flex items-start gap-3 p-2.5"
              style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 55}ms both` }}
            >
              <span className={cn("grid size-8 shrink-0 place-items-center rounded-md border", toneChip[record.tone])}>
                <record.icon className="size-4" strokeWidth={1.8} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[11.5px] font-medium text-foreground">{record.title}</p>
                <p className="hud-numeric mt-0.5 truncate text-[9.5px] text-subtle">
                  {record.source} · {record.tokens} tokens · {record.indexedAt}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <ToneChip tone={record.tone} className="text-[9px]">
                    {record.collection}
                  </ToneChip>
                  <ProgressMeter value={record.confidence} tone={record.tone} height="h-1" delay={220 + index * 60} />
                  <span className={cn("hud-numeric shrink-0 text-[10px]", toneText[record.tone])}>
                    {record.confidence}%
                  </span>
                </div>
              </div>
            </Panel>
          ))}
        </div>
      </Panel>
    </div>
  );
};

export default MemoryPage;
