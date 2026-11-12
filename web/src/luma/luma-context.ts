import { createContext, useContext } from "react";
import type { LumaState } from "./types";

export interface CommandLogEntry {
  id: string;
  text: string;
  at: string;
  state: LumaState;
}

export interface LumaContextValue {
  /** Current visual state of the orchestrator (drives orb, voice bar, badges). */
  state: LumaState;
  setState: (state: LumaState) => void;
  /** Briefly switch state, then fall back to the previous one. */
  pulse: (state: LumaState, duration?: number) => void;
  /** Local, mock command submission — no backend, no AI call. */
  submitCommand: (text: string) => void;
  commands: CommandLogEntry[];
  lastCommand: string | null;
  voiceActive: boolean;
  setVoiceActive: (active: boolean) => void;
}

export const LumaContext = createContext<LumaContextValue | undefined>(undefined);

export function useLuma(): LumaContextValue {
  const context = useContext(LumaContext);
  if (!context) {
    throw new Error("useLuma must be used inside <LumaProvider>.");
  }
  return context;
}
