import { cn } from "@/lib/utils";
import { toneChip, toneColor } from "@/luma/tokens";
import type { TimelineEvent, Tone } from "@/luma/types";

const nodeTone: Record<Tone, string> = {
  cyan: "bg-primary text-primary",
  blue: "bg-accent text-accent",
  violet: "bg-violet text-violet",
  green: "bg-success text-success",
  amber: "bg-warning text-warning",
  red: "bg-destructive text-destructive",
  slate: "bg-subtle text-subtle",
};

interface DayTimelineProps {
  events: TimelineEvent[];
  className?: string;
}

export const DayTimeline = ({ events, className }: DayTimelineProps) => (
  <ol className={cn("relative space-y-0.5 pl-1", className)}>
    <span
      aria-hidden
      className="absolute bottom-3 left-[7.4rem] top-3 w-px bg-[linear-gradient(180deg,transparent,var(--hud-line-strong),transparent)] sm:left-[4.4rem]"
    />

    {events.map((event, index) => (
      <li
        key={event.id}
        className={cn(
          "group relative flex items-start gap-3 rounded-md px-2 py-2 transition-colors duration-220 ease-hud hover:bg-primary/[0.05]",
          event.active && "bg-primary/[0.06]",
        )}
        style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 70}ms both` }}
      >
        <span className="hud-numeric w-10 shrink-0 pt-0.5 text-[10.5px] text-muted-foreground sm:text-[11px]">
          {event.time}
        </span>

        <span className="relative z-10 mt-1 flex size-3 shrink-0 items-center justify-center">
          <span
            className={cn(
              "size-2 rounded-full ring-4 ring-void/70",
              nodeTone[event.tone],
              event.active && "animate-pulse-dot",
            )}
          />
        </span>

        <div className="min-w-0 flex-1">
          <p
            className={cn(
              "truncate text-[11.5px] font-medium",
              event.active ? "text-foreground" : "text-foreground/85",
            )}
          >
            {event.title}
          </p>
          <div className="mt-0.5 flex items-center gap-2 text-[10px] text-subtle">
            <span className={cn("truncate", event.active && "text-primary")}>{event.meta}</span>
            {event.project && (
              <span className="hud-label shrink-0 rounded-sm border border-hud-soft bg-void/50 px-1.5 py-px text-[8.5px]">
                {event.project}
              </span>
            )}
          </div>
        </div>

        <span
          aria-hidden
          className="mt-1 size-1.5 shrink-0 rounded-full opacity-0 transition-opacity duration-220 ease-hud group-hover:opacity-100"
          style={{ backgroundColor: toneColor(event.tone, 0.9) }}
        />
      </li>
    ))}
  </ol>
);

interface TimelineNowProps {
  label?: string;
  tone?: Tone;
  className?: string;
}

export const TimelineNow = ({ label = "Agora · 11:28", tone = "cyan", className }: TimelineNowProps) => (
  <div
    className={cn(
      "sticky top-0 z-10 flex items-center gap-2 rounded-md border px-2.5 py-1 backdrop-blur-md",
      toneChip[tone],
      className,
    )}
  >
    <span className="size-1.5 animate-pulse-dot rounded-full bg-current" />
    <span className="hud-label text-[9.5px]">{label}</span>
  </div>
);

