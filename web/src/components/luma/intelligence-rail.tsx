import { ArrowRight, FolderKanban, ShieldQuestion, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";
import { approvals, feedEvents, projects } from "@/data/luma-data";
import { Panel, PanelAction, PanelHeader, PanelLink } from "@/components/luma/panel";
import { FeedFooter, FeedItem, LiveBadge } from "@/components/luma/feed-item";
import { ApprovalCard } from "@/components/luma/approval-card";
import { ProjectMiniCard } from "@/components/luma/project-card";
import { ToneChip } from "@/components/luma/status-indicator";

interface IntelligenceRailProps {
  className?: string;
}

const pending = approvals.filter((approval) => approval.status === "pending");

/** Right rail: live feed, approval queue and active projects. */
export const IntelligenceRail = ({ className }: IntelligenceRailProps) => (
  <aside
    className={cn(
      "flex w-rail shrink-0 flex-col gap-3 overflow-y-auto border-l border-hud-soft bg-void/55 p-3 backdrop-blur-xl",
      className,
    )}
  >
    <Panel corners className="animate-fade-up">
      <PanelHeader
        icon={Sparkles}
        title="Feed Inteligente"
        meta={<LiveBadge />}
        action={
          <PanelLink to="/conversations">
            Ver todos
            <ArrowRight className="size-3" strokeWidth={2} />
          </PanelLink>
        }
      />
      <div className="space-y-0.5 p-2">
        {feedEvents.map((event, index) => (
          <div
            key={event.id}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 60}ms both` }}
          >
            <FeedItem event={event} />
          </div>
        ))}
      </div>
      <FeedFooter />
    </Panel>

    <Panel className="animate-fade-up" style={{ animationDelay: "120ms" }}>
      <PanelHeader
        icon={ShieldQuestion}
        tone="amber"
        title="Fila de Aprovações"
        meta={<ToneChip tone="amber" className="text-[9.5px]">{pending.length} pendentes</ToneChip>}
        action={
          <PanelLink to="/approvals">
            Ver todas
            <ArrowRight className="size-3" strokeWidth={2} />
          </PanelLink>
        }
      />
      <div className="space-y-2 p-2.5">
        {pending.map((approval) => (
          <ApprovalCard key={approval.id} approval={approval} />
        ))}
      </div>
      <div className="border-t border-hud-soft px-3 py-1.5">
        <PanelAction className="w-full justify-center" icon={ArrowRight}>
          Gerenciar aprovações
        </PanelAction>
      </div>
    </Panel>

    <Panel className="animate-fade-up" style={{ animationDelay: "200ms" }}>
      <PanelHeader
        icon={FolderKanban}
        title="Projetos"
        meta={<span className="hud-numeric text-[10px] text-subtle">{projects.length} ativos</span>}
        action={
          <PanelLink to="/projects">
            Ver todos
            <ArrowRight className="size-3" strokeWidth={2} />
          </PanelLink>
        }
      />
      <div className="grid gap-2 p-2.5">
        {projects.map((project) => (
          <ProjectMiniCard key={project.id} project={project} />
        ))}
      </div>
      <div className="border-t border-hud-soft px-3 py-1.5">
        <PanelAction className="w-full justify-center" icon={ArrowRight}>
          Abrir quadro de projetos
        </PanelAction>
      </div>
    </Panel>

    <Panel className="animate-fade-up" style={{ animationDelay: "280ms" }}>
      <PanelHeader icon={ShieldQuestion} tone="green" title="Local Runtime" />
      <div className="grid gap-2 p-3 text-[10.5px]">
        <div className="flex items-center justify-between">
          <span className="text-subtle">Versão do runtime</span>
          <span className="hud-numeric text-foreground/90">v1.4.0</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-subtle">Control Plane</span>
          <span className="text-success">saudável</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-subtle">Fila de execução</span>
          <span className="hud-numeric text-foreground/90">4 jobs</span>
        </div>
        <Link
          to="/devices"
          className="mt-1 inline-flex items-center justify-center gap-1 rounded-md border border-hud-soft px-2 py-1 text-[10px] text-muted-foreground transition-colors duration-150 ease-hud hover:border-primary/50 hover:text-primary"
        >
          Abrir dispositivos
          <ArrowRight className="size-3" strokeWidth={2} />
        </Link>
      </div>
    </Panel>
  </aside>
);
