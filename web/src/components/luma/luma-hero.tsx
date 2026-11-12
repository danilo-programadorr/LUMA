import { CheckCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { coreIntro } from "@/data/luma-data";
import { useLuma } from "@/luma/luma-context";
import { Panel } from "@/components/luma/panel";
import { LumaOrb } from "@/components/luma/luma-orb";
import { OrbStateSwitch } from "@/components/luma/orb-state-switch";

interface LumaHeroProps {
  className?: string;
  variant?: "dashboard" | "core";
}

/** Hero of the command center: brand statement, CORE orb and capability list. */
export const LumaHero = ({ className, variant = "dashboard" }: LumaHeroProps) => {
  const { state } = useLuma();
  const isCore = variant === "core";

  return (
    <Panel
      variant="spotlight"
      corners
      className={cn("animate-scale-in relative overflow-hidden p-4 sm:p-5", className)}
    >
      <span aria-hidden className="pointer-events-none absolute inset-0 hud-grid-layer opacity-40" />
      <span
        aria-hidden
        className="pointer-events-none absolute -left-32 top-1/2 h-[520px] w-[520px] -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(0,168,255,0.18),rgba(0,168,255,0.05)_52%,transparent_70%)]"
      />
      <span
        aria-hidden
        className="pointer-events-none absolute -right-28 -top-28 h-[440px] w-[440px] rounded-full bg-[radial-gradient(circle,rgba(0,229,255,0.14),rgba(0,229,255,0.04)_50%,transparent_70%)]"
      />

      <div className="relative grid items-center gap-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <div className="order-2 min-w-0 lg:order-1">
          <p className="hud-label text-[9.5px] tracking-[0.34em] text-primary/90">
            {coreIntro.eyebrow}
          </p>
          <h1 className="hud-title mt-2 text-[34px] leading-[0.92] text-foreground text-glow sm:text-[42px] xl:text-[52px]">
            LUMA
            <span className="text-primary"> CORE</span>
          </h1>
          <p className="mt-3.5 max-w-md text-[12px] leading-relaxed text-muted-foreground">
            {coreIntro.description}
          </p>

          <div className="mt-4 flex flex-wrap gap-1.5">
            {coreIntro.chips.map((chip, index) => (
              <span
                key={chip.id}
                className="inline-flex items-center gap-1.5 rounded-full border border-hud-line bg-void/50 px-2.5 py-1 text-[10.5px] text-muted-foreground transition-all duration-150 ease-hud hover:border-primary/60 hover:bg-primary/10 hover:text-primary"
                style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${180 + index * 60}ms both` }}
              >
                <chip.icon className="size-3" strokeWidth={2} />
                {chip.label}
              </span>
            ))}
          </div>

          <OrbStateSwitch className="mt-4 max-w-md rounded-md border border-hud-soft bg-void/40 p-2.5" />
        </div>

        <div className="order-1 flex flex-col items-center gap-3.5 lg:order-2">
          <LumaOrb
            state={state}
            size={isCore ? 400 : 330}
            label="LUMA"
            sublabel="CORE"
            className="mx-auto"
          />

          <div className="w-full max-w-sm rounded-md border border-hud-soft bg-void/30 p-2.5">
            <p className="hud-label text-[9.5px] text-muted-foreground">Capacidades planejadas</p>
            <ul className="mt-2 grid grid-cols-2 gap-x-2.5 gap-y-1.5">
              {coreIntro.highlights.map((highlight, index) => (
                <li
                  key={highlight}
                  className="flex items-center gap-1.5 text-[10.5px] text-foreground/85 transition-colors duration-150 ease-hud hover:text-foreground"
                  style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${220 + index * 70}ms both` }}
                >
                  <CheckCircle2 className="size-3 shrink-0 text-primary" strokeWidth={2.2} />
                  <span className="truncate">{highlight}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </Panel>
  );
};
