import { DEMO } from '@/data/mode';
import { ResearchPanel } from './research-panel';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Command, MonitorDot, ShieldCheck } from "lucide-react";

import { cn } from "@/lib/utils";
import { useLuma } from "@/luma/luma-context";
import { CommandInput } from "@/components/luma/command-input";
import { StatusDot } from "@/components/luma/status-indicator";
import { Button } from "@/components/ui/button";

interface VoiceBarProps {
  className?: string;
}

/** Bottom command bar — always reachable, including on mobile. */
export const VoiceBar = ({ className }: VoiceBarProps) => {
  const { state, pulse, lastCommand } = useLuma();

  if (!DEMO) return <footer className={cn("shrink-0 border-t border-hud-soft bg-void/95 px-4 py-3 sm:px-6", className)}>
    <div className="mx-auto flex max-w-[1504px] items-center justify-between gap-4">
      <p className="text-xs text-muted-foreground"><span className="mr-2 inline-block size-1.5 rounded-full bg-primary"/>Pesquisa pública<span className="hidden sm:inline"> · escolha o computador antes de começar</span></p>
      <Dialog><DialogTrigger asChild><Button variant="outline" className="h-10 shrink-0 px-4" aria-label="Abrir pesquisa da LUMA">Pesquisar com a LUMA</Button></DialogTrigger>
        <DialogContent className="max-h-[90dvh] w-[calc(100vw_-_2rem)] max-w-5xl overflow-y-auto border-hud-line bg-void p-4 sm:p-7">
          <DialogHeader className="pr-6"><DialogTitle>Pesquisa da LUMA</DialogTitle><DialogDescription>Consulte fontes públicas ou o conhecimento do projeto em uma área dedicada.</DialogDescription></DialogHeader>
          <ResearchPanel/>
        </DialogContent>
      </Dialog>
    </div>
  </footer>;

  return (
    <footer
      className={cn(
        "relative z-20 shrink-0 border-t border-hud-soft bg-void/85 px-2.5 py-2 backdrop-blur-xl sm:px-3.5",
        className,
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent"
      />

      <div className="flex items-center gap-3">
        <div className="hidden shrink-0 items-center gap-3 xl:flex">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-success/35 bg-success/10 px-2.5 py-1 text-[10px] text-success">
            <StatusDot tone="green" size="xs" />
            Orquestrador planejado
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-hud-soft bg-void/60 px-2.5 py-1 text-[10px] text-muted-foreground">
            <ShieldCheck className="size-3 text-primary/80" strokeWidth={2} />
            Voz desabilitada
          </span>
          {lastCommand && (
            <span className="hud-numeric max-w-[190px] truncate rounded-full border border-hud-soft bg-void/60 px-2.5 py-1 text-[10px] text-subtle">
              último: {lastCommand}
            </span>
          )}
        </div>

        <CommandInput className="mx-auto max-w-[760px]" />

        <div className="flex shrink-0 items-center gap-2">
          <span className="hidden items-center gap-1 rounded border border-hud-soft bg-void/60 px-1.5 py-1 text-[9.5px] text-subtle lg:flex">
            <Command className="size-2.5" strokeWidth={2.4} />
            Ctrl + Enter
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-9 sm:h-7"
            disabled onClick={() => pulse("executing", 2000)}
            aria-label="Executar no PC Principal"
          >
            <MonitorDot className="size-3.5" strokeWidth={2} />
            <span className="hidden sm:inline">Executar no PC</span>
            <span className="sm:hidden">Executar</span>
          </Button>
        </div>
      </div>
    </footer>
  );
};
