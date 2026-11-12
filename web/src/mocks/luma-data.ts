import {
  Activity,
  AlertTriangle,
  AppWindow,
  BarChart3,
  Bell,
  BookOpen,
  Boxes,
  BrainCircuit,
  Cpu,
  CalendarDays,
  Code2,
  Command,
  Database,
  FileSearch,
  FileStack,
  FileText,
  Fingerprint,
  FolderKanban,
  Gauge,
  Globe,
  HardDrive,
  KeyRound,
  Layers,
  Library,
  ListTodo,
  Lock,
  Laptop,
  MapPin,
  MessagesSquare,
  Mic,
  MonitorDot,
  Network,
  Orbit,
  Palette,
  PenTool,
  Radar,
  Rocket,
  Server,
  Settings,
  ShieldAlert,
  ShieldCheck,
  ShieldHalf,
  ShieldQuestion,
  Smartphone,
  Sparkles,
  SquareTerminal,
  Sun,
  Terminal,
  TrendingUp,
  UserCircle,
  Users,
  Waypoints,
  Wifi,
  Workflow,
  Wrench,
  Zap,
} from "lucide-react";
import type {
  Agent,
  Approval,
  CalendarEvent,
  ChatMessage,
  Conversation,
  CoreStat,
  Device,
  FeedEvent,
  KnowledgeSource,
  LumaState,
  MemoryRecord,
  MetricReadout,
  Project,
  Task,
  TimelineEvent,
  Tool,
  WorkflowStage,
} from "@/luma/types";

/* ── Owner ───────────────────────────────────────────────────────────── */
export const owner = {
  name: "Danilo",
  role: "Proprietário",
  initials: "DL",
  tier: "Command Tier",
  location: "São Paulo, SP",
  country: "Brasil",
  weather: "24°C",
  weatherLabel: "Parcialmente nublado",
};

/* ── Header status rail ──────────────────────────────────────────────── */
export const systemStatus = [
  { id: "system", label: "Sistema", value: "Online", tone: "green" as const, icon: Zap },
  { id: "network", label: "Rede", value: "Estável", tone: "green" as const, icon: Wifi },
  { id: "services", label: "Serviços", value: "12/12", tone: "cyan" as const, icon: Server },
];

export const headerShortcuts = [
  { id: "grid", label: "Apps", icon: Boxes },
  { id: "alerts", label: "Notificações", icon: Bell, badge: 3 },
  { id: "settings", label: "Configurações", icon: Settings },
];

/* ── LUMA Core hero ──────────────────────────────────────────────────── */
export const coreIntro = {
  eyebrow: "Orquestradora Inteligente",
  title: "LUMA CORE",
  description:
    "Coordena agentes, projetos, ferramentas e seu computador para transformar ideias em resultados.",
  chips: [
    { id: "plan", label: "Planeja", icon: PenTool },
    { id: "orchestrate", label: "Coordena", icon: Workflow },
    { id: "execute", label: "Executa", icon: Zap },
    { id: "learn", label: "Aprende", icon: Sparkles },
  ],
  highlights: [
    "Múltiplos agentes",
    "Contexto unificado",
    "Execução no seu PC",
    "Aprovações seguras",
    "Aprendizado contínuo",
  ],
};

/* ── Visão do Núcleo ─────────────────────────────────────────────────── */
export const coreStats: CoreStat[] = [
  { id: "core", label: "Núcleo ativo", value: "v3.2.0", hint: "Build estável", tone: "cyan", icon: Orbit },
  { id: "memory", label: "Memória indexada", value: "12.4 GB", hint: "48.210 vetores", tone: "violet", icon: Database },
  { id: "agents", label: "9 agentes online", value: "9/9", hint: "de 9 configurados", tone: "green", icon: Users },
  { id: "plane", label: "Control Plane", value: "Saudável", hint: "latência 24 ms", tone: "green", icon: Activity },
  { id: "runtime", label: "Local Runtime", value: "Online", hint: "v1.4.0", tone: "cyan", icon: Terminal },
  { id: "executor", label: "Executor do PC", value: "Conectado", hint: "PC Principal", tone: "blue", icon: Cpu },
];

