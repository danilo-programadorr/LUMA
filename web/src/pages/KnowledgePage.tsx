import {DEMO} from '@/data/mode';
import {PrivateLibraryPanel} from '@/components/luma/private-library-panel';
import { queue, categories } from "@/data/page-data";
import { useEffect } from "react";
import { BookOpen, FileSearch, Library, Search, Sparkles, Upload } from "lucide-react";

import { knowledgeSources } from "@/data/luma-data";
import { toolStatusMeta, toneChip, toneText } from "@/luma/tokens";
import { useLuma } from "@/luma/luma-context";
import { PageHeader } from "@/components/luma/page-header";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { ProgressMeter } from "@/components/luma/gauge";
import { ReadoutPanel } from "@/components/luma/readout-panel";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";





const DemoKnowledgePage = () => {
  const { setState } = useLuma();

  useEffect(() => {
    setState("thinking");
  }, [setState]);

  const totalDocuments = knowledgeSources.reduce((total, source) => total + source.documents, 0);

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow="Base de conhecimento"
        icon={Library}
        title="Conhecimento"
        description="Fontes, documentos e status de indexação usados pela LUMA para fundamentar decisões. Fontes planejadas ainda não estão conectadas."
        meta={
          <>
            <ToneChip tone="cyan">
              <BookOpen className="size-3" strokeWidth={2.2} />
              {knowledgeSources.length} fontes
            </ToneChip>
            <ToneChip tone="violet">
              <FileSearch className="size-3" strokeWidth={2.2} />
              {totalDocuments} documentos
            </ToneChip>
            <ToneChip tone="green">
              <StatusDot tone="green" size="xs" />
              indexação ativa
            </ToneChip>
          </>
        }
        actions={
          <Button variant="outline" size="sm">
            <Upload className="size-3" strokeWidth={2.2} />
            Adicionar fonte
          </Button>
        }
      />

      <Panel className="animate-fade-up p-3">
        <label className="flex items-center gap-2.5 rounded-lg border border-hud-soft bg-void/50 px-3 py-2.5 transition-colors duration-220 ease-hud focus-within:border-primary/60 hover:border-primary/40">
          <Search className="size-4 shrink-0 text-subtle" strokeWidth={2} />
          <input
            aria-label="Buscar no conhecimento"
            placeholder="Buscar documentos, fontes ou trechos indexados..."
            className="min-w-0 flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-subtle"
          />
          <ToneChip tone="slate" className="hidden text-[9.5px] sm:inline-flex">
            busca semântica
          </ToneChip>
        </label>
      </Panel>

      <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
        {knowledgeSources.map((source, index) => {
          const meta = toolStatusMeta[source.status];
          const active = source.status !== "planned";
          return (
            <Panel
              key={source.id}
              interactive
              sheen={false}
              className="group flex flex-col gap-2.5 p-3"
              style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 60}ms both` }}
            >
              <div className="flex items-start justify-between gap-2">
                <span className={cn("grid size-9 place-items-center rounded-lg border", toneChip[active ? source.tone : "slate"])}>
                  <source.icon className="size-[18px]" strokeWidth={1.8} />
                </span>
                <ToneChip tone={meta.tone} className="text-[9.5px]">
                  <span className="size-1.5 rounded-full bg-current" />
                  {meta.label}
                </ToneChip>
              </div>

              <div>
                <p className={cn("text-[12.5px] font-semibold", active ? "text-foreground" : "text-muted-foreground")}>
                  {source.name}
                </p>
                <p className="hud-label mt-1 text-[9px] text-subtle">
                  {source.kind} · {source.documents} documentos
                </p>
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between text-[10px]">
                  <span className="text-subtle">Indexado</span>
                  <span className={cn("hud-numeric font-semibold", toneText[active ? source.tone : "slate"])}>
                    {source.indexed}%
                  </span>
                </div>
                <ProgressMeter
                  value={source.indexed}
                  tone={active ? source.tone : "slate"}
                  height="h-1"
                  delay={200 + index * 70}
                />
              </div>

              <p className="mt-auto border-t border-hud-soft pt-2 text-[9.5px] text-subtle">
                Atualizado {source.updated}
              </p>
            </Panel>
          );
        })}
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <ReadoutPanel
          icon={Sparkles}
          title="Categorias Indexadas"
          hint="Distribuição por domínio"
          tone="violet"
          columns={2}
          rows={categories.map((category) => ({
            id: category.id,
            label: category.name,
            value: category.value,
            tone: category.tone,
          }))}
        />

        <Panel className="animate-fade-up">
          <PanelHeader
            icon={FileSearch}
            title="Fila de Indexação"
            hint="Documentos processados recentemente"
            meta={<span className="hud-numeric text-[10px] text-subtle">4 itens</span>}
          />
          <ul className="space-y-2 p-3.5">
            {queue.map((item) => (
              <li
                key={item.id}
                className="flex items-center gap-2.5 rounded-md border border-hud-soft bg-void/40 px-2.5 py-2"
              >
                <StatusDot tone={item.tone} />
                <span className="hud-numeric min-w-0 flex-1 truncate text-[10.5px] text-foreground/90">
                  {item.name}
                </span>
                <span className="hud-numeric shrink-0 text-[9.5px] text-subtle">{item.size}</span>
                <span className="hud-label shrink-0 text-[8.5px] text-muted-foreground">{item.state}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
};

const KnowledgePage=()=>DEMO?<DemoKnowledgePage/>:<div className="space-y-6"><PageHeader eyebrow="Fontes e documentos" icon={Library} title="Conhecimento" description="Biblioteca privada local, separada do conhecimento oficial dos projetos e da pesquisa na internet."/><PrivateLibraryPanel/></div>;

export default KnowledgePage;
