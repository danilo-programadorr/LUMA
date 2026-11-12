import type { LumaState, StatusKey, Tone, ToolStatusKey, TaskStateKey } from "./types";

/* ── Tone primitives (single source of truth for HUD color usage) ─────── */
export const toneHsl: Record<Tone, string> = {
  cyan: "186, 100%, 50%",
  blue: "210, 100%, 54%",
  violet: "258, 100%, 68%",
  green: "162, 100%, 45%",
  amber: "40, 100%, 58%",
  red: "349, 100%, 63%",
  slate: "201, 24%, 55%",
};

export const toneColor = (tone: Tone, alpha = 1) =>
  `hsla(${toneHsl[tone]}, ${alpha})`;

export const toneText: Record<Tone, string> = {
  cyan: "text-primary",
  blue: "text-accent",
  violet: "text-violet",
  green: "text-success",
  amber: "text-warning",
  red: "text-destructive",
  slate: "text-muted-foreground",
};

export const toneChip: Record<Tone, string> = {
  cyan: "border-primary/40 bg-primary/10 text-primary",
  blue: "border-accent/40 bg-accent/10 text-accent",
  violet: "border-violet/40 bg-violet/10 text-violet",
  green: "border-success/40 bg-success/10 text-success",
  amber: "border-warning/40 bg-warning/10 text-warning",
  red: "border-destructive/40 bg-destructive/10 text-destructive",
  slate: "border-border bg-surface-high/60 text-muted-foreground",
};

export const toneWell: Record<Tone, string> = {
  cyan: "border-primary/25 bg-primary/[0.07]",
  blue: "border-accent/25 bg-accent/[0.07]",
  violet: "border-violet/25 bg-violet/[0.07]",
  green: "border-success/25 bg-success/[0.07]",
  amber: "border-warning/25 bg-warning/[0.07]",
  red: "border-destructive/25 bg-destructive/[0.07]",
  slate: "border-border/70 bg-surface-high/40",
};

export const toneGlow: Record<Tone, string> = {
  cyan: "shadow-glow-sm",
  blue: "shadow-glow-sm",
  violet: "shadow-violet",
  green: "shadow-online",
  amber: "shadow-waiting",
  red: "shadow-danger",
  slate: "",
};

export const toneRing: Record<Tone, string> = {
  cyan: "hover:border-primary/60",
  blue: "hover:border-accent/60",
  violet: "hover:border-violet/60",
  green: "hover:border-success/60",
  amber: "hover:border-warning/60",
  red: "hover:border-destructive/60",
  slate: "hover:border-border",
};

/* ── Status maps ─────────────────────────────────────────────────────── */
export const statusMeta: Record<StatusKey, { label: string; tone: Tone }> = {
  online: { label: "Online", tone: "green" },
  executing: { label: "Executando", tone: "cyan" },
  waiting: { label: "Aguardando", tone: "amber" },
  error: { label: "Erro", tone: "red" },
  offline: { label: "Offline", tone: "slate" },
};

export const toolStatusMeta: Record<ToolStatusKey, { label: string; tone: Tone }> = {
  connected: { label: "Conectado", tone: "green" },
  active: { label: "Ativo", tone: "cyan" },
  ready: { label: "Pronto", tone: "blue" },
  planned: { label: "Planejado", tone: "slate" },
  disabled: { label: "Desabilitado", tone: "slate" },
};

export const taskStateMeta: Record<TaskStateKey, { label: string; tone: Tone }> = {
  pending: { label: "Pendente", tone: "slate" },
  analyzing: { label: "Analisando", tone: "blue" },
  waiting: { label: "Aguardando autorização", tone: "amber" },
  executing: { label: "Executando", tone: "cyan" },
  completed: { label: "Concluída", tone: "green" },
  blocked: { label: "Bloqueada", tone: "red" },
};

/* ── Orb state descriptors ───────────────────────────────────────────── */
export const orbStateMeta: Record<
  LumaState,
  { label: string; caption: string; tone: Tone; speed: number }
> = {
  idle: { label: "Ociosa", caption: "Sistemas em repouso", tone: "cyan", speed: 0.14 },
  listening: { label: "Ouvindo", caption: "Estou ouvindo...", tone: "blue", speed: 0.3 },
  thinking: { label: "Pensando", caption: "Processando contexto", tone: "violet", speed: 0.72 },
  executing: { label: "Executando", caption: "Orquestrando agentes", tone: "cyan", speed: 0.48 },
  waiting: { label: "Aguardando autorização", caption: "Confirmação necessária", tone: "amber", speed: 0.2 },
  error: { label: "Erro", caption: "Intervenção requerida", tone: "red", speed: 0.18 },
};

export const severityMeta: Record<
  "success" | "info" | "warning" | "danger",
  { tone: Tone }
> = {
  success: { tone: "green" },
  info: { tone: "blue" },
  warning: { tone: "amber" },
  danger: { tone: "red" },
};
