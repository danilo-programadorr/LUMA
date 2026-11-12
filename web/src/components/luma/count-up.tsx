import { cn } from "@/lib/utils";
import { useCountUp } from "@/luma/use-count-up";

interface CountUpProps {
  value: number;
  decimals?: number;
  duration?: number;
  delay?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
}

export const CountUp = ({
  value,
  decimals = 0,
  duration = 1100,
  delay = 120,
  suffix = "",
  prefix = "",
  className,
}: CountUpProps) => {
  const current = useCountUp(value, { duration, decimals, delay });

  return (
    <span className={cn("hud-numeric tabular-nums", className)}>
      {prefix}
      {current.toFixed(decimals)}
      {suffix}
    </span>
  );
};
