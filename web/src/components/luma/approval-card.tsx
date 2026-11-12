import { useState } from "react";
import {
  Check,
  ChevronDown,
  Cpu,
  FolderKanban,
  ShieldAlert,
  ShieldCheck,
  Timer,
  X,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { toneChip, toneText } from "@/luma/tokens";
import type { Approval, ApprovalStateKey, RiskLevel, Tone } from "@/luma/types";
import { Panel } from "@/components/luma/panel";
import { StatusDot, ToneChip } from "@/components/luma/status-indicator";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useLuma } from "@/luma/luma-context";

const riskTone: Record<RiskLevel, Tone> = {
  baixo: "green",
  "médio": "amber",
  alto: "red",
};

const decisionMeta: Record<ApprovalStateKey, { label: string; tone: Tone }> = {
  pending: { label: "Aguardando autorização", tone: "amber" },
  granted: { label: "Autorizada", tone: "green" },
  denied: { label: "Negada", tone: "red" },
  expired: { label: "Expirada", tone: "slate" },
};

interface ApprovalCardProps {
  approval: Approval;
  variant?: "rail" | "full";
  /** Controlled decision override — lets pages move cards between tabs. */
  status?: ApprovalStateKey;
  onDecide?: (id: string, next: ApprovalStateKey) => void;
  className?: string;
}

