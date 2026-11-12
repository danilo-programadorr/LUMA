
import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, Radar } from "lucide-react";

import { Panel } from "@/components/luma/panel";
import { LumaOrb } from "@/components/luma/luma-orb";
import { Button } from "@/components/ui/button";

const NotFound = () => {
  const location = useLocation();



  return (
    <Panel corners className="animate-scale-in relative overflow-hidden p-6 sm:p-10">
      <div className="relative flex flex-col items-center gap-4 text-center">
        <LumaOrb state="error" size={220} sublabel="SETOR NÃO ENCONTRADO" />
        <p className="hud-label text-[10px] tracking-[0.3em] text-destructive">
          erro 404 · rota inexistente
        </p>
        <h1 className="hud-title text-[26px] leading-tight text-foreground text-glow-soft sm:text-[32px]">
          Esta área do Centro de Comando não existe
        </h1>
        <p className="max-w-md text-[11.5px] leading-relaxed text-muted-foreground">
          A LUMA não localizou o módulo solicitado em{" "}
          <span className="hud-numeric text-primary">{location.pathname}</span>. Verifique o endereço
          ou volte para o painel principal.
        </p>
        <div className="mt-1 flex flex-wrap items-center justify-center gap-2">
          <Button asChild variant="default" size="lg">
            <Link to="/">
              <LayoutDashboard className="size-3.5" strokeWidth={2} />
              Voltar ao painel
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link to="/core">
              <Radar className="size-3.5" strokeWidth={2} />
              Abrir núcleo
            </Link>
          </Button>
        </div>
      </div>
    </Panel>
  );
};

export default NotFound;

