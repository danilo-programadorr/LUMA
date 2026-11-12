/** Demonstration fixtures only; never real LUMA state. */
import { BrainCircuit, Activity, Terminal, Waypoints, Sparkles, Cpu } from "lucide-react";
import type { ReadoutRow } from "@/components/luma/readout-panel";

export const runtimeRows: ReadoutRow[] = [
  { id: "version", label: "Versão do núcleo", value: "v3.2.0", tone: "cyan", icon: BrainCircuit },
  { id: "control", label: "Control Plane", value: "Saudável", tone: "green", icon: Activity, hint: "latência 24 ms" },
  { id: "runtime", label: "Local Runtime", value: "v1.4.0", tone: "cyan", icon: Terminal, hint: "PC Principal" },
  { id: "adk", label: "Google ADK", value: "Ativo", tone: "green", icon: Waypoints, hint: "9 agentes registrados" },
  { id: "model", label: "Modelo primário", value: "Gemini", tone: "blue", icon: Sparkles, hint: "gemini-3-pro" },
  { id: "uptime", label: "Uptime contínuo", value: "42d 06h", tone: "violet", icon: Cpu },
];

export const processes = [
  { id: "pr1", name: "Indexação de memória", state: "executando", progress: 62, tone: "cyan" as const },
  { id: "pr2", name: "Feature de relatórios", state: "aguardando aprovação", progress: 41, tone: "amber" as const },
  { id: "pr3", name: "Auditoria de permissões", state: "na fila", progress: 12, tone: "slate" as const },
  { id: "pr4", name: "Sincronização de dispositivos", state: "concluído", progress: 100, tone: "green" as const },
];

export const collectionRows = [
  { id: "c1", label: "produto", value: "34%", tone: "cyan" as const },
  { id: "c2", label: "engenharia", value: "41%", tone: "blue" as const },
  { id: "c3", label: "preferências", value: "22%", tone: "amber" as const },
  { id: "c4", label: "conteúdo", value: "16%", tone: "violet" as const },
];

export const heartbeats = [
  { id: "h1", device: "PC Principal", interval: "12 s", status: "estável", tone: "green" as const },
  { id: "h2", device: "Celular de Danilo", interval: "48 s", status: "estável", tone: "green" as const },
  { id: "h3", device: "Tablet do Escritório", interval: "—", status: "offline", tone: "slate" as const },
];

export const queue = [
  { id: "q1", name: "docs/arquitetura-financeira.md", size: "412 KB", state: "indexado", tone: "green" as const },
  { id: "q2", name: "drive/growth-q4.pdf", size: "2.1 MB", state: "processando", tone: "cyan" as const },
  { id: "q3", name: "api/contratos-v3.ts", size: "88 KB", state: "na fila", tone: "slate" as const },
  { id: "q4", name: "brand/voice-guidelines.md", size: "126 KB", state: "indexado", tone: "green" as const },
];

export const categories = [
  { id: "k1", name: "Produto", value: "428 docs", tone: "cyan" as const },
  { id: "k2", name: "Engenharia", value: "176 docs", tone: "blue" as const },
  { id: "k3", name: "Marketing", value: "132 docs", tone: "green" as const },
  { id: "k4", name: "Segurança", value: "52 docs", tone: "red" as const },
  { id: "k5", name: "Conteúdo", value: "96 docs", tone: "violet" as const },
  { id: "k6", name: "Operações", value: "24 docs", tone: "amber" as const },
];

export const collections = [
  { id: "c1", name: "produto", documents: 428, weight: 34, tone: "cyan" as const },
  { id: "c2", name: "engenharia", documents: 176, weight: 41, tone: "blue" as const },
  { id: "c3", name: "preferências", documents: 24, weight: 22, tone: "amber" as const },
  { id: "c4", name: "conteúdo", documents: 96, weight: 16, tone: "violet" as const },
  { id: "c5", name: "marketing", documents: 132, weight: 18, tone: "green" as const },
  { id: "c6", name: "segurança", documents: 52, weight: 12, tone: "red" as const },
];

export const quotaRows = [
  { id: "q1", label: "Gemini · tokens diários", value: 62, tone: "blue" as const, hint: "1.2M de 2M utilizados" },
  { id: "q2", label: "ADK · execuções de agente", value: 48, tone: "cyan" as const, hint: "96 de 200 sessões" },
  { id: "q3", label: "Codex · minutos de sandbox", value: 34, tone: "violet" as const, hint: "102 de 300 minutos" },
  { id: "q4", label: "Filesystem · leituras", value: 21, tone: "green" as const, hint: "2.1k de 10k operações" },
];

export const mockReplies = [
  "Registrei sua solicitação. Vou coordenar os agentes necessários e retorno com o plano de execução.",
  "Analisando o contexto atual do projeto. Assim que o plano estiver pronto, envio para sua autorização.",
  "Entendido. Distribuí a demanda entre Product e Development e mantive o QA em observação.",
];

export const appearanceOptions = [
  { id: "dark", label: "Escuro oficial", hint: "Padrão LUMA", active: true },
  { id: "dim", label: "Escuro suave", hint: "Em preparação", active: false },
  { id: "light", label: "Claro", hint: "Tokens já preparados", active: false },
];

export const densityOptions = [
  { id: "comfortable", label: "Confortável", active: false },
  { id: "compact", label: "Compacto", active: true },
];

export const notificationRows = [
  { id: "n1", label: "Alertas críticos", detail: "Falhas e bloqueios de execução", enabled: true },
  { id: "n2", label: "Aprovações pendentes", detail: "Solicitações aguardando o proprietário", enabled: true },
  { id: "n3", label: "Resumo diário", detail: "Consolidado enviado às 08:00", enabled: false },
  { id: "n4", label: "Ruído do feed", detail: "Eventos informativos de baixa prioridade", enabled: false },
];