/* ── Agentes ─────────────────────────────────────────────────────────── */
export const agents: Agent[] = [
  {
    id: "luma", name: "LUMA", role: "ROOT / ORCHESTRATOR",
    description: "Orquestra todos os papéis, decide prioridades e garante contexto unificado.",
    tone: "cyan", icon: Orbit, status: "online", project: "Todos os projetos",
    openTasks: 4, completed: 312, uptime: "42d 06h", root: true,
  },
  {
    id: "product", name: "Product", role: "Product Manager",
    description: "Traduz objetivos do proprietário em escopo, roadmap e critérios de aceite.",
    tone: "violet", icon: Layers, status: "online", project: "Meu Gestor",
    openTasks: 3, completed: 88, uptime: "18d 02h",
  },
  {
    id: "development", name: "Development", role: "Engenharia de Software",
    description: "Implementa features, integra serviços e mantém a base de código.",
    tone: "blue", icon: Code2, status: "online", project: "Meu Gestor",
    openTasks: 5, completed: 147, uptime: "18d 02h",
  },
  {
    id: "codex", name: "Codex", role: "Code Engineer",
    description: "Executa tarefas de código diretamente no ambiente local do PC Principal.",
    tone: "violet", icon: SquareTerminal, status: "executing", project: "Meu Gestor",
    openTasks: 2, completed: 96, uptime: "12d 19h",
  },
  {
    id: "qa", name: "QA", role: "Qualidade",
    description: "Valida entregas, escreve testes e bloqueia regressões antes do merge.",
    tone: "green", icon: ShieldCheck, status: "online", project: "Meu Gestor",
    openTasks: 1, completed: 64, uptime: "11d 08h",
  },
  {
    id: "security", name: "Security", role: "Segurança",
    description: "Audita permissões, classifica risco e exige aprovação em ações sensíveis.",
    tone: "red", icon: ShieldHalf, status: "waiting", project: "MechAI",
    openTasks: 2, completed: 41, uptime: "9d 14h",
  },
  {
    id: "data", name: "Data & Analytics", role: "Dados",
    description: "Modela métricas, consolida fontes e gera leituras analíticas.",
    tone: "blue", icon: BarChart3, status: "online", project: "Meu Gestor",
    openTasks: 2, completed: 53, uptime: "7d 21h",
  },
  {
    id: "growth", name: "Growth & Marketing", role: "Crescimento",
    description: "Planeja experimentos de aquisição e acompanha funil de crescimento.",
    tone: "green", icon: TrendingUp, status: "online", project: "MechAI",
    openTasks: 3, completed: 37, uptime: "6d 03h",
  },
  {
    id: "content", name: "Content & Social", role: "Conteúdo",
    description: "Produz, revisa e distribui conteúdo com a voz da marca.",
    tone: "cyan", icon: FileText, status: "online", project: "LUMA",
    openTasks: 2, completed: 58, uptime: "5d 16h",
  },
];

/* ── Monitor do Sistema ──────────────────────────────────────────────── */
export const systemMonitor = {
  gauges: [
    { id: "cpu", label: "CPU", value: 18, tone: "cyan" as const },
    { id: "ram", label: "RAM", value: 54, tone: "violet" as const },
    { id: "disk", label: "DISCO", value: 36, tone: "cyan" as const },
  ] as MetricReadout[],
  network: {
    download: 42.6,
    upload: 8.4,
    latency: 12,
    series: [18, 26, 22, 34, 30, 44, 38, 52, 46, 58, 50, 62, 56, 68, 61, 74],
  },
  environment: { location: owner.location, country: owner.country, weather: owner.weather, label: owner.weatherLabel },
};

