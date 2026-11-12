import { Activity, Users2, ListChecks, ArrowUpRight } from "lucide-react";

import { cn } from "@/lib/utils";
import { toneChip, toneText } from "@/luma/tokens";
import type { Project } from "@/luma/types";
import { Panel } from "@/components/luma/panel";
import { ProgressMeter } from "@/components/luma/gauge";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";

interface ProjectCardProps {
  project: Project;
  className?: string;
}

export const ProjectCard = ({ project, className }: ProjectCardProps) => {
  const Icon = project.icon;
  const done = project.status === "Em andamento";

  return (
    <Panel interactive sheen className={cn("group flex flex-col gap-3 p-3.5", className)}>
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "grid size-9 shrink-0 place-items-center rounded-lg border transition-shadow duration-220 ease-hud group-hover:shadow-glow-sm",
            toneChip[project.tone],
          )}
        >
          <Icon className="size-[18px]" strokeWidth={1.8} />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-[13.5px] font-semibold text-foreground">{project.name}</p>
            <ArrowUpRight
              className="size-3.5 shrink-0 text-subtle transition-transform duration-220 ease-hud group-hover:-translate-y-0.5 group-hover:text-primary"
              strokeWidth={2}
            />
          </div>
          <p className="mt-0.5 line-clamp-1 text-[10.5px] text-muted-foreground">
            {project.description}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        <ToneChip tone={done ? "cyan" : "slate"}>
          <StatusDot tone={done ? "cyan" : "slate"} pulse={done} size="xs" />
          {project.status}
        </ToneChip>
        <ToneChip tone="slate">
          <ListChecks className="size-2.5" strokeWidth={2.2} />
          {project.tasks} tarefas
        </ToneChip>
        <ToneChip tone="slate">
          <Users2 className="size-2.5" strokeWidth={2.2} />
          {project.agents} agentes
        </ToneChip>
      </div>

      <div>
        <div className="mb-1.5 flex items-center justify-between text-[10px]">
          <span className="text-subtle">Progresso</span>
          <span className={cn("hud-numeric font-semibold", toneText[project.tone])}>
            {project.progress}%
          </span>
        </div>
        <ProgressMeter value={project.progress} tone={project.tone} />
      </div>

      <div className="flex items-center justify-between border-t border-hud-soft pt-2 text-[10px] text-subtle">
        <span className="inline-flex items-center gap-1.5">
          <Activity className="size-3" strokeWidth={2} />
          Última atividade
        </span>
        <span className="hud-numeric">{project.updated}</span>
      </div>
    </Panel>
  );
};

interface ProjectMiniCardProps {
  project: Project;
  className?: string;
}

/** Condensed project tile used inside the intelligence rail. */
export const ProjectMiniCard = ({ project, className }: ProjectMiniCardProps) => {
  const Icon = project.icon;

  return (
    <Panel interactive sheen={false} className={cn("group p-2.5", className)}>
      <div className="flex items-center gap-2.5">
        <span
          className={cn(
            "grid size-7 shrink-0 place-items-center rounded-md border",
            toneChip[project.tone],
          )}
        >
          <Icon className="size-3.5" strokeWidth={1.9} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[11.5px] font-medium text-foreground">{project.name}</p>
          <p className="flex items-center gap-1 text-[9.5px] text-subtle">
            <StatusDot tone={project.status === "Em andamento" ? "cyan" : "slate"} size="xs" />
            {project.status}
          </p>
        </div>
        <span className={cn("hud-numeric text-[11px] font-semibold", toneText[project.tone])}>
          {project.progress}%
        </span>
      </div>

      <div className="mt-2">
        <ProgressMeter value={project.progress} tone={project.tone} height="h-1" delay={280} />
      </div>

      <div className="mt-2 flex items-center gap-2.5 text-[9.5px] text-subtle">
        <span className="inline-flex items-center gap-1">
          <ListChecks className="size-2.5" strokeWidth={2.2} />
          {project.tasks} tarefas
        </span>
        <span className="inline-flex items-center gap-1">
          <Users2 className="size-2.5" strokeWidth={2.2} />
          {project.agents} agentes
        </span>
      </div>
    </Panel>
  );
};
