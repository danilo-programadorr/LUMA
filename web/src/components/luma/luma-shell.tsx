import { DEMO } from '@/data/mode';
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Outlet, useLocation } from "react-router-dom";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";
import { AppSidebar } from "@/components/luma/app-sidebar";
import { IntelligenceRail } from "@/components/luma/intelligence-rail";
import { TechBackground } from "@/components/luma/tech-background";
import { TopBar } from "@/components/luma/top-bar";
import { VoiceBar } from "@/components/luma/voice-bar";

/** Desktop shell: sidebar · working area · intelligence rail · command bar. */
export const LumaShell = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [railVisible, setRailVisible] = useState(
    () => typeof window !== "undefined" && window.innerWidth >= 1536,
  );
  const mainRef = useRef<HTMLElement | null>(null);
  const drawerRef = useRef<HTMLDivElement | null>(null);
  const { pathname } = useLocation();

  useEffect(() => {
    setDrawerOpen(false);
    mainRef.current?.scrollTo({ top: 0, behavior: "auto" });
  }, [pathname]);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawerOpen(false);
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  useEffect(() => {
    if (!drawerOpen) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const drawer = drawerRef.current;
    const focusable = () => Array.from(drawer?.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input') ?? []);
    focusable()[0]?.focus();
    const trapFocus = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const elements = focusable();
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first?.focus();
      }
    };
    drawer?.addEventListener("keydown", trapFocus);
    return () => {
      drawer?.removeEventListener("keydown", trapFocus);
      previousFocus?.focus();
    };
  }, [drawerOpen]);

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden">
      <TechBackground /><div role="status" className="relative z-20 border-b border-primary/20 bg-void px-3 py-1 text-center text-xs text-primary">{DEMO ? "DEMONSTRAÇÃO — dados fictícios, nenhuma execução real" : "Piloto privado · integrações não conectadas · execução indisponível"}</div>

      <div className="flex min-h-0 flex-1">
        <AppSidebar className="hidden lg:flex" />

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <TopBar
            onOpenSidebar={() => setDrawerOpen(true)}
            onToggleRail={() => setRailVisible((value) => !value)}
            railVisible={railVisible}
          />

          <div className="flex min-h-0 flex-1">
            <main
              ref={mainRef}
              className="relative min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden scroll-smooth"
            >
              <div className="mx-auto w-full max-w-[1560px] p-4 sm:p-6 lg:p-7">
                <Outlet />
              </div>
            </main>

            {railVisible && <IntelligenceRail className="hidden xl:flex" />}          </div>
          <VoiceBar />
        </div>
      </div>

      <AnimatePresence>
        {drawerOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
              onClick={() => setDrawerOpen(false)}
              className="fixed inset-0 z-40 bg-void/80 backdrop-blur-sm lg:hidden"
            />
            <motion.div
              ref={drawerRef}
              role="dialog"
              aria-modal="true"
              aria-label="Menu de módulos"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              className="fixed inset-y-0 left-0 z-50 flex lg:hidden"
            >
              <AppSidebar className="shadow-glow-lg" onNavigate={() => setDrawerOpen(false)} />
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                aria-label="Fechar menu"
                className={cn(
                  "ml-2 mt-3 grid size-8 place-items-center self-start rounded-full border border-hud-line bg-void/80 text-muted-foreground transition-colors duration-150 ease-hud hover:border-primary/50 hover:text-primary",
                )}
              >
                <X className="size-4" strokeWidth={2} />
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

