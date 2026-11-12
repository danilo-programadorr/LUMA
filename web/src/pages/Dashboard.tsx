import { AgentsPanel } from "@/components/luma/agents-panel";
import { ApprovalsPanel } from "@/components/luma/approvals-panel";
import { CoreVisionPanel } from "@/components/luma/core-vision-panel";
import { DevicesPanel } from "@/components/luma/devices-panel";
import { FeedPanel } from "@/components/luma/feed-panel";
import { LumaHero } from "@/components/luma/luma-hero";
import { MonitorPanel } from "@/components/luma/monitor-panel";
import { TimelinePanel } from "@/components/luma/timeline-panel";
import { ToolsPanel } from "@/components/luma/tools-panel";

/**
 * Painel — the command center overview.
 * Below 2xl the rail is hidden, so a priority stack (approvals → devices → feed)
 * is rendered above the alternating panel grid.
 */
const Dashboard = () => (
  <div className="space-y-3">
    <LumaHero />

    <div className="grid gap-3 2xl:hidden">
      <ApprovalsPanel />
      <DevicesPanel variant="full" headline="Status do PC" />
      <FeedPanel limit={5} />
    </div>

    <div className="grid gap-3 xl:grid-cols-2">
      <CoreVisionPanel />
      <AgentsPanel />
      <DevicesPanel className="hidden 2xl:block" />
      <TimelinePanel />
      <MonitorPanel />
      <ToolsPanel />
    </div>
  </div>
);

export default Dashboard;
