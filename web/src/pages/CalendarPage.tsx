import { useEffect } from "react";
import { CalendarClock, CalendarDays, Clock, MapPin, Video } from "lucide-react";

import { calendarEvents, calendarWeek } from "@/data/luma-data";
import type { TimelineEvent } from "@/luma/types";
import { useLuma } from "@/luma/luma-context";
import { PageHeader } from "@/components/luma/page-header";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { DayTimeline, TimelineNow } from "@/components/luma/day-timeline";
import { ReadoutPanel } from "@/components/luma/readout-panel";
import { ProgressMeter } from "@/components/luma/gauge";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";
import { cn } from "@/lib/utils";

const agenda: TimelineEvent[] = calendarEvents.map((event) => ({
  id: event.id,
  time: event.time,
  title: event.title,
  meta: `${event.kind} · ${event.time} – ${event.end}`,
  project: event.project,
  tone: event.tone,
  active: event.kind === "execução" && event.time === "10:00",
}));

const CalendarPage = () => {
  const { setState } = useLuma();

  useEffect(() => {
    setState("idle");
  }, [setState]);

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow="Agenda"
        icon={CalendarDays}
        title="Calendário"
        description="Leitura visual da agenda do dia, blocos de execução dos agentes e carga da semana. Integração real chega em etapa posterior."
        meta={
          <>
            <ToneChip tone="cyan">
              <Clock className="size-3" strokeWidth={2.2} />
              {calendarEvents.length} eventos hoje
            </ToneChip>
            <ToneChip tone="violet">
              <Video className="size-3" strokeWidth={2.2} />
              2 reuniões
            </ToneChip>
            <ToneChip tone="green">
              <MapPin className="size-3" strokeWidth={2.2} />
              São Paulo, SP
            </ToneChip>
          </>
        }
      />

      <Panel corners className="animate-fade-up">
        <PanelHeader
          icon={CalendarDays}
          title="Semana Atual"
          hint="Junho de 2026"
          meta={<span className="hud-numeric text-[10px] text-subtle">carga média 49%</span>}
        />
        <div className="grid grid-cols-2 gap-2.5 p-3.5 sm:grid-cols-4 xl:grid-cols-7">
          {calendarWeek.map((day, index) => (
            <div
              key={day.day}
              className={cn(
                "rounded-lg border p-2.5 transition-all duration-220 ease-hud hover:-translate-y-0.5",
                day.today
                  ? "border-primary/60 bg-primary/12 shadow-glow-sm"
                  : "border-hud-soft bg-void/40 hover:border-primary/40",
              )}
              style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 50}ms both` }}
            >
              <div className="flex items-center justify-between">
                <span className="hud-label text-[9px] text-muted-foreground">{day.day}</span>
                {day.today && <StatusDot status="executing" size="xs" />}
              </div>
              <p
                className={cn(
                  "hud-numeric mt-1 text-[19px] font-semibold leading-none",
                  day.today ? "text-primary" : "text-foreground",
                )}
              >
                {day.date}
              </p>
              <div className="mt-2">
                <ProgressMeter value={day.load} tone={day.today ? "cyan" : "blue"} height="h-1" delay={200 + index * 60} />
              </div>
              <p className="hud-numeric mt-1 text-[9px] text-subtle">{day.load}% ocupado</p>
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <Panel className="animate-fade-up">
          <PanelHeader
            icon={CalendarClock}
            title="Agenda do Dia"
            hint="Sábado, 24 de Outubro"
            meta={<TimelineNow />}
          />
          <div className="p-2.5">
            <DayTimeline events={agenda} />
          </div>
        </Panel>

        <div className="space-y-3">
          <ReadoutPanel
            icon={Clock}
            title="Próximos Blocos"
            hint="Sequência de execução"
            rows={calendarEvents.slice(1, 5).map((event) => ({
              id: event.id,
              label: event.title,
              value: `${event.time}–${event.end}`,
              tone: event.tone,
              hint: `${event.kind} · ${event.project}`,
            }))}
          />

          <Panel className="animate-fade-up">
            <PanelHeader
              icon={Video}
              title="Reuniões e Reservas"
              hint="Blocos colaborativos"
              tone="violet"
            />
            <div className="space-y-2.5 p-3.5">
              {[
                { id: "m1", name: "Daily de alinhamento", time: "09:00 · 30 min", people: 4 },
                { id: "m2", name: "Planejamento de crescimento", time: "14:00 · 1 h", people: 3 },
                { id: "m3", name: "Revisão de segurança", time: "16:30 · 45 min", people: 2 },
              ].map((meeting) => (
                <div
                  key={meeting.id}
                  className="flex items-center gap-2.5 rounded-md border border-hud-soft bg-void/40 px-2.5 py-2"
                >
                  <span className="grid size-7 place-items-center rounded-md border border-violet/40 bg-violet/10 text-violet">
                    <Video className="size-3.5" strokeWidth={1.9} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[11.5px] text-foreground">{meeting.name}</p>
                    <p className="hud-numeric text-[9.5px] text-subtle">{meeting.time}</p>
                  </div>
                  <span className="hud-numeric shrink-0 text-[10px] text-muted-foreground">
                    {meeting.people} pessoas
                  </span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

export default CalendarPage;
