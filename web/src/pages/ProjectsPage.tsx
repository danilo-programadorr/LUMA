import { useEffect } from "react";
import {
  CalendarClock,
  FolderKanban,
  ListChecks,
  Plus,
  TrendingUp,
  Users,
} from "lucide-react";

import { projects, tasks, timelineEvents } from "@/data/luma-data";
import { taskStateMeta, toneText } from "@/luma/tokens";
import { useLuma } from "@/luma/luma-context";
import { PageHeader } from "@/components/luma/page-header";
import { ProjectCard } from "@/components/luma/project-card";
import { MetricTile } from "@/components/luma/metric-tile";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { ReadoutPanel } from "@/components/luma/readout-panel";
import { DayTimeline } from "@/components/luma/day-timeline";
import { ProgressMeter } from "@/components/luma/gauge";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";
import { Button } from "@/components/ui/button";

const ProjectsPage = () => {
  const { setState } = useLuma();

  useEffect(() => {
    setState("idle");
  }, [setState]);

  const openTasks = tasks.filter((task) => task.state !== "completed").length;
  const average = Math.round(
    projects.reduce((total, project) => total + project.progress, 0) / projects.length,
  );

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow="Portfólio"
        icon={FolderKanban}
        title="Projetos"
        description="Iniciativas ativas com progresso, agentes alocados e última atividade registrada pela orquestradora."
        meta={
          <>
            <ToneChip tone="cyan">
              <StatusDot tone="cyan" size="xs" />
              {projects.length} projetos
            </ToneChip>
            <ToneChip tone="slate">
              <ListChecks className="size-3" strokeWidth={2.2} />
              {openTasks} tarefas abertas
            </ToneChip>
            <ToneChip tone="green">
              <TrendingUp className="size-3" strokeWidth={2.2} />
              {average}% progresso médio
            </ToneChip>
          </>
        }
        actions={
          <Button variant="default" size="sm">
            <Plus className="size-3" strokeWidth={2.4} />
            Novo projeto
          </Button>
        }
      />

      <div className="grid gap-3 xl:grid-cols-3">
        {projects.map((project, index) => (
          <div
            key={project.id}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 70}ms both` }}
          >
            <ProjectCard project={project} />
          </div>
        ))}
      </div>

      <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { id: "s1", icon: FolderKanban, label: "Projetos ativos", value: String(projects.length), hint: "todos em execução", tone: "cyan" as const },
          { id: "s2", icon: ListChecks, label: "Tarefas abertas", value: String(openTasks), hint: "no backlog atual", tone: "violet" as const },
          { id: "s3", icon: Users, label: "Agentes alocados", value: "16", hint: "compartilhados", tone: "blue" as const },
          { id: "s4", icon: TrendingUp, label: "Progresso médio", value: `${average}%`, hint: "portfólio completo", tone: "green" as const },
        ].map((stat, index) => (
          <div
            key={stat.id}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 50}ms both` }}
          >
            <MetricTile icon={stat.icon} label={stat.label} value={stat.value} hint={stat.hint} tone={stat.tone} />
          </div>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <Panel className="animate-fade-up">
          <PanelHeader
            icon={ListChecks}
            title="Backlog por Projeto"
            hint="Estado atual das tarefas"
            meta={<span className="hud-numeric text-[10px] text-subtle">{tasks.length} itens</span>}
          />
          <div className="grid gap-2.5 p-3.5 sm:grid-cols-2">
            {projects.map((project) => {
              const projectTasks = tasks.filter((task) => task.project === project.name);
              const distributed = projectTasks.filter((task) => task.state === "completed").length;
              return (
                <div key={project.id} className="rounded-md border border-hud-soft bg-void/40 p-2.5">
                  <div className="flex items-center gap-2">
                    <span className={toneText[project.tone]}>
                      <project.icon style={{ width: 14, height: 14 }} strokeWidth={2} />
                    </span>
                    <p className="truncate text-[11.5px] font-medium text-foreground">{project.name}</p>
                    <span className="hud-numeric ml-auto text-[10px] text-subtle">
                      {distributed}/{projectTasks.length || project.tasks}
                    </span>
                  </div>
                  <div className="mt-2 space-y-1.5">
                    {projectTasks.slice(0, 3).map((task) => (
                      <div key={task.id} className="flex items-center gap-2">
                        <span className="truncate text-[10px] text-muted-foreground">{task.title}</span>
                        <span className={`hud-label ml-auto shrink-0 text-[8px] ${toneText[taskStateMeta[task.state].tone]}`}>
                          {taskStateMeta[task.state].label}
                        </span>
                      </div>
                    ))}
                    {!projectTasks.length && (
                      <p className="text-[10px] text-subtle">Sem tarefas registradas neste ciclo.</p>
                    )}
                  </div>
                  <div className="mt-2">
                    <ProgressMeter value={project.progress} tone={project.tone} height="h-1" delay={200} />
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>

        <div className="space-y-3">
          <Panel className="animate-fade-up">
            <PanelHeader
              icon={CalendarClock}
              title="Marcos de Hoje"
              hint="Cronograma consolidado"
              meta={<span className="hud-numeric text-[10px] text-subtle">{timelineEvents.length} marcos</span>}
            />
            <div className="p-2.5">
              <DayTimeline events={timelineEvents} />
            </div>
          </Panel>

          <ReadoutPanel
            icon={Users}
            tone="violet"
            title="Equipes Alocadas"
            hint="Agentes por projeto"
            rows={projects.map((project) => ({
              id: project.id,
              label: project.name,
              value: `${project.agents} agentes`,
              tone: project.tone,
              icon: project.icon,
              hint: `${project.tasks} tarefas · ${project.status}`,
            }))}
          />
        </div>
      </div>
    </div>
  );
};

export default ProjectsPage;
