import { useAuth } from '@/auth/context';
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bell,
  ChevronDown,
  Command,
  Focus,
  LogOut,
  Menu,
  PanelRight,
  Search,
  Settings,
  SlidersHorizontal,
  UserCircle,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { headerShortcuts, owner, systemStatus } from "@/data/luma-data";
import { toneChip, toneText } from "@/luma/tokens";
import type { Tone } from "@/luma/types";
import { Button } from "@/components/ui/button";
import { StatusDot } from "@/components/luma/status-indicator";

const useClock = () => {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const interval = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(interval);
  }, []);
  return now;
};

const capitalize = (value: string) => value.charAt(0).toUpperCase() + value.slice(1);

const profileMenu = [
  { id: "profile", label: "Meu perfil", icon: UserCircle },
  { id: "prefs", label: "Preferências", icon: SlidersHorizontal },
  { id: "focus", label: "Modo Foco", icon: Focus },
  { id: "settings", label: "Configurações", icon: Settings },
  { id: "exit", label: "Encerrar sessão", icon: LogOut },
];

interface TopBarProps {
  onOpenSidebar: () => void;
  onToggleRail: () => void;
  railVisible: boolean;
  className?: string;
}

export const TopBar = ({
  onOpenSidebar,
  onToggleRail,
  railVisible,
  className,
}: TopBarProps) => {
  const auth = useAuth();
  const now = useClock();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  const hours = now.toLocaleTimeString("pt-BR", { hour: "2-digit", hour12: false });
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  const date = capitalize(
    now.toLocaleDateString("pt-BR", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    }),
  );

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <header
      className={cn(
        "relative z-30 flex h-frame shrink-0 items-center gap-3 border-b border-hud-soft bg-void/70 px-2.5 backdrop-blur-xl sm:px-4",
        className,
      )}
    >
      <Button
        variant="ghost"
        size="icon-sm"
        className="lg:hidden"
        onClick={onOpenSidebar}
        aria-label="Abrir menu de módulos"
      >
        <Menu className="size-4" strokeWidth={2} />
      </Button>

      <div className="min-w-0 shrink-0">
        <p className="truncate text-[10px] text-muted-foreground sm:text-[10.5px]">{date}</p>
        <p className="hud-numeric flex items-baseline text-[20px] font-semibold leading-none text-foreground sm:text-[26px]">
          <span>{hours}</span>
          <span className="animate-blink text-primary">:</span>
          <span>{minutes}</span>
          <span className="animate-blink text-primary">:</span>
          <span className="text-[14px] text-muted-foreground sm:text-[18px]">{seconds}</span>
        </p>
      </div>

      <div className="ml-2 hidden min-w-0 items-center gap-2 2xl:flex">
        {systemStatus.map((item, index) => (
          <div
            key={item.id}
            className="flex items-center gap-2 rounded-md border border-hud-soft bg-hud-surface px-2.5 py-1.5 transition-colors duration-220 ease-hud hover:border-primary/45"
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 70 + 120}ms both` }}
          >
            <span className={cn("grid size-6 place-items-center rounded-full border", toneChip[item.tone as Tone])}>
              <item.icon className="size-3" strokeWidth={2} />
            </span>
            <span className="leading-tight">
              <span className="hud-label block text-[8px] text-subtle">{item.label}</span>
              <span className={cn("block text-[11px] font-medium", toneText[item.tone as Tone])}>
                {item.id === "system" && auth.health === "AVAILABLE" ? "Disponível" : item.value}
              </span>
            </span>
          </div>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-1.5">
        <label
          className="group hidden h-9 w-[220px] cursor-text items-center gap-2 rounded-md border border-hud-soft bg-hud-surface px-2.5 transition-colors duration-220 ease-hud focus-within:border-primary/60 hover:border-primary/45 xl:flex"
        >
          <Search className="size-3.5 shrink-0 text-subtle group-focus-within:text-primary" strokeWidth={2} />
          <input
            aria-label="Buscar em tudo"
            placeholder="Buscar em tudo..."
            className="min-w-0 flex-1 bg-transparent text-[11.5px] text-foreground outline-none placeholder:text-subtle"
          />
          <span className="inline-flex shrink-0 items-center gap-0.5 rounded border border-hud-soft bg-void/60 px-1 py-0.5 text-[9px] text-subtle">
            <Command className="size-2.5" strokeWidth={2.4} />K
          </span>
        </label>

        <Button variant="ghost" size="icon-sm" className="xl:hidden" aria-label="Buscar em tudo">
          <Search className="size-4" strokeWidth={2} />
        </Button>

        <Button
          variant="ghost"
          size="icon-sm"
          className="hidden sm:inline-flex"
          aria-label="Alternar painel de inteligência"
          aria-pressed={railVisible}
          onClick={onToggleRail}
        >
          <PanelRight className={cn("size-4", railVisible && "text-primary")} strokeWidth={2} />
        </Button>

        {headerShortcuts.map((shortcut) => (
          <Button key={shortcut.id} variant="ghost" size="icon-sm" className="relative hidden sm:inline-flex" aria-label={shortcut.label}>
            <shortcut.icon className="size-4" strokeWidth={2} />
            {shortcut.badge ? (
              <span className="absolute -right-0.5 -top-0.5 grid size-4 place-items-center rounded-full border border-void bg-destructive text-[8.5px] font-semibold text-destructive-foreground animate-pulse-dot">
                {shortcut.badge}
              </span>
            ) : null}
          </Button>
        ))}

        <div ref={menuRef} className="relative">
          <button
            type="button"
            onClick={() => setMenuOpen((value) => !value)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            className="flex items-center gap-2 rounded-md border border-transparent px-1.5 py-1 transition-colors duration-150 ease-hud hover:border-hud-soft hover:bg-primary/[0.07]"
          >
            <span className="relative grid size-9 shrink-0 place-items-center rounded-full border border-primary/45 bg-[linear-gradient(140deg,rgba(0,229,255,0.22),rgba(22,139,255,0.28))] text-[12px] font-semibold text-foreground">
              {owner.initials}
              <StatusDot tone="green" size="xs" className="absolute -bottom-0 -right-0 ring-2 ring-void" />
            </span>
            <span className="hidden text-left leading-tight lg:block">
              <span className="block text-[11.5px] font-medium text-foreground">{owner.name}</span>
              <span className="block text-[9.5px] text-subtle">{owner.role}</span>
            </span>
            <ChevronDown
              className={cn(
                "hidden size-3.5 text-subtle transition-transform duration-220 ease-hud lg:block",
                menuOpen && "rotate-180",
              )}
              strokeWidth={2}
            />
          </button>

          <AnimatePresence>
            {menuOpen && (
              <motion.div
                role="menu"
                initial={{ opacity: 0, y: -8, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -6, scale: 0.98 }}
                transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
                className="hud-panel absolute right-0 top-[calc(100%+8px)] z-50 w-56 p-1.5"
              >
                <div className="flex items-center gap-2 rounded-md border border-hud-soft bg-void/50 px-2 py-1.5">
                  <span className="grid size-7 place-items-center rounded-full border border-primary/40 bg-primary/10 text-[10px] font-semibold text-primary">
                    {owner.initials}
                  </span>
                  <span className="leading-tight">
                    <span className="block text-[11px] font-medium text-foreground">{owner.name}</span>
                    <span className="block text-[9px] text-subtle">{owner.tier}</span>
                  </span>
                </div>
                <div className="my-1.5 h-px bg-hud-soft" />
                {profileMenu.map((entry) => (
                  <button
                    key={entry.id}
                    type="button"
                    role="menuitem"
                    onClick={() => { setMenuOpen(false); if (entry.id === "exit") void auth.logout(); }}
                    className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-[11.5px] text-muted-foreground transition-colors duration-150 ease-hud hover:bg-primary/10 hover:text-primary"
                  >
                    <entry.icon className="size-3.5" strokeWidth={2} />
                    {entry.label}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
};
