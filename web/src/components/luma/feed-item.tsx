import { cn } from "@/lib/utils";
import { severityMeta, toneChip } from "@/luma/tokens";
import type { FeedEvent } from "@/luma/types";
import { PanelAction } from "@/components/luma/panel";

interface FeedItemProps {
  event: FeedEvent;
  className?: string;
  showAccent?: boolean;
}

export const FeedItem = ({ event, className, showAccent = true }: FeedItemProps) => {
  const Icon = event.icon;
  const tone = severityMeta[event.severity].tone;

  return (
    <div
      className={cn(
        "group relative flex gap-2.5 rounded-md border border-transparent px-2 py-2 transition-all duration-220 ease-hud hover:border-hud-line hover:bg-primary/[0.05]",
        className,
      )}
    >
      {showAccent && (
        <span
          aria-hidden
          className={cn(
            "absolute inset-y-2 left-0 w-[2px] rounded-full opacity-40 transition-opacity duration-220 ease-hud group-hover:opacity-90",
            toneChip[tone].split(" ")[0],
          )}
        />
      )}

      <span className="hud-numeric w-9 shrink-0 pt-0.5 text-[10px] text-subtle">{event.time}</span>

      <span className={cn("mt-0.5 grid size-6 shrink-0 place-items-center rounded-md border", toneChip[tone])}>
        <Icon className="size-3" strokeWidth={2} />
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="text-[11.5px] font-medium leading-snug text-foreground/95">
            {event.title}
          </p>
          {event.tag && (
            <span className="hud-label shrink-0 rounded border border-hud-soft bg-void/60 px-1.5 py-0.5 text-[8.5px] text-subtle">
              {event.tag}
            </span>
          )}
        </div>
        <p className="mt-0.5 truncate text-[10px] text-muted-foreground">{event.detail}</p>
      </div>
    </div>
  );
};

interface LiveBadgeProps {
  label?: string;
  className?: string;
}

export const LiveBadge = ({ label = "AO VIVO", className }: LiveBadgeProps) => (
  <span
    className={cn(
      "inline-flex items-center gap-1.5 rounded-full border border-success/40 bg-success/10 px-2 py-0.5 text-[9.5px] font-semibold tracking-[0.12em] text-success",
      className,
    )}
  >
    <span className="relative flex size-1.5">
      <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-70" />
      <span className="relative inline-flex size-1.5 rounded-full bg-success" />
    </span>
    {label}
  </span>
);

interface FeedFooterProps {
  label?: string;
}

export const FeedFooter = ({ label = "Ver todo o feed" }: FeedFooterProps) => (
  <div className="border-t border-hud-soft px-3 py-1.5">
    <PanelAction className="w-full justify-center">{label}</PanelAction>
  </div>
);
