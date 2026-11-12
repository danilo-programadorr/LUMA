import { quotaRows } from "@/data/page-data";
import { useEffect } from "react";
import { Globe, HardDrive, Plug, ShieldCheck, Sparkles, SquareTerminal, Wrench } from "lucide-react";

import { tools } from "@/data/luma-data";
import { toolStatusMeta } from "@/luma/tokens";
import { useLuma } from "@/luma/luma-context";
import { PageHeader } from "@/components/luma/page-header";
import { ToolStatusCard } from "@/components/luma/tool-status-card";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { ReadoutPanel } from "@/components/luma/readout-panel";
import { ProgressMeter } from "@/components/luma/gauge";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";



const ToolsPage = () => {
  const { setState } = useLuma();

  useEffect(() => {
    setState("executing");
  }, [setState]);

  const connected = tools.filter((tool) => tool.status === "connected").length;
  const planned = tools.filter((tool) => tool.status === "planned").length;
  const disabled = tools.filter((tool) => tool.status === "disabled").length;

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow="Integrações"
        icon={Wrench}
        title="Ferramentas"
        description="Modelos de linguagem, orquestração de agentes, execução local e automações disponíveis para a LUMA. Integrações planejadas não estão conectadas."
        meta={
          <>
            <ToneChip tone="green">
              <Plug className="size-3" strokeWidth={2.2} />
              {connected} conectadas
            </ToneChip>
            <ToneChip tone="slate">
              <ShieldCheck className="size-3" strokeWidth={2.2} />
              {planned} planejadas
            </ToneChip>
            <ToneChip tone="red">
              <ShieldCheck className="size-3" strokeWidth={2.2} />
              {disabled} desabilitada
            </ToneChip>
          </>
        }
      />

      <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
        {tools.map((tool, index) => (
          <div
            key={tool.id}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 55}ms both` }}
          >
            <ToolStatusCard tool={tool} variant="tile" />
          </div>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <Panel className="animate-fade-up">
          <PanelHeader
            icon={Sparkles}
            title="Consumo e Quotas"
            hint="Uso do ciclo atual"
            meta={<span className="hud-numeric text-[10px] text-subtle">renova em 6 h</span>}
          />
          <div className="space-y-3 p-3.5">
            {quotaRows.map((row, index) => (
              <div key={row.id}>
                <div className="mb-1.5 flex items-center justify-between gap-2 text-[10.5px]">
                  <span className="text-foreground/90">{row.label}</span>
                  <span className="hud-numeric text-muted-foreground">{row.value}%</span>
                </div>
                <ProgressMeter value={row.value} tone={row.tone} height="h-1" delay={180 + index * 90} />
                <p className="mt-1 text-[9.5px] text-subtle">{row.hint}</p>
              </div>
            ))}
          </div>
        </Panel>

        <div className="space-y-3">
          <ReadoutPanel
            icon={SquareTerminal}
            title="Detalhes das Integrações"
            hint="Estado técnico declarado"
            rows={tools.map((tool) => ({
              id: tool.id,
              label: tool.name,
              value: toolStatusMeta[tool.status].label,
              tone: toolStatusMeta[tool.status].tone,
              icon: tool.icon,
              hint: tool.detail,
            }))}
          />

          <Panel className="animate-fade-up">
            <PanelHeader icon={HardDrive} title="Fontes Locais" hint="Recursos acessíveis" tone="green" />
            <div className="grid gap-2 p-3.5 sm:grid-cols-2">
              {[
                { id: "l1", name: "Workspace principal", value: "1.4 GB", icon: HardDrive },
                { id: "l2", name: "Repositórios Git", value: "6 repos", icon: SquareTerminal },
                { id: "l3", name: "Navegador automatizado", value: "desabilitado", icon: Globe },
                { id: "l4", name: "Cache de modelos", value: "820 MB", icon: Sparkles },
              ].map((resource) => (
                <div
                  key={resource.id}
                  className="flex items-center gap-2 rounded-md border border-hud-soft bg-void/40 px-2.5 py-2"
                >
                  <span className="grid size-7 place-items-center rounded-md border border-hud-soft bg-void/60 text-muted-foreground">
                    <resource.icon className="size-3.5" strokeWidth={1.9} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[11px] text-foreground/90">{resource.name}</p>
                    <p className="hud-numeric text-[9.5px] text-subtle">{resource.value}</p>
                  </div>
                  <StatusDot tone={resource.value === "desabilitado" ? "slate" : "green"} size="xs" />
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

export default ToolsPage;