/* ── Dispositivos ────────────────────────────────────────────────────── */
export const devices: Device[] = [
  {
    id: "pc-main", name: "PC Principal", kind: "Workstation", status: "online",
    platform: "Windows 11", detail: "Local Runtime v1.4 · Codex disponível",
    metrics: [
      { label: "CPU", value: 18 },
      { label: "RAM", value: 42 },
      { label: "Disco", value: 36 },
    ],
    capabilities: ["Execução local", "Codex", "Filesystem", "Terminal", "Navegador"],
    lastSeen: "agora", icon: Laptop,
  },
  {
    id: "phone", name: "Celular de Danilo", kind: "Mobile", status: "online",
    platform: "iOS 17.5", detail: "Acesso remoto habilitado",
    metrics: [{ label: "Bateria", value: 78 }],
    capabilities: ["Acesso remoto", "Voz", "Notificações", "Aprovações"],
    lastSeen: "há 2 min", battery: 78, icon: Smartphone,
  },
  {
    id: "tablet", name: "Tablet do Escritório", kind: "Mobile", status: "offline",
    platform: "iPadOS 18", detail: "Modo leitura · aguardando pareamento",
    metrics: [{ label: "Bateria", value: 31 }],
    capabilities: ["Dashboard", "Aprovações"],
    lastSeen: "há 3 dias", battery: 31, icon: MonitorDot,
  },
];

/* ── Linha do tempo ──────────────────────────────────────────────────── */
export const timelineEvents: TimelineEvent[] = [
  { id: "t1", time: "09:00", title: "Daily de alinhamento", meta: "Reunião · 30 min", tone: "blue" },
  { id: "t2", time: "10:00", title: "Implementar feature de relatórios", meta: "Em andamento", project: "Meu Gestor", tone: "cyan", active: true },
  { id: "t3", time: "12:00", title: "Revisão de conteúdos", meta: "Pendente", project: "LUMA", tone: "violet" },
  { id: "t4", time: "14:00", title: "Planejamento de crescimento", meta: "Reunião · 1 hora", tone: "green" },
  { id: "t5", time: "16:30", title: "Auditoria de segurança", meta: "Aguardando autorização", project: "MechAI", tone: "amber" },
];

/* ── Ferramentas / Modelos ───────────────────────────────────────────── */
export const tools: Tool[] = [
  { id: "gemini", name: "Gemini", category: "Modelo de linguagem", status: "connected", detail: "gemini-3-pro · 1.2M tokens/dia", icon: Sparkles, tone: "blue" },
  { id: "adk", name: "Google ADK", category: "Orquestração de agentes", status: "active", detail: "9 agentes registrados", icon: Waypoints, tone: "cyan" },
  { id: "codex", name: "Codex Local", category: "Engenharia de código", status: "ready", detail: "PC Principal · sandbox ativo", icon: SquareTerminal, tone: "violet" },
  { id: "filesystem", name: "Filesystem", category: "Acesso local", status: "connected", detail: "2 workspaces monitorados", icon: HardDrive, tone: "green" },
  { id: "calendar", name: "Google Calendar", category: "Agenda", status: "planned", detail: "Integração planejada", icon: CalendarDays, tone: "slate" },
  { id: "tasks", name: "Google Tasks", category: "Tarefas", status: "planned", detail: "Integração planejada", icon: ListTodo, tone: "slate" },
  { id: "browser", name: "Navegador", category: "Automação web", status: "disabled", detail: "Desabilitado pelo proprietário", icon: Globe, tone: "slate" },
];

