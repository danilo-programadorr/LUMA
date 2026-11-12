import { DEMO } from '@/data/mode';
import { CloudSun, MapPin } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";
import { navItems } from "@/luma/nav";
import { owner } from "@/data/luma-data";
import { LumaBrandMark, LumaWordmark } from "@/components/luma/brand-mark";
import { VoicePanel } from "@/components/luma/voice-panel";

interface AppSidebarProps {
  className?: string;
  onNavigate?: () => void;
}

/** Fixed navigation rail: brand, module list, voice assistant, environment readout. */
export const AppSidebar = ({ className, onNavigate }: AppSidebarProps) => (
  <aside
    className={cn(
      "flex h-full w-sidebar shrink-0 flex-col border-r border-hud-soft bg-void/75 backdrop-blur-xl",
      className,
    )}
  >
    <div className="flex h-frame shrink-0 items-center gap-3 border-b border-hud-soft px-4">
      <LumaBrandMark className="size-10 shrink-0" />
      <LumaWordmark />
    </div>

    <nav aria-label="Módulos da LUMA" className="no-scrollbar min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2.5 py-3">
      {navItems.map((item, index) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          onClick={onNavigate}
          title={item.hint}
          style={{ animation: `luma-slide-right 0.42s cubic-bezier(0.22,1,0.36,1) ${index * 28}ms both` }}
          className={({ isActive }) =>
            cn(
              "group relative flex items-center gap-2.5 rounded-md border border-transparent px-2.5 py-[7px] text-[12px] transition-all duration-150 ease-hud",
              isActive
                ? "border-primary/30 bg-primary/[0.12] text-foreground shadow-glow-xs"
                : "text-muted-foreground hover:border-hud-soft hover:bg-primary/[0.06] hover:text-foreground",
            )
          }
        >
          {({ isActive }) => (
            <>
              <span
                aria-hidden
                className={cn(
                  "absolute inset-y-[6px] left-0 w-[2px] rounded-full transition-opacity duration-220 ease-hud",
                  isActive ? "bg-primary opacity-100 shadow-glow-sm" : "opacity-0 group-hover:opacity-40",
                )}
              />
              <item.icon
                className={cn(
                  "size-[15px] shrink-0 transition-colors duration-150 ease-hud",
                  isActive ? "text-primary" : "text-subtle group-hover:text-primary",
                )}
                strokeWidth={1.9}
              />
              <span className="truncate">{item.label}</span>
              {item.badge !== undefined && (
                <span
                  className={cn(
                    "hud-numeric ml-auto rounded-full border px-1.5 py-px text-[9.5px] leading-none transition-colors duration-150 ease-hud",
                    isActive
                      ? "border-primary/50 bg-primary/15 text-primary"
                      : "border-hud-soft bg-void/60 text-subtle group-hover:border-primary/40 group-hover:text-primary",
                  )}
                >
                  {item.badge}
                </span>
              )}
            </>
          )}
        </NavLink>
      ))}
    </nav>

    <div className="shrink-0 space-y-2 border-t border-hud-soft p-2.5">
      {DEMO ? <VoicePanel/> : <details className="rounded-lg border border-hud-soft bg-void/60 text-xs text-muted-foreground"><summary className="cursor-pointer px-3 py-3">Voz · disponível em fase futura</summary><div className="max-h-[35dvh] overflow-y-auto p-2"><VoicePanel/></div></details>}

      <div className="flex items-center justify-between gap-2 px-1 text-[9.5px] text-subtle">
        <span className="inline-flex items-center gap-1">
          <MapPin className="size-2.5 text-primary/70" strokeWidth={2.2} />
          {owner.location}
        </span>
        <span className="inline-flex items-center gap-1">
          <CloudSun className="size-2.5 text-warning/80" strokeWidth={2.2} />
          {owner.weather}
        </span>
      </div>
    </div>
  </aside>
);
