import { AuthGuard, AuthScreen } from './auth/AuthScreen';
import { LumaShell } from "./components/luma/luma-shell";
import AgentsPage from "./pages/AgentsPage";
import ApprovalsPage from "./pages/ApprovalsPage";
import CalendarPage from "./pages/CalendarPage";
import ConversationsPage from "./pages/ConversationsPage";
import CorePage from "./pages/CorePage";
import Dashboard from "./pages/Dashboard";
import DevicesPage from "./pages/DevicesPage";
import KnowledgePage from "./pages/KnowledgePage";
import MemoryPage from "./pages/MemoryPage";
import NotFound from "./pages/NotFound";
import ProjectsPage from "./pages/ProjectsPage";
import SettingsPage from "./pages/SettingsPage";
import TasksPage from "./pages/TasksPage";
import ToolsPage from "./pages/ToolsPage";
import WorkflowsPage from "./pages/WorkflowsPage";

export const routers = [
  { path: "/login", element: <AuthScreen /> },
  {
    path: "/",
    name: "luma-shell",
    element: <AuthGuard><LumaShell /></AuthGuard>,
    children: [
      { index: true, name: "painel", element: <Dashboard /> },
      { path: "dashboard", name: "dashboard", element: <Dashboard /> },
      { path: "core", name: "nucleo", element: <CorePage /> },
      { path: "agents", name: "agentes", element: <AgentsPage /> },
      { path: "projects", name: "projetos", element: <ProjectsPage /> },
      { path: "tasks/:taskId", element: <TasksPage /> },
      { path: "approvals/:taskId", element: <ApprovalsPage /> },
      { path: "tasks", name: "tarefas", element: <TasksPage /> },
      { path: "calendar", name: "calendario", element: <CalendarPage /> },
      { path: "memory", name: "memoria", element: <MemoryPage /> },
      { path: "conversations", name: "conversas", element: <ConversationsPage /> },
      { path: "knowledge", name: "conhecimento", element: <KnowledgePage /> },
      { path: "tools", name: "ferramentas", element: <ToolsPage /> },
      { path: "workflows", name: "fluxos", element: <WorkflowsPage /> },
      { path: "devices", name: "dispositivos", element: <DevicesPage /> },
      { path: "approvals", name: "aprovacoes", element: <ApprovalsPage /> },
      { path: "settings", name: "configuracoes", element: <SettingsPage /> },
      /* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */
      { path: "*", name: "404", element: <NotFound /> },
    ],
  },
];

declare global {
  interface Window {
    __routers__: typeof routers;
  }
}

window.__routers__ = routers;
