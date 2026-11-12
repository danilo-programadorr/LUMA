import { cn } from "@/lib/utils";

interface HudSkeletonProps {
  className?: string;
  rounded?: string;
}

export const HudSkeleton = ({ className, rounded = "rounded-md" }: HudSkeletonProps) => (
  <div
    aria-hidden
    className={cn(
      "hud-shimmer animate-shimmer border border-hud-soft bg-void/50",
      rounded,
      className,
    )}
  />
);

interface HudSkeletonStackProps {
  rows?: number;
  className?: string;
}

export const HudSkeletonStack = ({ rows = 4, className }: HudSkeletonStackProps) => (
  <div className={cn("space-y-2", className)}>
    {Array.from({ length: rows }).map((_, index) => (
      <div key={index} className="flex items-center gap-2.5">
        <HudSkeleton className="size-8 shrink-0" />
        <div className="flex-1 space-y-1.5">
          <HudSkeleton className="h-2.5 w-2/5" rounded="rounded-full" />
          <HudSkeleton className="h-2 w-3/5" rounded="rounded-full" />
        </div>
      </div>
    ))}
  </div>
);

export const HudSkeletonCard = ({ className }: { className?: string }) => (
  <div className={cn("hud-panel p-3.5", className)}>
    <div className="flex items-center gap-2.5">
      <HudSkeleton className="size-9 shrink-0" />
      <div className="flex-1 space-y-2">
        <HudSkeleton className="h-3 w-1/3" rounded="rounded-full" />
        <HudSkeleton className="h-2.5 w-2/3" rounded="rounded-full" />
      </div>
    </div>
    <HudSkeleton className="mt-3 h-1.5 w-full" rounded="rounded-full" />
  </div>
);
