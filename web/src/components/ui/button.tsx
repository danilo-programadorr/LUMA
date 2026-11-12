import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md text-[12.5px] font-medium ring-offset-background transition-all duration-150 ease-hud focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-void disabled:pointer-events-none disabled:opacity-45 active:translate-y-[1px] [&_svg]:pointer-events-none [&_svg]:size-3.5 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-signature text-primary-foreground shadow-glow-sm hover:shadow-glow hover:brightness-110",
        outline:
          "border border-primary/45 bg-primary/[0.06] text-primary hover:border-primary hover:bg-primary/15 hover:shadow-glow-sm",
        subtle:
          "border border-hud-soft bg-hud-surface-raised text-foreground hover:border-primary/50 hover:bg-primary/10 hover:text-primary",
        ghost:
          "text-muted-foreground hover:bg-primary/10 hover:text-primary",
        danger:
          "border border-destructive/45 bg-destructive/10 text-destructive hover:border-destructive/80 hover:bg-destructive/20",
        success:
          "border border-success/45 bg-success/10 text-success hover:border-success/80 hover:bg-success/20",
        violet:
          "border border-violet/45 bg-violet/10 text-violet hover:border-violet/80 hover:bg-violet/20",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-3.5",
        xs: "h-6 px-2 text-[11px] rounded-[5px] [&_svg]:size-3",
        sm: "h-7 px-2.5 text-[11.5px] rounded-[6px]",
        lg: "h-10 px-5 text-[13px]",
        xl: "h-12 px-7 text-[14px]",
        icon: "size-9",
        "icon-sm": "size-7 rounded-[6px] [&_svg]:size-3.5",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

// eslint-disable-next-line react-refresh/only-export-components
export { Button, buttonVariants }