/* ── Feed inteligente ────────────────────────────────────────────────── */
export const feedEvents: FeedEvent[] = [
  { id: "f1", time: "11:24", title: "Agente Development concluiu tarefa", detail: "Implementação da feature de relatórios", severity: "success", icon: ShieldCheck, tag: "Dev" },
  { id: "f2", time: "11:18", title: "Novo conteúdo indexado na memória", detail: "3 documentos processados · 1.284 vetores", severity: "info", icon: Database, tag: "Memória" },
  { id: "f3", time: "10:52", title: "Aprovação pendente", detail: "Execução de script no PC Principal", severity: "warning", icon: ShieldAlert, tag: "Aprovação" },
  { id: "f4", time: "10:41", title: "Reunião iniciando em 10 minutos", detail: "Planejamento Semanal", severity: "info", icon: CalendarDays, tag: "Agenda" },
  { id: "f5", time: "09:36", title: "Projeto Meu Gestor atualizado", detail: "2 novas tarefas criadas", severity: "success", icon: FolderKanban, tag: "Projeto" },
  { id: "f6", time: "08:15", title: "Alerta de sistema", detail: "Uso de RAM acima de 75%", severity: "danger", icon: AlertTriangle, tag: "Sistema" },
];

/* ── Aprovações ──────────────────────────────────────────────────────── */
export const approvals: Approval[] = [
  {
    id: "a1", action: "Execução de script no PC Principal", agent: "Codex", project: "Meu Gestor",
    device: "PC Principal", risk: "médio", scope: "npm run migrate -- --dry-run",
    expires: "expira em 1 h", requestedAt: "há 12 min", status: "pending", tone: "amber", icon: SquareTerminal,
  },
  {
    id: "a2", action: "Acesso a dados sensíveis", agent: "Security", project: "MechAI",
    device: "PC Principal", risk: "alto", scope: "dataset-clientes/financeiro",
    expires: "expira em 30 min", requestedAt: "há 28 min", status: "pending", tone: "red", icon: Lock,
  },
  {
    id: "a3", action: "Publicação automática de conteúdo", agent: "Content & Social", project: "LUMA",
    device: "Celular de Danilo", risk: "baixo", scope: "3 posts · LinkedIn",
    expires: "expira em 4 h", requestedAt: "há 46 min", status: "pending", tone: "cyan", icon: Rocket,
  },
  {
    id: "a4", action: "Instalação de dependência", agent: "Development", project: "Meu Gestor",
    device: "PC Principal", risk: "baixo", scope: "pnpm add recharts", expires: "concluída",
    requestedAt: "hoje, 09:12", status: "granted", tone: "green", icon: Code2,
  },
  {
    id: "a5", action: "Envio de e-mail para 120 contatos", agent: "Growth & Marketing", project: "MechAI",
    device: "Nuvem", risk: "médio", scope: "campanha · retenção Q4", expires: "concluída",
    requestedAt: "ontem, 18:40", status: "granted", tone: "green", icon: TrendingUp,
  },
  {
    id: "a6", action: "Execução de rotina de limpeza", agent: "Codex", project: "MechAI",
    device: "PC Principal", risk: "alto", scope: "rm -rf ./tmp/build", expires: "negada",
    requestedAt: "ontem, 15:02", status: "denied", tone: "red", icon: ShieldAlert,
  },
  {
    id: "a7", action: "Acesso remoto contínuo", agent: "LUMA", project: "LUMA",
    device: "Tablet do Escritório", risk: "baixo", scope: "sessão de 8 h", expires: "expirada",
    requestedAt: "3 dias atrás", status: "expired", tone: "slate", icon: KeyRound,
  },
];

/* ── Projetos ────────────────────────────────────────────────────────── */
export const projects: Project[] = [
  {
    id: "p1", name: "Meu Gestor", status: "Em andamento", progress: 68,
    description: "Sistema de gestão financeira com IA", tasks: 12, agents: 4,
    updated: "há 12 min", tone: "cyan", icon: FolderKanban,
  },
  {
    id: "p2", name: "MechAI", status: "Planejamento", progress: 25,
    description: "Automação e agentes especializados", tasks: 8, agents: 3,
    updated: "há 2 h", tone: "violet", icon: Boxes,
  },
  {
    id: "p3", name: "LUMA", status: "Em andamento", progress: 82,
    description: "Centro de comando e orquestração", tasks: 16, agents: 9,
    updated: "há 34 min", tone: "blue", icon: Orbit,
  },
];

