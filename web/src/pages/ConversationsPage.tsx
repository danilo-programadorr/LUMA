import { DEMO } from '@/data/mode';
import { mockReplies } from "@/data/page-data";
import { useEffect, useRef, useState } from "react";
import { MessageSquare, Pin, Plus, Sparkles, Users } from "lucide-react";

import { chatSeed, conversations } from "@/data/luma-data";
import type { ChatMessage } from "@/luma/types";
import { useLuma } from "@/luma/luma-context";
import { PageHeader } from "@/components/luma/page-header";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { LumaOrb } from "@/components/luma/luma-orb";
import { CommandInput } from "@/components/luma/command-input";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";
import { Waveform } from "@/components/luma/waveform";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";



const ConversationsPage = () => {
  const { setState } = useLuma();
  const [activeId, setActiveId] = useState(conversations[0]?.id ?? "");
  const [messages, setMessages] = useState<ChatMessage[]>(chatSeed);
  const [thinking, setThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const timers = useRef(new Set<number>());

  const activeConversation = conversations.find((conversation) => conversation.id === activeId);

  useEffect(() => {
    setState("listening");
  }, [setState]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  useEffect(() => {
    const pendingTimers = timers.current;
    return () => {
      pendingTimers.forEach((timer) => window.clearTimeout(timer));
      pendingTimers.clear();
    };
  }, []);

  const handleSend = (text: string) => {
    if (!DEMO) return;
    const time = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    setMessages((previous) => [
      ...previous,
      { id: `user-${Date.now()}`, from: "user", text, time },
    ]);
    setThinking(true);
    setState("thinking");

    const timer = window.setTimeout(() => {
      timers.current.delete(timer);
      setThinking(timers.current.size > 0);
      if (!timers.current.size) setState("listening");
      setMessages((previous) => [
        ...previous,
        {
          id: `luma-${Date.now()}`,
          from: "luma",
          text: mockReplies[previous.length % mockReplies.length],
          time,
          chips: ["Product", "Development"],
        },
      ]);
    }, 1500);
    timers.current.add(timer);
  };

  return (
    <div className="space-y-3">
      <PageHeader
        eyebrow="Interação"
        icon={MessageSquare}
        title="Conversas"
        description="Histórico de diálogos com a LUMA. As respostas desta demonstração são locais e simuladas — nenhum modelo é consultado."
        meta={
          <>
            <ToneChip tone="cyan">
              <MessageSquare className="size-3" strokeWidth={2.2} />
              {conversations.length} conversas
            </ToneChip>
            <ToneChip tone="amber">
              <Users className="size-3" strokeWidth={2.2} />
              3 não lidas
            </ToneChip>
            <ToneChip tone="green">
              <StatusDot tone="green" size="xs" />
              orquestradora ativa
            </ToneChip>
          </>
        }
        actions={
          <Button variant="outline" size="sm">
            <Plus className="size-3" strokeWidth={2.4} />
            Nova conversa
          </Button>
        }
      />

      <div className="grid gap-3 lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)]">
        <Panel className="flex h-[min(76vh,760px)] flex-col">
          <PanelHeader
            icon={Users}
            title="Histórico"
            hint="Contextos recentes"
            meta={<span className="hud-numeric text-[10px] text-subtle">12 total</span>}
          />
          <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
            {conversations.map((conversation) => {
              const active = conversation.id === activeId;
              return (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => setActiveId(conversation.id)}
                  className={cn(
                    "group w-full rounded-md border px-2.5 py-2 text-left transition-all duration-150 ease-hud",
                    active
                      ? "border-primary/45 bg-primary/12 shadow-glow-xs"
                      : "border-transparent hover:border-hud-soft hover:bg-primary/[0.06]",
                  )}
                >
                  <div className="flex items-center gap-1.5">
                    {conversation.pinned && <Pin className="size-2.5 shrink-0 text-primary" strokeWidth={2.2} />}
                    <span
                      className={cn(
                        "truncate text-[11.5px] font-medium",
                        active ? "text-foreground" : "text-muted-foreground group-hover:text-foreground",
                      )}
                    >
                      {conversation.title}
                    </span>
                    <span className="hud-numeric ml-auto shrink-0 text-[9px] text-subtle">{conversation.time}</span>
                  </div>
                  <p className="mt-0.5 truncate text-[10px] text-subtle">{conversation.preview}</p>
                  {conversation.unread > 0 && (
                    <span className="hud-numeric mt-1.5 inline-flex items-center gap-1 rounded-full border border-primary/40 bg-primary/12 px-1.5 text-[9px] text-primary">
                      {conversation.unread} nova(s)
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </Panel>

        <Panel className="flex h-[min(76vh,760px)] flex-col">
          <div className="flex items-center gap-3 border-b border-hud-soft px-3 py-2.5">
            <LumaOrb state="idle" size={46} showLabel={false} gyroscope={false} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12.5px] font-medium text-foreground">
                LUMA · {activeConversation?.title}
              </p>
              <p className="flex items-center gap-1.5 text-[10px] text-subtle">
                <StatusDot tone={thinking ? "cyan" : "green"} />
                {thinking ? "processando contexto..." : "não conectado"}
              </p>
            </div>
            <Waveform bars={5} tone="cyan" active={thinking} className="hidden w-12 sm:flex" />
            <ToneChip tone="violet" className="hidden text-[9.5px] sm:inline-flex">
              <Sparkles className="size-2.5" strokeWidth={2.2} />
              Agentes planejados
            </ToneChip>
          </div>

          <div ref={scrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3.5">
            {messages.map((message, index) => {
              const isUser = message.from === "user";
              return (
                <div
                  key={message.id}
                  className={cn("flex", isUser ? "justify-end" : "justify-start")}
                  style={{ animation: `luma-fade-up 0.45s cubic-bezier(0.22,1,0.36,1) ${Math.min(index, 6) * 40}ms both` }}
                >
                  <div className={cn("max-w-[85%] sm:max-w-[72%]", isUser && "text-right")}>
                    <div
                      className={cn(
                        "rounded-lg border px-3 py-2 text-left text-[11.5px] leading-relaxed",
                        isUser
                          ? "border-primary/40 bg-primary/12 text-foreground"
                          : "border-hud-line bg-hud-surface text-foreground/90 backdrop-blur-md",
                      )}
                    >
                      {message.text}
                    </div>
                    {message.chips && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {message.chips.map((chip) => (
                          <span
                            key={chip}
                            className="hud-label rounded-full border border-hud-soft bg-void/50 px-1.5 py-0.5 text-[8.5px] text-subtle"
                          >
                            {chip}
                          </span>
                        ))}
                      </div>
                    )}
                    <p className="hud-numeric mt-1 text-[9px] text-subtle">{message.time}</p>
                  </div>
                </div>
              );
            })}

            {thinking && (
              <div className="flex justify-start">
                <div className="inline-flex items-center gap-2 rounded-lg border border-hud-line bg-hud-surface px-3 py-2 backdrop-blur-md">
                  <Waveform bars={4} tone="violet" className="w-8" />
                  <span className="text-[10.5px] text-muted-foreground">LUMA está pensando...</span>
                </div>
              </div>
            )}
          </div>

          <div className="border-t border-hud-soft p-3">
            <CommandInput variant="panel" showPrompts onSubmit={handleSend} />
          </div>
        </Panel>
      </div>
    </div>
  );
};

export default ConversationsPage;

