import { ReauthenticateButton } from '@/auth/AuthScreen';
import { appearanceOptions, densityOptions, notificationRows } from "@/data/page-data";
import { useEffect } from "react";
import {
  Bell,
  Fingerprint,
  Palette,
  RotateCcw,
  Save,
  Settings as SettingsIcon,
  ShieldCheck,
  Trash2,
  UserCircle,
} from "lucide-react";

import { owner, settingsSections, tools } from "@/data/luma-data";
import { toneChip } from "@/luma/tokens";
import { useLuma } from "@/luma/luma-context";
import { PageHeader } from "@/components/luma/page-header";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { ReadoutPanel } from "@/components/luma/readout-panel";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";







const SettingsPage = () => {
  const { setState } = useLuma();

  useEffect(() => {
    setState("idle");
  }, [setState]);

  return (
    <div className="space-y-3">
      <ReauthenticateButton />
      <PageHeader
        eyebrow="Configuração"
        icon={SettingsIcon}
        title="Ajustes"
        description="Identidade, aparência, segurança, dispositivos, notificações e integrações do Centro de Comando. Apenas interface nesta etapa."
        meta={
          <>
            <ToneChip tone="cyan">
              <Palette className="size-3" strokeWidth={2.2} />
              dark oficial
            </ToneChip>
            <ToneChip tone="red">
              <Fingerprint className="size-3" strokeWidth={2.2} />
              aprovação obrigatória
            </ToneChip>
            <ToneChip tone="green">
              <StatusDot tone="green" size="xs" />
              {tools.filter((tool) => tool.status === "connected").length} integrações conectadas
            </ToneChip>
          </>
        }
        actions={
          <>
            <Button variant="subtle" size="sm">
              <RotateCcw className="size-3" strokeWidth={2.2} />
              Restaurar
            </Button>
            <Button variant="default" size="sm">
              <Save className="size-3" strokeWidth={2.2} />
              Salvar
            </Button>
          </>
        }
      />

      <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
        {settingsSections.map((section, index) => (
          <Panel
            key={section.id}
            interactive
            sheen={false}
            className="group flex items-start gap-3 p-3"
            style={{ animation: `luma-fade-up 0.5s cubic-bezier(0.22,1,0.36,1) ${index * 55}ms both` }}
          >
            <span className={cn("grid size-9 shrink-0 place-items-center rounded-lg border", toneChip[section.tone])}>
              <section.icon className="size-[18px]" strokeWidth={1.8} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[12.5px] font-semibold text-foreground">{section.title}</p>
              <p className="mt-1 text-[10.5px] leading-relaxed text-muted-foreground">{section.detail}</p>
              <p className="hud-numeric mt-2 truncate text-[9.5px] text-subtle">{section.meta}</p>
            </div>
          </Panel>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Panel corners className="animate-fade-up self-start">
          <PanelHeader icon={UserCircle} title="Perfil do Proprietário" hint="Identidade no comando" meta={<ToneChip tone="cyan" className="text-[9.5px]">{owner.tier}</ToneChip>} />
          <div className="p-3.5">
            <div className="flex items-center gap-3">
              <span className="grid size-12 shrink-0 place-items-center rounded-full border border-primary/45 bg-[linear-gradient(140deg,rgba(0,229,255,0.22),rgba(22,139,255,0.3))] text-[15px] font-semibold text-foreground">
                {owner.initials}
              </span>
              <div className="min-w-0">
                <p className="hud-title text-[16px] text-foreground">{owner.name}</p>
                <p className="text-[10.5px] text-muted-foreground">
                  {owner.role} · {owner.location}, {owner.country}
                </p>
              </div>
            </div>

            <div className="mt-3 space-y-2">
              {[
                { id: "p1", label: "Tom de resposta", value: "objetivo e direto" },
                { id: "p2", label: "Fuso horário", value: "GMT-3 · São Paulo" },
                { id: "p3", label: "Idioma do sistema", value: "Português (Brasil)" },
                { id: "p4", label: "Autonomia concedida", value: "supervisionada" },
              ].map((row) => (
                <div
                  key={row.id}
                  className="flex items-center justify-between gap-2 rounded-md border border-hud-soft bg-void/35 px-2.5 py-1.5"
                >
                  <span className="text-[11px] text-muted-foreground">{row.label}</span>
                  <span className="hud-numeric text-[11px] text-primary">{row.value}</span>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        <div className="space-y-3">
          <Panel className="animate-fade-up">
            <PanelHeader icon={Palette} title="Aparência" hint="Tema, densidade e movimento" />
            <div className="space-y-3 p-3.5">
              <div>
                <p className="hud-label mb-2 text-[9px] text-subtle">Tema</p>
                <div className="grid gap-2 sm:grid-cols-3">
                  {appearanceOptions.map((option) => (
                    <div
                      key={option.id}
                      className={cn(
                        "rounded-md border p-2.5 transition-all duration-150 ease-hud",
                        option.active
                          ? "border-primary/60 bg-primary/10 shadow-glow-xs"
                          : "border-hud-soft bg-void/40 opacity-70",
                      )}
                    >
                      <div className="flex h-8 items-end gap-1">
                        <span className="h-full w-2 rounded-sm bg-[linear-gradient(180deg,rgba(0,229,255,0.7),rgba(22,139,255,0.35))]" />
                        <span className="h-3/4 w-2 rounded-sm bg-void/80" />
                        <span className="h-1/2 w-2 rounded-sm bg-violet/40" />
                      </div>
                      <p className="mt-2 text-[11px] text-foreground/90">{option.label}</p>
                      <p className="text-[9px] text-subtle">{option.hint}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <p className="hud-label mb-2 text-[9px] text-subtle">Densidade</p>
                <div className="flex flex-wrap gap-1.5">
                  {densityOptions.map((option) => (
                    <span
                      key={option.id}
                      className={cn(
                        "rounded-full border px-2.5 py-0.5 text-[10.5px]",
                        option.active
                          ? "border-primary/55 bg-primary/12 text-primary"
                          : "border-hud-soft bg-void/40 text-muted-foreground",
                      )}
                    >
                      {option.label}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between gap-3 rounded-md border border-hud-soft bg-void/35 px-2.5 py-2">
                <span>
                  <span className="block text-[11px] text-foreground/90">Animações do orb</span>
                  <span className="block text-[9.5px] text-subtle">Respeita prefers-reduced-motion</span>
                </span>
                <Switch defaultChecked aria-label="Animações do orb" />
              </div>
            </div>
          </Panel>

          <Panel className="animate-fade-up">
            <PanelHeader icon={Bell} title="Notificações" hint="Canais monitorados" tone="amber" />
            <div className="space-y-2 p-3.5">
              {notificationRows.map((row) => (
                <div
                  key={row.id}
                  className="flex items-center justify-between gap-3 rounded-md border border-hud-soft bg-void/35 px-2.5 py-2"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[11px] text-foreground/90">{row.label}</span>
                    <span className="block truncate text-[9.5px] text-subtle">{row.detail}</span>
                  </span>
                  <Switch defaultChecked={row.enabled} aria-label={row.label} />
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <ReadoutPanel
          icon={ShieldCheck}
          tone="red"
          title="Segurança"
          hint="Regras de autorização"
          rows={[
            { id: "s1", label: "Aprovação para escrita", value: "sempre", tone: "red", hint: "sem exceção por escopo" },
            { id: "s2", label: "Validade do token", value: "60 min", tone: "amber", hint: "renovação manual" },
            { id: "s3", label: "Auditoria", value: "imutável", tone: "violet", hint: "retenção permanente" },
            { id: "s4", label: "Acesso remoto", value: "controlado", tone: "cyan", hint: "sessão registrada" },
          ]}
        />

        <Panel className="animate-fade-up">
          <PanelHeader icon={Trash2} title="Zona de Cuidado" hint="Ações destrutivas demonstrativas" tone="red" />
          <div className="space-y-2.5 p-3.5">
            {[
              { id: "d1", label: "Revogar todas as autorizações", detail: "Tokens ativos expiram imediatamente." },
              { id: "d2", label: "Limpar memória temporária", detail: "Mantém coleções permanentes intactas." },
              { id: "d3", label: "Desconectar executor local", detail: "Interrompe execuções no PC Principal." },
            ].map((action) => (
              <div
                key={action.id}
                className="flex items-center justify-between gap-3 rounded-md border border-destructive/25 bg-destructive/[0.06] px-2.5 py-2"
              >
                <span className="min-w-0">
                  <span className="block truncate text-[11px] text-foreground/90">{action.label}</span>
                  <span className="block truncate text-[9.5px] text-subtle">{action.detail}</span>
                </span>
                <Button variant="danger" size="sm">
                  Executar
                </Button>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
};

export default SettingsPage;
