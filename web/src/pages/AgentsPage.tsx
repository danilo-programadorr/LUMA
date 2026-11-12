import { useEffect } from "react";
import { Crown, Plus, ShieldCheck, Users, Waypoints } from "lucide-react";

import { agents } from "@/data/luma-data";
import { useLuma } from "@/luma/luma-context";
import { PageHeader } from "@/components/luma/page-header";
import { AgentCard } from "@/components/luma/agent-card";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { ProgressMeter } from "@/components/luma/gauge";
import { ReadoutPanel } from "@/components/luma/readout-panel";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";
import { Button } from "@/components/ui/button";
import { toneText } from "@/luma/tokens";

const load = (completed: number, open: number) =>
  Math.round((completed / (completed + open)) * 100);

const AgentsPage = () => {
  const { setState } = useLuma();

  useEffect(() => {
    setState("executing");
  }, [setState]);

  const root = agents.find((agent) => agent.root);
  const totalCompleted = agents.reduce((total, agent) => total + agent.completed, 0);

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow="Orquestração"
        icon={Waypoints}
        title="Agentes"
        description="Nove papéis especializados operando sob a coordenação permanente da LUMA, com contexto compartilhado e escopo de aprovação."
        meta={
          <>
            <ToneChip tone="green">
              <StatusDot tone="green" size="xs" />
              {agents.filter(a => a.status === "online").length} online
            </ToneChip>
            <ToneChip tone="cyan">
              <Crown className="size-3" strokeWidth={2.2} />
              LUMA orquestradora
            </ToneChip>
            <ToneChip tone="violet">
              <ShieldCheck className="size-3" strokeWidth={2.2} />
              {totalCompleted} entregas
            </ToneChip>
          </>
        }
        actions={
          <Button variant="outline" size="sm">
            <Plus className="size-3" strokeWidth={2.4} />
            Convidar agente
          </Button>
        }
      />

      {root && (
        <Panel variant="spotlight" corners className="animate-fade-up p-3.5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <span className="grid size-12 shrink-0 place-items-center rounded-xl border border-primary/45 bg-primary/12 text-primary shadow-glow-sm">
              <root.icon className="size-6" strokeWidth={1.7} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="hud-title text-[17px] text-foreground">{root.name}</p>
                <ToneChip tone="cyan" className="text-[9.5px] tracking-[0.16em]">
                  {root.role}
                </ToneChip>
              </div>
              <p className="mt-1 max-w-2xl text-[11.5px] leading-relaxed text-muted-foreground">
                {root.description}
              </p>
            </div>
            <div className="grid shrink-0 grid-cols-3 gap-3 text-center sm:gap-4">
              <div>
                <p className="hud-numeric text-[15px] font-semibold text-primary">{root.openTasks}</p>
                <p className="text-[9px] text-subtle">em aberto</p>
              </div>
              <div>
                <p className="hud-numeric text-[15px] font-semibold text-foreground">{root.completed}</p>
                <p className="text-[9px] text-subtle">concluídas</p>
              </div>
              <div>
                <p className="hud-numeric text-[15px] font-semibold text-foreground">{root.uptime}</p>
                <p className="text-[9px] text-subtle">uptime</p>
              </div>
            </div>
          </div>
        </Panel>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {agents.map((agent, index) => (
          <div
            key={agent.id}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 45}ms both` }}
          >
            <AgentCard agent={agent} />
          </div>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <Panel className="animate-fade-up">
          <PanelHeader
            icon={Users}
            title="Distribuição de Carga"
            hint="Entregas concluídas por agente"
            meta={<span className="hud-numeric text-[10px] text-subtle">{totalCompleted} no total</span>}
          />
          <div className="space-y-2.5 p-3.5">
            {agents.map((agent, index) => {
              const percentage = load(agent.completed, agent.openTasks);
              return (
                <div key={agent.id}>
                  <div className="mb-1.5 flex items-center justify-between gap-2 text-[10.5px]">
                    <span className="inline-flex items-center gap-1.5 text-foreground/90">
                      <agent.icon className={toneText[agent.tone]} style={{ width: 12, height: 12 }} strokeWidth={2.2} />
                      {agent.name}
                    </span>
                    <span className="hud-numeric text-muted-foreground">
                      {agent.completed} / {agent.completed + agent.openTasks}
                    </span>
                  </div>
                  <ProgressMeter
                    value={percentage}
                    tone={agent.tone}
                    height="h-1"
                    delay={160 + index * 70}
                  />
                </div>
              );
            })}
          </div>
        </Panel>

        <ReadoutPanel
          icon={ShieldCheck}
          tone="violet"
          title="Governança dos Papéis"
          hint="Escopo e estado de cada agente"
          rows={agents.map((agent) => ({
            id: agent.id,
            label: agent.name,
            value: agent.status === "waiting" ? "aguardando" : "operando",
            tone: agent.status === "waiting" ? "amber" : agent.tone,
            icon: agent.icon,
            hint: agent.role,
          }))}
        />
      </div>
    </div>
  );
};

export default AgentsPage;
