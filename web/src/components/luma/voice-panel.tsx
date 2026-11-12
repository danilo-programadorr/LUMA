import { ChevronUp, Focus, Keyboard, Mic, MicOff } from "lucide-react";

import { cn } from "@/lib/utils";
import { orbStateMeta } from "@/luma/tokens";
import { useLuma } from "@/luma/luma-context";
import { Panel } from "@/components/luma/panel";
import { Waveform } from "@/components/luma/waveform";
import { Button } from "@/components/ui/button";

interface VoicePanelProps {
  className?: string;
}

/** Sidebar assistant card — mock voice states, no real audio capture. */
export const VoicePanel = ({ className }: VoicePanelProps) => {
  const { state, pulse, voiceActive, setVoiceActive } = useLuma();
  const meta = orbStateMeta[state];

  const toggleVoice = () => {
    if (voiceActive) {
      setVoiceActive(false);
      pulse("idle", 1400);
      return;
    }
    setVoiceActive(true);
    pulse("listening", 3200);
  };

  return (
    <Panel variant="spotlight" corners sheen={false} className={cn("p-3", className)}>
      <div className="flex items-center gap-2">
        <span className="grid size-5 place-items-center rounded border border-primary/40 bg-primary/10 text-primary">
          <Mic className="size-2.5" strokeWidth={2.2} />
        </span>
        <span className="hud-label text-[9px] text-muted-foreground">Assistente de voz</span>
        <ChevronUp className="ml-auto size-3.5 text-subtle" strokeWidth={2} />
      </div>

      <div className="mt-3 flex items-center justify-center gap-2.5">
        <Waveform bars={5} tone={meta.tone} active={voiceActive} className="w-11" />

        <button
          type="button"
          disabled onClick={toggleVoice}
          aria-label={voiceActive ? "Pausar assistente de voz" : "Ativar assistente de voz"}
          aria-pressed={voiceActive}
          className={cn(
            "group relative grid size-[52px] shrink-0 place-items-center rounded-full border transition-all duration-220 ease-hud",
            voiceActive
              ? "border-primary/60 bg-primary/15 text-primary shadow-glow"
              : "border-hud-line bg-void/60 text-muted-foreground hover:border-primary/50 hover:text-primary",
          )}
        >
          {voiceActive && (
            <>
              <span className="absolute inset-0 animate-ring rounded-full border border-primary/40" />
              <span
                className="absolute inset-0 animate-ring rounded-full border border-primary/25"
                style={{ animationDelay: "1.3s" }}
              />
            </>
          )}
          {voiceActive ? (
            <Mic className="size-5 transition-transform duration-220 ease-hud group-hover:scale-110" strokeWidth={1.8} />
          ) : (
            <MicOff className="size-5" strokeWidth={1.8} />
          )}
        </button>

        <Waveform bars={5} tone={meta.tone} active={voiceActive} className="w-11" />
      </div>

      <p className="hud-title mt-3 text-center text-[13px] text-foreground">
        {voiceActive ? `${meta.label}...` : "Voz desabilitada"}
      </p>
      <p className="mt-0.5 text-center text-[10px] text-muted-foreground">
        {voiceActive ? "Fale agora para dar um comando" : "Disponível em fase futura"}
      </p>

      <div className="mt-3 grid grid-cols-2 gap-1.5">
        <Button size="sm" variant="subtle">
          <Focus className="size-3" strokeWidth={2.2} />
          Modo Foco
        </Button>
        <Button size="sm" variant="subtle">
          <Keyboard className="size-3" strokeWidth={2.2} />
          Atalhos
        </Button>
      </div>
    </Panel>
  );
};
