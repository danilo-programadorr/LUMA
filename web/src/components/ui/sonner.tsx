import { Toaster as Sonner, toast } from "sonner"

type ToasterProps = React.ComponentProps<typeof Sonner>

/** LUMA toast surface: dark translucent, cyan hairline, controlled glow. */
const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="dark"
      position="top-right"
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast hud-panel !w-[320px] !gap-2 !rounded-lg !border-hud-line !bg-void/92 !p-3 !text-foreground !shadow-panel backdrop-blur-xl",
          title: "!text-[12.5px] !font-medium !tracking-wide",
          description: "!text-[10.5px] !leading-relaxed !text-muted-foreground",
          actionButton:
            "!h-7 !rounded-md !border !border-primary/40 !bg-primary/12 !px-2.5 !text-[11px] !text-primary",
          cancelButton:
            "!h-7 !rounded-md !border !border-hud-line !bg-void/60 !px-2.5 !text-[11px] !text-muted-foreground",
          closeButton:
            "!border-hud-line !bg-void/80 !text-muted-foreground hover:!text-primary",
          success: "!border-success/45",
          error: "!border-destructive/45",
          warning: "!border-warning/45",
          info: "!border-accent/45",
        },
      }}
      {...props}
    />
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export { Toaster, toast }
