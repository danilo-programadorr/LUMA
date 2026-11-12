import { ArrowRight, CalendarClock } from "lucide-react";

import { cn } from "@/lib/utils";
import { timelineEvents } from "@/data/luma-data";
import { Panel, PanelHeader, PanelLink } from "@/components/luma/panel";
import { DayTimeline, TimelineNow } from "@/components/luma/day-timeline";

interface TimelinePanelProps {
  className?: string;
}

export const TimelinePanel = ({ className }: TimelinePanelProps) => (
  <Panel className={cn("animate-fade-up", className)}>
    <PanelHeader
      icon={CalendarClock}
      title="Linha do Tempo — Hoje"
      hint="5 eventos programados"
      meta={<TimelineNow />}
      action={
        <PanelLink to="/calendar">
          Ver calendário
          <ArrowRight className="size-3" strokeWidth={2} />
        </PanelLink>
      }
    />
    <div className="p-2.5">
      <DayTimeline events={timelineEvents} />
    </div>
  </Panel>
);