/* ── Tarefas ─────────────────────────────────────────────────────────── */
export const tasks: Task[] = [
  { id: "k1", title: "Implementar feature de relatórios", project: "Meu Gestor", agent: "Development", state: "executing", priority: "alta", eta: "hoje, 14:00" },
  { id: "k2", title: "Revisar modelo de dados financeiro", project: "Meu Gestor", agent: "Data & Analytics", state: "analyzing", priority: "média", eta: "hoje, 17:00" },
  { id: "k3", title: "Autorizar migração de schema", project: "Meu Gestor", agent: "Codex", state: "waiting", priority: "alta", eta: "aguardando" },
  { id: "k4", title: "Escrever testes de integração", project: "Meu Gestor", agent: "QA", state: "pending", priority: "média", eta: "amanhã" },
  { id: "k5", title: "Revisão de conteúdos do lançamento", project: "LUMA", agent: "Content & Social", state: "pending", priority: "baixa", eta: "amanhã" },
  { id: "k6", title: "Plano de crescimento Q4", project: "MechAI", agent: "Growth & Marketing", state: "pending", priority: "média", eta: "sexta" },
  { id: "k7", title: "Auditoria de permissões do executor", project: "MechAI", agent: "Security", state: "waiting", priority: "alta", eta: "aguardando" },
  { id: "k8", title: "Refatorar pipeline de indexação", project: "Meu Gestor", agent: "Code2", state: "completed", priority: "média", eta: "concluída 10:24" },
  { id: "k9", title: "Deploy de staging bloqueado por credencial", project: "Meu Gestor", agent: "Codex", state: "blocked", priority: "alta", eta: "bloqueada" },
  { id: "k10", title: "Documentar arquitetura de agentes", project: "LUMA", agent: "Product", state: "completed", priority: "baixa", eta: "concluída 09:10" },
];

/* ── Memória ─────────────────────────────────────────────────────────── */
export const memoryRecords: MemoryRecord[] = [
  { id: "m1", title: "Arquitetura financeira — Meu Gestor", source: "docs/arquitetura.md", collection: "produto", confidence: 96, tokens: "12.4k", indexedAt: "há 6 min", tone: "cyan", icon: FileStack },
  { id: "m2", title: "Preferências do proprietário", source: "system/profile", collection: "preferências", confidence: 99, tokens: "1.1k", indexedAt: "há 2 h", tone: "violet", icon: UserCircle },
  { id: "m3", title: "Playbook de growth Q4", source: "drive/growth-q4.pdf", collection: "marketing", confidence: 88, tokens: "24.8k", indexedAt: "há 5 h", tone: "green", icon: TrendingUp },
  { id: "m4", title: "Política de aprovações sensíveis", source: "security/policy.md", collection: "segurança", confidence: 100, tokens: "3.6k", indexedAt: "ontem", tone: "red", icon: ShieldHalf },
  { id: "m5", title: "Histórico de decisões técnicas", source: "codex/decisions.log", collection: "engenharia", confidence: 92, tokens: "8.2k", indexedAt: "ontem", tone: "blue", icon: Code2 },
  { id: "m6", title: "Voz e tom de comunicação", source: "brand/voice.md", collection: "conteúdo", confidence: 94, tokens: "2.3k", indexedAt: "há 2 dias", tone: "amber", icon: Mic },
];

export const memoryStats = [
  { label: "Vetores indexados", value: "48.210", tone: "cyan" as const, icon: Radar },
  { label: "Coleções", value: "6", tone: "violet" as const, icon: Layers },
  { label: "Documentos", value: "1.284", tone: "blue" as const, icon: FileStack },
  { label: "Precisão média", value: "94%", tone: "green" as const, icon: Gauge },
];

