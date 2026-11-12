import { DEMO } from '@/data/mode';
import { cn } from "@/lib/utils";
import { orbStateMeta, toneChip } from "@/luma/tokens";
import type { LumaState } from "@/luma/types";
import { useLuma } from "@/luma/luma-context";

const demoStates: LumaState[] = ["idle", "listening", "thinking", "executing", "waiting", "error"];

interface OrbStateSwitchProps {
  className?: string;
  label?: string;
}

/** Internal demo control: lets the interface showcase every orb state. */
export const OrbStateSwitch = ({ className, label = "Estado da LUMA" }: OrbStateSwitchProps) => {
  const { state, setState } = useLuma();

  return (
    <div className={cn("", className)}>
      <div className="flex items-center gap-2">
        <span className="hud-label text-[9px] text-subtle">{label}</span>
        <span className="h-px flex-1 bg-hud-soft" />
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        {demoStates.map((candidate) => {
          const meta = orbStateMeta[candidate];
          const active = candidate === state;
          return (
            <button
              key={candidate}
              type="button"
              disabled={!DEMO} onClick={() => setState(candidate)}
              aria-pressed={active}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2 py-[3px] text-[9.5px] font-medium transition-all duration-150 ease-hud",
                active
                  ? cn(toneChip[meta.tone], "shadow-glow-xs")
                  : "border-hud-soft bg-void/40 text-subtle hover:border-primary/40 hover:text-primary",
              )}
            >
              <span
                className={cn(
                  "size-1.5 rounded-full bg-current",
                  active && "animate-pulse-dot",
                )}
              />
              {meta.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};
