import type { LucideIcon } from "lucide-react";

/* ── Orb / system states ─────────────────────────────────────────────── */
export type LumaState =
  | "idle"
  | "listening"
  | "thinking"
  | "executing"
  | "waiting"
  | "error";

export type Tone =
  | "cyan"
  | "blue"
  | "violet"
  | "green"
  | "amber"
  | "red"
  | "slate";

export type StatusKey =
  | "online"
  | "executing"
  | "waiting"
  | "error"
  | "offline";

export type ToolStatusKey =
  | "connected"
  | "active"
  | "ready"
  | "planned"
  | "disabled";

export type TaskStateKey =
  | "pending"
  | "analyzing"
  | "waiting"
  | "executing"
  | "completed"
  | "blocked";

export type ApprovalStateKey = "pending" | "granted" | "denied" | "expired";

export type RiskLevel = "baixo" | "médio" | "alto";

/* ── Navigation ──────────────────────────────────────────────────────── */
export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  badge?: number;
  hint: string;
}

/* ── Domain models ───────────────────────────────────────────────────── */
export interface Agent {
  id: string;
  name: string;
  role: string;
  description: string;
  tone: Tone;
  icon: LucideIcon;
  status: StatusKey;
  project: string;
  openTasks: number;
  completed: number;
  uptime: string;
  root?: boolean;
}

export interface Project {
  id: string;
  name: string;
  status: string;
  progress: number;
  description: string;
  tasks: number;
  agents: number;
  updated: string;
  tone: Tone;
  icon: LucideIcon;
}

export interface Approval {
  id: string;
  action: string;
  agent: string;
  project: string;
  device: string;
  risk: RiskLevel;
  scope: string;
  expires: string;
  requestedAt: string;
  status: ApprovalStateKey;
  icon: LucideIcon;
  tone: Tone;
}

export interface FeedEvent {
  id: string;
  time: string;
  title: string;
  detail: string;
  severity: "success" | "info" | "warning" | "danger";
  icon: LucideIcon;
  tag?: string;
}

export interface DeviceMetric {
  label: string;
  value: number;
}

export interface Device {
  id: string;
  name: string;
  kind: string;
  status: StatusKey;
  platform: string;
  detail: string;
  metrics: DeviceMetric[];
  capabilities: string[];
  lastSeen: string;
  battery?: number;
  icon: LucideIcon;
}

export interface Tool {
  id: string;
  name: string;
  category: string;
  status: ToolStatusKey;
  detail: string;
  icon: LucideIcon;
  tone: Tone;
}

export interface TimelineEvent {
  id: string;
  time: string;
  title: string;
  meta: string;
  project?: string;
  tone: Tone;
  active?: boolean;
}

export interface Task {
  id: string;
  title: string;
  project: string;
  agent: string;
  state: TaskStateKey;
  priority: "alta" | "média" | "baixa";
  eta: string;
}

export interface MemoryRecord {
  id: string;
  title: string;
  source: string;
  collection: string;
  confidence: number;
  tokens: string;
  indexedAt: string;
  tone: Tone;
  icon: LucideIcon;
}

export interface KnowledgeSource {
  id: string;
  name: string;
  kind: string;
  documents: number;
  indexed: number;
  status: ToolStatusKey;
  updated: string;
  icon: LucideIcon;
  tone: Tone;
}

export interface Conversation {
  id: string;
  title: string;
  preview: string;
  time: string;
  unread: number;
  tone: Tone;
  pinned?: boolean;
}

export interface ChatMessage {
  id: string;
  from: "user" | "luma";
  text: string;
  time: string;
  chips?: string[];
}

export interface WorkflowStage {
  id: string;
  title: string;
  subtitle: string;
  state: "done" | "active" | "queued" | "gate";
  tone: Tone;
  icon: LucideIcon;
  outputs: string[];
}

export interface CalendarEvent {
  id: string;
  time: string;
  end: string;
  title: string;
  project: string;
  kind: "reunião" | "execução" | "revisão" | "planejamento";
  tone: Tone;
}

export interface CoreStat {
  id: string;
  label: string;
  value: string;
  hint: string;
  tone: Tone;
  icon: LucideIcon;
}

export interface MetricReadout {
  id: string;
  label: string;
  value: number;
  tone: Tone;
}

