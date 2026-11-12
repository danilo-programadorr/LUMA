import { DEMO } from '@/data/mode';
import {
  AppWindow,
  BrainCircuit,
  CalendarDays,
  FolderKanban,
  LayoutDashboard,
  Library,
  ListTodo,
  MessagesSquare,
  Radar,
  Settings,
  ShieldQuestion,
  Waypoints,
  Wrench,
} from "lucide-react";
import type { NavItem } from "./types";

export const navItems: NavItem[] = [
  { label: "Painel", to: "/", icon: LayoutDashboard, hint: "Visão geral operacional" },
  { label: "Núcleo", to: "/core", icon: BrainCircuit, hint: "Cérebro da LUMA" },
  { label: "Agentes", to: "/agents", icon: Waypoints, badge: DEMO ? 9 : undefined, hint: "Papéis orquestrados" },
  { label: "Projetos", to: "/projects", icon: FolderKanban, badge: DEMO ? 2 : undefined, hint: "Iniciativas ativas" },
  { label: "Tarefas", to: "/tasks", icon: ListTodo, badge: DEMO ? 8 : undefined, hint: "Fila de execução" },
  { label: "Calendário", to: "/calendar", icon: CalendarDays, hint: "Agenda do dia" },
  { label: "Memória", to: "/memory", icon: Radar, hint: "Contexto indexado" },
  { label: "Conversas", to: "/conversations", icon: MessagesSquare, badge: DEMO ? 12 : undefined, hint: "Histórico com a LUMA" },
  { label: "Conhecimento", to: "/knowledge", icon: Library, hint: "Fontes e documentos" },
  { label: "Ferramentas", to: "/tools", icon: Wrench, hint: "Modelos e integrações" },
  { label: "Fluxos", to: "/workflows", icon: AppWindow, hint: "Orquestração visual" },
  { label: "Dispositivos", to: "/devices", icon: Settings, hint: "Máquinas conectadas" },
  { label: "Aprovações", to: "/approvals", icon: ShieldQuestion, badge: DEMO ? 3 : undefined, hint: "Autorizações pendentes" },
];