/* ── Conhecimento ────────────────────────────────────────────────────── */
export const knowledgeSources: KnowledgeSource[] = [
  { id: "k1", name: "Documentação interna", kind: "Repositório", documents: 428, indexed: 96, status: "connected", updated: "há 6 min", icon: BookOpen, tone: "cyan" },
  { id: "k2", name: "Google Drive", kind: "Nuvem", documents: 512, indexed: 74, status: "connected", updated: "há 2 h", icon: Network, tone: "blue" },
  { id: "k3", name: "Drive de produto", kind: "Especificações", documents: 96, indexed: 88, status: "active", updated: "há 5 h", icon: FileSearch, tone: "violet" },
  { id: "k4", name: "Base de código", kind: "Engenharia", documents: 176, indexed: 91, status: "ready", updated: "ontem", icon: Code2, tone: "green" },
  { id: "k5", name: "Notion da equipe", kind: "Wiki", documents: 72, indexed: 0, status: "planned", updated: "—", icon: FileText, tone: "slate" },
];

/* ── Conversas ───────────────────────────────────────────────────────── */
export const conversations: Conversation[] = [
  { id: "c1", title: "Relatórios do Meu Gestor", preview: "Preparei o plano de implementação em 4 etapas...", time: "11:32", unread: 2, tone: "cyan", pinned: true },
  { id: "c2", title: "Planejamento de crescimento", preview: "Sugiro testar 3 canais antes de escalar.", time: "10:58", unread: 0, tone: "green" },
  { id: "c3", title: "Auditoria de segurança", preview: "Encontrei 2 permissões amplas no executor.", time: "10:12", unread: 1, tone: "red", pinned: true },
  { id: "c4", title: "Revisão de conteúdo", preview: "Ajustei o tom dos 3 posts para o padrão LUMA.", time: "09:40", unread: 0, tone: "violet" },
  { id: "c5", title: "Arquitetura MechAI", preview: "O ADK cobre bem os 9 papéis com 3 nós.", time: "ontem", unread: 0, tone: "blue" },
  { id: "c6", title: "Memória: preferências", preview: "Memorizei que você prefere respostas curtas.", time: "ontem", unread: 0, tone: "amber" },
  { id: "c7", title: "Codex — execução local", preview: "O script foi autorizado e concluído.", time: "2 dias", unread: 0, tone: "cyan" },
];

export const chatSeed: ChatMessage[] = [
  {
    id: "s1", from: "user", time: "11:26",
    text: "LUMA, preciso entregar a feature de relatórios do Meu Gestor até o fim do dia.",
  },
  {
    id: "s2", from: "luma", time: "11:26",
    text: "Entendido, Danilo. Dividi a entrega em 4 etapas e aloquei 3 agentes. O Codex vai executar no PC Principal.",
    chips: ["Product", "Development", "Codex", "QA"],
  },
  {
    id: "s3", from: "user", time: "11:28",
    text: "Quais riscos você enxerga nessa execução?",
  },
  {
    id: "s4", from: "luma", time: "11:29",
    text: "Um risco médio: a migração do schema exige sua autorização explícita. Enviei a solicitação para a fila de aprovações.",
    chips: ["Aprovações", "Security"],
  },
  {
    id: "s5", from: "luma", time: "11:32",
    text: "Etapa 1 concluída: contratos de API definidos e documentados. Iniciando a implementação do núcleo de relatórios.",
  },
];

/* ── Workflows ───────────────────────────────────────────────────────── */
export const workflowStages: WorkflowStage[] = [
  { id: "w1", title: "Owner Request", subtitle: "Entrada do proprietário", state: "done", tone: "blue", icon: UserCircle, outputs: ["objetivo", "prazo"] },
  { id: "w2", title: "LUMA", subtitle: "Planejamento e roteamento", state: "done", tone: "cyan", icon: Orbit, outputs: ["plano", "agentes"] },
  { id: "w3", title: "Product", subtitle: "Escopo e critérios de aceite", state: "done", tone: "violet", icon: Layers, outputs: ["escopo", "backlog"] },
  { id: "w4", title: "Development", subtitle: "Implementação da entrega", state: "active", tone: "blue", icon: Code2, outputs: ["código", "branch"] },
  { id: "w5", title: "Security", subtitle: "Classificação de risco", state: "gate", tone: "amber", icon: ShieldHalf, outputs: ["risco", "escopo"] },
  { id: "w6", title: "Approval", subtitle: "Autorização humana", state: "gate", tone: "amber", icon: ShieldQuestion, outputs: ["token", "expiração"] },
  { id: "w7", title: "Executor", subtitle: "Execução no dispositivo", state: "queued", tone: "green", icon: Cpu, outputs: ["resultado", "log"] },
];

