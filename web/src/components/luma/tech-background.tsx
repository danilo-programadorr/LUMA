import { cn } from "@/lib/utils";

const particles = [
  { top: "12%", left: "18%", size: 2, delay: "0s", duration: "7.5s" },
  { top: "26%", left: "62%", size: 1.5, delay: "1.1s", duration: "9s" },
  { top: "44%", left: "34%", size: 2.5, delay: "2.2s", duration: "8.2s" },
  { top: "62%", left: "78%", size: 1.5, delay: "0.6s", duration: "10.5s" },
  { top: "74%", left: "12%", size: 2, delay: "1.8s", duration: "8.8s" },
  { top: "18%", left: "86%", size: 1, delay: "3s", duration: "9.6s" },
  { top: "56%", left: "52%", size: 1.5, delay: "2.6s", duration: "7.8s" },
  { top: "86%", left: "44%", size: 2.5, delay: "0.9s", duration: "11s" },
  { top: "34%", left: "8%", size: 1, delay: "3.4s", duration: "8.4s" },
  { top: "8%", left: "42%", size: 1.5, delay: "1.4s", duration: "9.2s" },
];

/** Ambient command-center atmosphere: tech grid, radial glows, drifting particles. */
export const TechBackground = ({ className }: { className?: string }) => (
  <div aria-hidden className={cn("pointer-events-none fixed inset-0 -z-10 overflow-hidden", className)}>
    <div className="absolute inset-0 hud-grid-layer opacity-[0.5]" />
    <div className="absolute inset-0 hud-dots-layer opacity-[0.22]" />

    <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_-10%,rgba(0,168,255,0.16),transparent_58%)]" />
    <div className="absolute inset-0 bg-[radial-gradient(circle_at_88%_108%,rgba(140,92,255,0.09),transparent_56%)]" />
    <div className="absolute inset-0 bg-[radial-gradient(circle_at_10%_96%,rgba(0,229,255,0.07),transparent_52%)]" />

    <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/45 to-transparent" />
    <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-accent/35 to-transparent" />

    {particles.map((particle, index) => (
      <span
        key={index}
        className="absolute rounded-full bg-primary/70 animate-float"
        style={{
          top: particle.top,
          left: particle.left,
          width: `${particle.size * 2}px`,
          height: `${particle.size * 2}px`,
          animationDelay: particle.delay,
          animationDuration: particle.duration,
          boxShadow: "0 0 12px 2px rgba(0,229,255,0.35)",
        }}
      />
    ))}

    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_42%,rgba(2,10,18,0.72)_100%)]" />

    <span className="absolute left-4 top-4 h-5 w-5 border-l border-t border-primary/25" />
    <span className="absolute right-4 top-4 h-5 w-5 border-r border-t border-primary/25" />
    <span className="absolute bottom-4 left-4 h-5 w-5 border-b border-l border-primary/25" />
    <span className="absolute bottom-4 right-4 h-5 w-5 border-b border-r border-primary/25" />
  </div>
);
