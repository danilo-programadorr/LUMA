import { useEffect } from "react";
import { AppWindow, GitBranch, ShieldQuestion, Workflow } from "lucide-react";

import { workflowStages, workflowTemplates } from "@/data/luma-data";
import { useLuma } from "@/luma/luma-context";
import { PageHeader, SectionHeading } from "@/components/luma/page-header";
import { WorkflowFlow, WorkflowTemplates } from "@/components/luma/workflow-flow";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { ReadoutPanel } from "@/components/luma/readout-panel";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";

const nodeRows = workflowStages.map((stage) => ({
  id: stage.id,
  label: stage.title,
  value:
    stage.state === "done"
      ? "concluído"
      : stage.state === "active"
        ? "executando"
        : stage.state === "gate"
          ? "aguardando aprovação"
          : "na fila",
  tone:
    stage.state === "done"
      ? ("green" as const)
      : stage.state === "active"
        ? ("cyan" as const)
        : stage.state === "gate"
          ? ("amber" as const)
          : ("slate" as const),
  icon: stage.icon,
  hint: stage.subtitle,
}));

const WorkflowsPage = () => {
  const { setState } = useLuma();

  useEffect(() => {
    setState("executing");
  }, [setState]);

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow="Orquestração visual"
        icon={AppWindow}
        title="Fluxos"
        description="Como a LUMA encadeia pedido do proprietário, papéis de agente, gates de aprovação e execução final no dispositivo."
        meta={
          <>
            <ToneChip tone="cyan">
              <Workflow className="size-3" strokeWidth={2.2} />
              {workflowStages.length} nós no fluxo
            </ToneChip>
            <ToneChip tone="amber">
              <ShieldQuestion className="size-3" strokeWidth={2.2} />
              2 gates de aprovação
            </ToneChip>
            <ToneChip tone="green">
              <StatusDot tone="green" size="xs" />
              executor pronto
            </ToneChip>
          </>
        }
      />

      <WorkflowFlow stages={workflowStages} />

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <div>
          <SectionHeading icon={GitBranch} title="Fluxos Salvos" hint="Templates reutilizáveis" />
          <WorkflowTemplates templates={workflowTemplates} />
        </div>

        <ReadoutPanel
          icon={ShieldQuestion}
          tone="violet"
          title="Estado dos Nós"
          hint="Cada etapa do pipeline"
          rows={nodeRows}
        />
      </div>

      <Panel className="animate-fade-up">
        <PanelHeader
          icon={Workflow}
          title="Regras de Orquestração"
          hint="Como o pipeline decide, pausa e executa"
          meta={<span className="hud-numeric text-[10px] text-subtle">v1.4</span>}
        />
        <div className="grid gap-2.5 p-3.5 sm:grid-cols-2 xl:grid-cols-4">
          {[
            {
              id: "r1",
              title: "Roteamento por papel",
              description: "Cada tarefa é enviada ao agente especializado do papel correspondente.",
            },
            {
              id: "r2",
              title: "Pausa em gate sensível",
              description: "Ações sensíveis interrompem o fluxo até autorização explícita.",
            },
            {
              id: "r3",
              title: "Contexto compartilhado",
              description: "Todo nó recebe o mesmo contexto unificado e o histórico da decisão.",
            },
            {
              id: "r4",
              title: "Execução local",
              description: "O executor do PC Principal aplica a mudança aprovada no ambiente real.",
            },
          ].map((rule, index) => (
            <Panel
              key={rule.id}
              sheen={false}
              className="p-3"
              style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 60}ms both` }}
            >
              <p className="text-[11.5px] font-medium text-foreground">{rule.title}</p>
              <p className="mt-1.5 text-[10.5px] leading-relaxed text-muted-foreground">{rule.description}</p>
            </Panel>
          ))}
        </div>
      </Panel>
    </div>
  );
};

export default WorkflowsPage;
