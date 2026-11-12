import { ArrowRight, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import { feedEvents } from "@/data/luma-data";
import { Panel, PanelHeader, PanelLink } from "@/components/luma/panel";
import { FeedItem, LiveBadge } from "@/components/luma/feed-item";

interface FeedPanelProps {
  className?: string;
  limit?: number;
  onOpen?: string;
}

export const FeedPanel = ({ className, limit = 6 }: FeedPanelProps) => {
  const list = feedEvents.slice(0, limit);

  return (
    <Panel className={cn("animate-fade-up", className)}>
      <PanelHeader
        icon={Sparkles}
        title="Feed Inteligente"
        meta={<LiveBadge />}
        action={
          <PanelLink to="/conversations">
            Ver tudo
            <ArrowRight className="size-3" strokeWidth={2} />
          </PanelLink>
        }
      />
      <div className="space-y-0.5 p-2">
        {list.map((event, index) => (
          <div
            key={event.id}
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 55}ms both` }}
          >
            <FeedItem event={event} />
          </div>
        ))}
      </div>
    </Panel>
  );
};
