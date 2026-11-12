import { useEffect, useRef, useState } from "react";

interface CountUpOptions {
  duration?: number;
  decimals?: number;
  delay?: number;
}

/** Animates a number from 0 to `value` once mounted. Visual only. */
export function useCountUp(value: number, options: CountUpOptions = {}) {
  const { duration = 1100, decimals = 0, delay = 120 } = options;
  const [current, setCurrent] = useState(0);
  const frame = useRef<number | undefined>(undefined);

  useEffect(() => {
    const factor = 10 ** decimals;
    let start: number | null = null;

    const tick = (now: number) => {
      if (start === null) start = now;
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - progress) ** 3;
      setCurrent(Math.round(value * eased * factor) / factor);
      if (progress < 1) frame.current = requestAnimationFrame(tick);
    };

    const timeout = window.setTimeout(() => {
      frame.current = requestAnimationFrame(tick);
    }, delay);

    return () => {
      window.clearTimeout(timeout);
      if (frame.current) cancelAnimationFrame(frame.current);
    };
  }, [value, duration, decimals, delay]);

  return current;
}

