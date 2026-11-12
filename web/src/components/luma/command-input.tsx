import { ResearchPanel } from './research-panel';
import { DEMO } from '@/data/mode';
import { useState, type FormEvent } from "react";
import { CornerDownLeft, Mic, Send } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { voicePrompts } from "@/data/luma-data";
import { orbStateMeta } from "@/luma/tokens";
import { useLuma } from "@/luma/luma-context";
import { Waveform } from "@/components/luma/waveform";
import { Button } from "@/components/ui/button";

interface CommandInputProps {
  className?: string;
  variant?: "bar" | "panel";
  showPrompts?: boolean;
  /** When provided, the command is delegated instead of using the mock orb flow. */
  onSubmit?: (text: string) => void;
  placeholder?: string;
}

/** Command surface. Submitting only produces local, mock UI feedback. */
export const CommandInput = ({
  className,
  variant = "bar",
  showPrompts = true,
  onSubmit,
  placeholder = "Fale com a LUMA",
}: CommandInputProps) => {
  const { state, submitCommand, voiceActive, pulse } = useLuma();
  const [value, setValue] = useState("");
  const meta = orbStateMeta[state];
  const isPanel = variant === "panel";

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!DEMO) { toast.info("Chat e execução indisponíveis neste piloto."); return; }
    const trimmed = value.trim();
    if (!trimmed) {
      pulse("listening", 2400);
      return;
    }
    if (onSubmit) {
      onSubmit(trimmed);
    } else {
      submitCommand(trimmed);
      toast.info("Comando enviado para a LUMA", {
        description: `${trimmed} · demonstração visual, sem execução real`,
      });
    }
    setValue("");
  };

  if (!DEMO) return <div className={className}><ResearchPanel /></div>;

  return (
    <div className={cn("w-full", className)}>
      <form
        onSubmit={handleSubmit}
        className={cn(
          "flex items-center gap-2.5 rounded-md border border-hud-line bg-void/70 px-2.5 shadow-[inset_0_0_30px_-16px_var(--hud-glow-strong)] backdrop-blur-md transition-all duration-220 ease-hud focus-within:border-primary/70 focus-within:shadow-glow",
          isPanel ? "rounded-lg py-3" : "rounded-full py-1.5",
        )}
      >
        <Waveform bars={isPanel ? 9 : 7} tone={meta.tone} active={voiceActive} className={cn("hidden shrink-0 md:flex", isPanel ? "w-20" : "w-16")} />

        <span
          className={cn(
            "grid size-8 shrink-0 place-items-center rounded-full border",
            voiceActive
              ? "animate-pulse-dot border-primary/60 bg-primary/15 text-primary"
              : "border-hud-line bg-void/60 text-muted-foreground",
          )}
        >
          <Mic className="size-3.5" strokeWidth={1.9} />
        </span>

        <div className="min-w-0 flex-1">
          <input
            value={value}
            onChange={(event) => setValue(event.target.value)}
            aria-label="Fale com a LUMA"
            placeholder={placeholder}
            className="w-full bg-transparent text-[12.5px] text-foreground outline-none placeholder:text-foreground/85"
          />
          <p className="truncate text-[9.5px] text-primary/85">
            {value.trim()
              ? "Pressione Enter para enviar o comando"
              : voiceActive
                ? "Estou ouvindo..."
                : "Assistente em pausa"}
          </p>
        </div>

        <span className="hidden shrink-0 items-center gap-1 rounded border border-hud-soft bg-void/60 px-1.5 py-0.5 text-[9.5px] text-subtle sm:flex">
          <CornerDownLeft className="size-2.5" strokeWidth={2.4} />
          Enter
        </span>

        <Button disabled={!DEMO} type="submit" size="icon-sm" variant="default" aria-label="Enviar comando" className="shrink-0">
          <Send className="size-3.5" strokeWidth={2} />
        </Button>
      </form>

      {showPrompts && (
        <div className={cn("mt-2 flex flex-wrap items-center gap-1.5", isPanel ? "" : "hidden xl:flex")}>
          {voicePrompts.map((prompt, index) => (
            <button
              key={prompt}
              type="button"
              onClick={() => setValue(prompt)}
              className="rounded-full border border-hud-soft bg-void/50 px-2 py-0.5 text-[10px] text-muted-foreground transition-all duration-150 ease-hud hover:border-primary/50 hover:bg-primary/10 hover:text-primary"
              style={{ animation: `luma-fade-up 0.45s cubic-bezier(0.22,1,0.36,1) ${240 + index * 40}ms both` }}
            >
              {prompt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