export const workflowTemplates = [
  { id: "wt1", name: "Entrega de feature", nodes: 7, tone: "cyan" as const, icon: Code2, runs: 42 },
  { id: "wt2", name: "Campanha de conteúdo", nodes: 5, tone: "violet" as const, icon: FileText, runs: 18 },
  { id: "wt3", name: "Auditoria de segurança", nodes: 4, tone: "red" as const, icon: ShieldHalf, runs: 9 },
  { id: "wt4", name: "Rotina de memória", nodes: 6, tone: "blue" as const, icon: Database, runs: 124 },
];

/* ── Calendário ──────────────────────────────────────────────────────── */
export const calendarEvents: CalendarEvent[] = [
  { id: "e1", time: "09:00", end: "09:30", title: "Daily de alinhamento", project: "Todos", kind: "reunião", tone: "blue" },
  { id: "e2", time: "10:00", end: "13:00", title: "Feature de relatórios", project: "Meu Gestor", kind: "execução", tone: "cyan" },
  { id: "e3", time: "12:00", end: "12:40", title: "Revisão de conteúdos", project: "LUMA", kind: "revisão", tone: "violet" },
  { id: "e4", time: "14:00", end: "15:00", title: "Planejamento de crescimento", project: "MechAI", kind: "planejamento", tone: "green" },
  { id: "e5", time: "16:30", end: "17:15", title: "Auditoria de segurança", project: "MechAI", kind: "revisão", tone: "amber" },
  { id: "e6", time: "18:00", end: "18:20", title: "Sincronização de memória", project: "LUMA", kind: "execução", tone: "cyan" },
];

export const calendarWeek = [
  { day: "Seg", date: 19, load: 40 },
  { day: "Ter", date: 20, load: 65 },
  { day: "Qua", date: 21, load: 52 },
  { day: "Qui", date: 22, load: 78 },
  { day: "Sex", date: 23, load: 61 },
  { day: "Sáb", date: 24, load: 34, today: true },
  { day: "Dom", date: 25, load: 12 },
];

/* ── Settings ────────────────────────────────────────────────────────── */
export const settingsSections = [
  { id: "s1", title: "Perfil", detail: "Identidade, tom de voz e fuso horário do proprietário", icon: UserCircle, tone: "cyan" as const, meta: "Danilo · Proprietário" },
  { id: "s2", title: "Aparência", detail: "Tema escuro oficial LUMA, densidade e animações", icon: Palette, tone: "violet" as const, meta: "Dark oficial" },
  { id: "s3", title: "Segurança", detail: "Aprovações exigidas, escopos e expiração de tokens", icon: Fingerprint, tone: "red" as const, meta: "Aprovação obrigatória" },
  { id: "s4", title: "Dispositivos", detail: "Pareamento, acesso remoto e executor local", icon: Cpu, tone: "blue" as const, meta: "3 dispositivos" },
  { id: "s5", title: "Notificações", detail: "Feed inteligente, alertas críticos e resumo diário", icon: Bell, tone: "amber" as const, meta: "12 canais" },
  { id: "s6", title: "Integrações", detail: "Modelos, ferramentas e fontes de conhecimento", icon: Wrench, tone: "green" as const, meta: "4 conectadas" },
];

/* ── Voice ───────────────────────────────────────────────────────────── */
export const voicePrompts = [
  "Resumo do dia",
  "Status do PC",
  "Aprovações pendentes",
  "Criar tarefa",
  "Abrir relatórios",
];

export const orbStateRotation: LumaState[] = [
  "listening",
  "thinking",
  "executing",
  "waiting",
  "idle",
];
