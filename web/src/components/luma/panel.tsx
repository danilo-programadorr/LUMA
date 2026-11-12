import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";
import { toneChip } from "@/luma/tokens";
import type { Tone } from "@/luma/types";

const panelVariants = cva("hud-panel overflow-hidden", {
  variants: {
    variant: {
      default: "",
      raised: "bg-hud-raised",
      solid: "bg-void/70",
      spotlight: "bg-[linear-gradient(150deg,rgba(0,229,255,0.09),rgba(4,24,38,0.86)_46%)]",
      warning: "border-warning/40 bg-[linear-gradient(150deg,rgba(255,183,43,0.1),rgba(4,24,38,0.88)_52%)]",
    },
    interactive: {
      true: "hud-panel-interactive",
      false: "",
    },
  },
  defaultVariants: { variant: "default", interactive: false },
});

export interface PanelProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof panelVariants> {
  corners?: boolean;
  sheen?: boolean;
}

const Panel = React.forwardRef<HTMLDivElement, PanelProps>(
  ({ className, variant, interactive, corners = false, sheen = true, children, ...props }, ref) => (
    <div ref={ref} className={cn(panelVariants({ variant, interactive }), className)} {...props}>
      {sheen && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-primary/45 to-transparent"
        />
      )}
      {corners && (
        <>
          <span
            aria-hidden
            className="pointer-events-none absolute left-0 top-0 h-3.5 w-3.5 rounded-tl-[3px] border-l border-t border-primary/70"
          />
          <span
            aria-hidden
            className="pointer-events-none absolute bottom-0 right-0 h-3.5 w-3.5 rounded-br-[3px] border-b border-r border-primary/70"
          />
        </>
      )}
      <div className="relative">{children}</div>
    </div>
  ),
);
Panel.displayName = "Panel";

interface PanelHeaderProps {
  title: string;
  icon?: LucideIcon;
  tone?: Tone;
  hint?: string;
  meta?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const PanelHeader = ({
  title,
  icon: Icon,
  tone = "cyan",
  hint,
  meta,
  action,
  className,
}: PanelHeaderProps) => (
  <div
    className={cn(
      "flex items-center gap-2.5 border-b border-hud-soft px-3.5 py-2.5",
      className,
    )}
  >
    {Icon && (
      <span
        className={cn(
          "grid size-6 shrink-0 place-items-center rounded-md border",
          toneChip[tone],
        )}
      >
        <Icon className="size-3.5" strokeWidth={1.8} />
      </span>
    )}
    <div className="flex min-w-0 items-baseline gap-2">
      <h2 className="hud-label text-[10.5px] text-foreground/90">{title}</h2>
      {hint && (
        <span className="hidden truncate text-[10px] text-subtle sm:inline">{hint}</span>
      )}
    </div>
    <div className="ml-auto flex shrink-0 items-center gap-2">
      {meta}
      {action}
    </div>
  </div>
);

interface PanelActionProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: LucideIcon;
}

export const PanelAction = ({
  children,
  icon: Icon,
  className,
  ...props
}: PanelActionProps) => (
  <button
    type="button"
    className={cn(
      "group inline-flex items-center gap-1 rounded-full border border-transparent px-2 py-0.5 text-[10.5px] font-medium text-muted-foreground transition-colors duration-150 ease-hud hover:border-primary/40 hover:bg-primary/10 hover:text-primary",
      className,
    )}
    {...props}
  >
    {children}
    {Icon && (
      <Icon
        className="size-3 transition-transform duration-220 ease-hud group-hover:translate-x-0.5"
        strokeWidth={1.9}
      />
    )}
  </button>
);

export const PanelBody = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("p-3.5", className)} {...props} />
);

export const PanelGrid = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("grid gap-2.5 p-3.5", className)} {...props} />
);

interface PanelLinkProps {
  to: string;
  children: React.ReactNode;
  className?: string;
  icon?: LucideIcon;
}

export const PanelLink = ({ to, children, className }: PanelLinkProps) => (
  <Link
    to={to}
    className={cn(
      "group inline-flex items-center gap-1 rounded-full border border-transparent px-2 py-0.5 text-[10.5px] font-medium text-muted-foreground transition-colors duration-150 ease-hud hover:border-primary/40 hover:bg-primary/10 hover:text-primary",
      className,
    )}
  >
    {children}
  </Link>
);

export { Panel };