/** Approval request with a purely demonstrative local authorization flow. */
export const ApprovalCard = ({
  approval,
  variant = "rail",
  status,
  onDecide,
  className,
}: ApprovalCardProps) => {
  const { pulse } = useLuma();
  const [localDecision, setLocalDecision] = useState<ApprovalStateKey>(approval.status);
  const [expanded, setExpanded] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const decision = status ?? localDecision;
  const Icon = approval.icon;
  const isRail = variant === "rail";
  const resolved = decision !== "pending";
  const meta = decisionMeta[decision];

  const handleApprove = () => {
    setLocalDecision("granted");
    onDecide?.(approval.id, "granted");
    setConfirmOpen(false);
    pulse("executing", 1600);
    toast.success("Autorização registrada", {
      description: `${approval.action} · demonstração visual`,
    });
  };

  const handleDeny = () => {
    setLocalDecision("denied");
    onDecide?.(approval.id, "denied");
    pulse("error", 1400);
    toast.error("Solicitação negada", {
      description: "Nenhuma ação externa foi executada.",
    });
  };

  return (
    <>
      <Panel
        interactive={!resolved}
        sheen={false}
        corners={approval.risk === "alto" && decision === "pending"}
        variant={approval.risk === "alto" && decision === "pending" ? "warning" : "default"}
        className={cn("relative overflow-hidden p-2.5", className)}
      >
        <span
          aria-hidden
          className={cn("absolute inset-y-0 left-0 w-[2px]", toneChip[riskTone[approval.risk]].split(" ")[0])}
        />

        <div className="flex items-start gap-2.5 pl-1">
          <span className={cn("grid size-8 shrink-0 place-items-center rounded-md border", toneChip[approval.tone])}>
            <Icon className="size-4" strokeWidth={1.8} />
          </span>

          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <p className="text-[11.5px] font-medium leading-snug text-foreground">
                {approval.action}
              </p>
              <span className="shrink-0 whitespace-nowrap text-[9.5px] text-subtle">
                {approval.requestedAt}
              </span>
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-subtle">
              <span className="inline-flex items-center gap-1">
                <Zap className="size-2.5" strokeWidth={2.2} />
                {approval.agent}
              </span>
              <span className="text-border">•</span>
              <span className="inline-flex items-center gap-1">
                <FolderKanban className="size-2.5" strokeWidth={2.2} />
                {approval.project}
              </span>
              <span className="text-border">•</span>
              <span className="inline-flex items-center gap-1">
                <Cpu className="size-2.5" strokeWidth={2.2} />
                {approval.device}
              </span>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              {resolved ? (
                <ToneChip tone={meta.tone}>
                  {decision === "granted" ? (
                    <Check className="size-2.5" strokeWidth={2.6} />
                  ) : decision === "denied" ? (
                    <X className="size-2.5" strokeWidth={2.6} />
                  ) : (
                    <Timer className="size-2.5" strokeWidth={2.2} />
                  )}
                  {meta.label}
                </ToneChip>
              ) : (
                <ToneChip tone="amber">
                  <StatusDot tone="amber" size="xs" />
                  {meta.label}
                </ToneChip>
              )}

              <ToneChip tone={riskTone[approval.risk]}>
                <ShieldAlert className="size-2.5" strokeWidth={2.2} />
                risco {approval.risk}
              </ToneChip>

              <button
                type="button"
                onClick={() => setExpanded((value) => !value)}
                className="inline-flex items-center gap-1 rounded-full border border-transparent px-1.5 py-0.5 text-[10px] text-muted-foreground transition-colors duration-150 ease-hud hover:border-primary/40 hover:text-primary"
              >
                Ver detalhes
                <ChevronDown
                  className={cn("size-2.5 transition-transform duration-220 ease-hud", expanded && "rotate-180")}
                  strokeWidth={2.2}
                />
              </button>
            </div>

            <div
              className={cn(
                "grid transition-all duration-300 ease-hud",
                expanded ? "mt-2 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
              )}
            >
              <div className="overflow-hidden">
                <div className="rounded-md border border-hud-soft bg-void/50 p-2">
                  <dl className="grid gap-1.5 text-[10px]">
                    <div className="flex items-center justify-between gap-2">
                      <dt className="text-subtle">Escopo</dt>
                      <dd className="hud-numeric truncate text-foreground/90">{approval.scope}</dd>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <dt className="text-subtle">Expiração</dt>
                      <dd className={toneText[meta.tone]}>{approval.expires}</dd>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <dt className="text-subtle">Dispositivo</dt>
                      <dd className="text-foreground/90">{approval.device}</dd>
                    </div>
                  </dl>
                </div>
              </div>
            </div>

            {!resolved && (
              <div className={cn("mt-2.5 flex items-center gap-1.5", isRail ? "" : "flex-wrap")}>
                <Button
                  size="sm"
                  variant="default"
                  className={cn(!isRail && "h-11 flex-1 text-[13px] font-semibold sm:h-9 sm:flex-none sm:text-[11.5px]")}
                  onClick={() => setConfirmOpen(true)}
                >
                  <ShieldCheck className="size-3" strokeWidth={2.2} />
                  Autorizar
                </Button>
                <Button
                  size="sm"
                  variant="subtle"
                  className={cn(!isRail && "h-11 text-[13px] sm:h-7 sm:text-[11.5px]")}
                  onClick={() => setExpanded((value) => !value)}
                >
                  Detalhes
                </Button>
                {!isRail && (
                  <Button size="sm" variant="danger" className="h-11 text-[13px] sm:h-7 sm:text-[11.5px]" onClick={handleDeny}>
                    <X className="size-3" strokeWidth={2.4} />
                    Negar
                  </Button>
                )}
                <span className="ml-auto hidden items-center gap-1 text-[9.5px] text-subtle sm:inline-flex">
                  <Timer className="size-2.5" strokeWidth={2.2} />
                  {approval.expires}
                </span>
              </div>
            )}
          </div>
        </div>
      </Panel>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent className="border-primary/40 bg-void/95 shadow-glow backdrop-blur-xl">
          <AlertDialogHeader>
            <AlertDialogTitle className="hud-title text-[17px] tracking-wide text-foreground">
              Confirmar autorização
            </AlertDialogTitle>
            <AlertDialogDescription className="text-[12px] text-muted-foreground">
              Você está autorizando <span className="text-primary">{approval.agent}</span> a executar
              <span className="hud-numeric text-foreground"> {approval.scope}</span> em {approval.device}.
              Esta é uma demonstração de interface: nenhuma ação real será executada.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="rounded-md border border-hud-soft bg-void/60 p-2.5 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-subtle">Risco classificado</span>
              <span className={cn("font-medium capitalize", toneText[riskTone[approval.risk]])}>
                {approval.risk}
              </span>
            </div>
            <div className="mt-1.5 flex items-center justify-between">
              <span className="text-subtle">Validade</span>
              <span className="text-foreground/90">{approval.expires}</span>
            </div>
          </div>
          <AlertDialogFooter className="gap-2 sm:space-x-0">
            <AlertDialogCancel className="border-hud-line bg-transparent text-muted-foreground hover:bg-primary/10 hover:text-primary">
              Cancelar
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleApprove}
              className="bg-signature text-primary-foreground shadow-glow-sm hover:brightness-110"
            >
              Autorizar execução
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};
