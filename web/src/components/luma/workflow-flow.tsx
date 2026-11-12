import { Fragment, type ElementType } from "react";

import { cn } from "@/lib/utils";
import { toneChip, toneColor, toneText } from "@/luma/tokens";
import type { Tone, WorkflowStage } from "@/luma/types";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { Workflow } from "lucide-react";

const stateStyle: Record<WorkflowStage["state"], { label: string; tone: Tone; ring: string }> = {
  done: { label: "Concluído", tone: "green", ring: "border-success/40" },
  active: { label: "Executando", tone: "cyan", ring: "border-primary/70 shadow-glow" },
  gate: { label: "Gate de aprovação", tone: "amber", ring: "border-warning/55" },
  queued: { label: "Na fila", tone: "slate", ring: "border-hud-line border-dashed" },
};

const Connector = ({ tone }: { tone: Tone }) => (
  <div aria-hidden className="flex items-center justify-center py-1 lg:w-9 lg:py-0">
    <svg viewBox="0 0 40 12" className="h-3 w-10 rotate-90 lg:rotate-0" preserveAspectRatio="none">
      <line x1="0" y1="6" x2="32" y2="6" stroke={toneColor(tone, 0.4)} strokeWidth="1" strokeDasharray="3 4" />
      <polygon points="32,2 40,6 32,10" fill={toneColor(tone, 0.75)} />
    </svg>
  </div>
);

interface WorkflowFlowProps {
  stages: WorkflowStage[];
  className?: string;
}

/** Visual orchestration pipeline — presentation only, no execution engine. */
export const WorkflowFlow = ({ stages, className }: WorkflowFlowProps) => (
  <Panel corners className={cn("animate-fade-up", className)}>
    <PanelHeader
      icon={Workflow}
      title="Fluxo de Orquestração"
      hint="Do pedido do proprietário até a execução"
      meta={<span className="hud-numeric text-[10px] text-subtle">{stages.length} nós</span>}
    />
    <div className="flex flex-col items-stretch p-3.5 lg:flex-row lg:items-stretch">
      {stages.map((stage, index) => {
        const style = stateStyle[stage.state];
        return (
          <Fragment key={stage.id}>
            <div
              className={cn(
                "group relative min-w-0 flex-1 rounded-lg border bg-hud-surface p-2.5 transition-all duration-220 ease-hud hover:-translate-y-0.5",
                style.ring,
              )}
              style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 70}ms both` }}
            >
              <div className="flex items-center gap-2">
                <span className={cn("grid size-7 shrink-0 place-items-center rounded-md border", toneChip[stage.tone])}>
                  <stage.icon className="size-3.5" strokeWidth={1.9} />
                </span>
                <div className="min-w-0">
                  <p className="text-[11.5px] font-semibold leading-tight text-foreground">{stage.title}</p>
                  <p className="hud-label mt-0.5 text-[8.5px] leading-tight text-subtle">{style.label}</p>
                </div>
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">{stage.subtitle}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {stage.outputs.map((output) => (
                  <span
                    key={output}
                    className={cn("hud-numeric rounded border px-1.5 py-px text-[9px]", toneChip[stage.tone])}
                  >
                    {output}
                  </span>
                ))}
              </div>
            </div>
            {index < stages.length - 1 && <Connector tone={stage.tone} />}          </Fragment>
        );
      })}
    </div>
  </Panel>
);

interface WorkflowTemplatesProps {
  templates: { id: string; name: string; nodes: number; tone: Tone; icon: ElementType; runs: number }[];
  className?: string;
}

export const WorkflowTemplates = ({ templates, className }: WorkflowTemplatesProps) => (
  <div className={cn("grid gap-2.5 sm:grid-cols-2", className)}>
    {templates.map((template, index) => (
      <Panel
        key={template.id}
        interactive
        sheen={false}
        className="group flex items-center gap-2.5 p-2.5"
        style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 60}ms both` }}
      >
        <span className={cn("grid size-8 shrink-0 place-items-center rounded-md border", toneChip[template.tone])}>
          <template.icon className="size-4" strokeWidth={1.8} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[11.5px] font-medium text-foreground">{template.name}</p>
          <p className="hud-numeric text-[9.5px] text-subtle">
            {template.nodes} nós · {template.runs} execuções
          </p>
        </div>
        <span className={cn("hud-numeric shrink-0 text-[10px]", toneText[template.tone])}>
          {template.runs}x
        </span>
      </Panel>
    ))}
  </div>
);
