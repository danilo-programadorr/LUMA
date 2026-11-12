import { DEMO } from '@/data/mode';
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { LumaContext, type CommandLogEntry } from "@/luma/luma-context";
import type { LumaState } from "@/luma/types";

const MAX_LOG = 12;

/**
 * Holds the purely visual orchestrator state used across the command center.
 * No backend, no network, no persistence — local UI state only.
 */
export const LumaProvider = ({ children }: { children: ReactNode }) => {
  const [state, setState] = useState<LumaState>("idle");
  const [commands, setCommands] = useState<CommandLogEntry[]>([]);
  const [voiceActive, setVoiceActive] = useState(false);
  const timers = useRef<number[]>([]);

  const clearTimers = useCallback(() => {
    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  const pulse = useCallback(
    (next: LumaState, duration = 1900) => {
      clearTimers();
      setState(next);
      timers.current.push(window.setTimeout(() => setState("idle"), duration));
    },
    [clearTimers],
  );

  const submitCommand = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || !DEMO) return;

      clearTimers();
      const at = new Date().toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
      });

      setCommands((previous) =>
        [
          { id: `${Date.now()}-${previous.length}`, text: trimmed, at, state: "thinking" as LumaState },
          ...previous,
        ].slice(0, MAX_LOG),
      );

      setState("thinking");
      timers.current.push(window.setTimeout(() => setState("executing"), 1200));
      timers.current.push(window.setTimeout(() => setState("idle"), 3200));
    },
    [clearTimers],
  );

  const value = useMemo(
    () => ({
      state,
      setState,
      pulse,
      submitCommand,
      commands,
      lastCommand: commands[0]?.text ?? null,
      voiceActive,
      setVoiceActive,
    }),
    [state, pulse, submitCommand, commands, voiceActive],
  );

  return <LumaContext.Provider value={value}>{children}</LumaContext.Provider>;
};
