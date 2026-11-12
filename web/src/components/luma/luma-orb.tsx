import { useEffect, useMemo, useRef, type CSSProperties } from "react";

import { cn } from "@/lib/utils";
import { orbStateMeta, toneColor, toneHsl } from "@/luma/tokens";
import type { LumaState } from "@/luma/types";

interface LumaOrbProps {
  state?: LumaState;
  size?: number;
  className?: string;
  showLabel?: boolean;
  label?: string;
  sublabel?: string;
  gyroscope?: boolean;
}

type Vec3 = [number, number, number];

const fibonacciSphere = (count: number): Vec3[] => {
  const points: Vec3[] = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let index = 0; index < count; index += 1) {
    const y = count === 1 ? 0 : 1 - (index / (count - 1)) * 2;
    const ring = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = golden * index;
    points.push([Math.cos(theta) * ring, y, Math.sin(theta) * ring]);
  }
  return points;
};

/** Connects each node to its nearest neighbours — the neural lattice look. */
const buildLattice = (points: Vec3[], links: number) => {
  const edges: [number, number][] = [];
  for (let a = 0; a < points.length; a += 1) {
    const nearest: { index: number; distance: number }[] = [];
    for (let b = a + 1; b < points.length; b += 1) {
      const dx = points[a][0] - points[b][0];
      const dy = points[a][1] - points[b][1];
      const dz = points[a][2] - points[b][2];
      nearest.push({ index: b, distance: dx * dx + dy * dy + dz * dz });
    }
    nearest.sort((m, n) => m.distance - n.distance);
    nearest.slice(0, links).forEach((entry) => edges.push([a, entry.index]));
  }
  return edges;
};

interface OrbitRingProps {
  rx: number;
  ry: number;
  rotate: number;
  strength: "ring" | "ring-soft" | "accent-faint";
  speed?: string;
  dash?: string;
  node?: boolean;
  nodeStrength?: string;
}

/** Flat SVG orbit — rotating in 2D keeps rasterization reliable everywhere. */
const OrbitRing = ({
  rx,
  ry,
  rotate,
  strength,
  speed = "animate-orbit-slow",
  dash = "2.2 4.4",
  node = false,
  nodeStrength = "var(--orb-accent)",
}: OrbitRingProps) => (
  <svg
    viewBox="0 0 100 100"
    aria-hidden
    className={cn("pointer-events-none absolute inset-0 size-full", speed)}
  >
    <g transform={`rotate(${rotate} 50 50)`}>
      <ellipse
        cx="50"
        cy="50"
        rx={rx}
        ry={ry}
        fill="none"
        strokeWidth="0.5"
        strokeDasharray={dash}
        strokeLinecap="round"
        style={{ stroke: `var(--orb-${strength})` }}
      />
      {node && (
        <circle cx={50 + rx * 0.82} cy={50 + ry * 0.4} r="1.4" style={{ fill: nodeStrength }} />
      )}
      {node && (
        <circle cx={50 - rx * 0.9} cy={50 - ry * 0.3} r="1" style={{ fill: nodeStrength }} />
      )}
    </g>
  </svg>
);

/**
 * LUMA CORE — the animated brain of the command center.
 * Pure canvas + SVG + CSS, no 3D engine.
 */
export const LumaOrb = ({
  state = "idle",
  size = 340,
  className,
  showLabel = true,
  label = "LUMA",
  sublabel = "CORE",
  gyroscope = true,
}: LumaOrbProps) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const speedRef = useRef(orbStateMeta[state].speed);
  const hueRef = useRef(toneHsl[orbStateMeta[state].tone]);

  const nodeCount = size < 220 ? 72 : size < 360 ? 104 : 132;
  const points = useMemo(() => fibonacciSphere(nodeCount), [nodeCount]);
  const lattice = useMemo(() => buildLattice(points, 2), [points]);

  const meta = orbStateMeta[state];
  const accentVars = {
    "--orb-accent": toneColor(meta.tone),
    "--orb-accent-soft": toneColor(meta.tone, 0.26),
    "--orb-accent-faint": toneColor(meta.tone, 0.1),
    "--orb-ring": toneColor(meta.tone, 0.44),
    "--orb-ring-soft": toneColor(meta.tone, 0.22),
  } as CSSProperties;

  useEffect(() => {
    speedRef.current = orbStateMeta[state].speed;
    hueRef.current = toneHsl[orbStateMeta[state].tone];
  }, [state]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const maxBackingEdge = 480;
    let devicePixelRatio = 1;
    let frame = 0;
    let angle = 0.6;
    let previous = performance.now();

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const cssEdge = Math.max(1, Math.min(rect.width, rect.height) || rect.width);
      devicePixelRatio = Math.min(
        window.devicePixelRatio || 1,
        2,
        maxBackingEdge / cssEdge,
      );
      canvas.width = Math.max(1, Math.floor(rect.width * devicePixelRatio));
      canvas.height = Math.max(1, Math.floor(rect.height * devicePixelRatio));
    };

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();

    const tilt = 0.36;
    const cosTilt = Math.cos(tilt);
    const sinTilt = Math.sin(tilt);
    const projected: { x: number; y: number; depth: number }[] = points.map(() => ({
      x: 0,
      y: 0,
      depth: 0,
    }));

    const render = (currentAngle: number) => {
      const width = canvas.width;
      const height = canvas.height;
      if (!width || !height) return;

      const centerX = width / 2;
      const centerY = height / 2;
      const radius = Math.min(width, height) * 0.46;
      const hue = hueRef.current;

      context.clearRect(0, 0, width, height);

      const cosA = Math.cos(currentAngle);
      const sinA = Math.sin(currentAngle);

      for (let index = 0; index < points.length; index += 1) {
        const [x, y, z] = points[index];
        const rx = x * cosA + z * sinA;
        const rz = -x * sinA + z * cosA;
        const ry = y * cosTilt - rz * sinTilt;
        const rz2 = y * sinTilt + rz * cosTilt;
        const perspective = 1 / (1 + rz2 * 0.32);
        projected[index].x = centerX + rx * radius * perspective;
        projected[index].y = centerY + ry * radius * perspective;
        projected[index].depth = (rz2 + 1) / 2;
      }

      /* sphere body — gives the globe a solid volume */
      const body = context.createRadialGradient(
        centerX - radius * 0.3,
        centerY - radius * 0.34,
        radius * 0.04,
        centerX,
        centerY,
        radius,
      );
      body.addColorStop(0, "rgba(12, 44, 68, 0.94)");
      body.addColorStop(0.58, "rgba(6, 25, 39, 0.9)");
      body.addColorStop(1, "rgba(2, 10, 18, 0.6)");
      context.fillStyle = body;
      context.beginPath();
      context.arc(centerX, centerY, radius, 0, Math.PI * 2);
      context.fill();

      /* core bloom */
      const bloom = context.createRadialGradient(
        centerX,
        centerY,
        0,
        centerX,
        centerY,
        radius,
      );
      bloom.addColorStop(0, `hsla(${hue}, 0.3)`);
      bloom.addColorStop(0.5, `hsla(${hue}, 0.12)`);
      bloom.addColorStop(1, `hsla(${hue}, 0.02)`);
      context.fillStyle = bloom;
      context.beginPath();
      context.arc(centerX, centerY, radius, 0, Math.PI * 2);
      context.fill();

      /* rim light */
      context.strokeStyle = `hsla(${hue}, 0.5)`;
      context.lineWidth = Math.max(0.8, width / 480);
      context.beginPath();
      context.arc(centerX, centerY, radius, 0, Math.PI * 2);
      context.stroke();

      /* neural links */
      context.lineWidth = Math.max(0.6, width / 820);
      for (let index = 0; index < lattice.length; index += 1) {
        const [a, b] = lattice[index];
        const from = projected[a];
        const to = projected[b];
        const depth = (from.depth + to.depth) / 2;
        context.strokeStyle = `hsla(${hue}, ${(0.1 + depth * 0.34).toFixed(3)})`;
        context.beginPath();
        context.moveTo(from.x, from.y);
        context.lineTo(to.x, to.y);
        context.stroke();
      }

      /* nodes */
      const nodeScale = width / 260;
      for (let index = 0; index < projected.length; index += 1) {
        const node = projected[index];
        const nodeRadius = Math.max(0.8, (1 + node.depth * 3) * nodeScale * 0.6);
        context.fillStyle = `hsla(${hue}, ${(0.28 + node.depth * 0.66).toFixed(3)})`;
        context.beginPath();
        context.arc(node.x, node.y, nodeRadius, 0, Math.PI * 2);
        context.fill();
      }
    };

    const loop = (now: number) => {
      const delta = Math.min(64, now - previous);
      previous = now;
      angle += (delta / 1000) * speedRef.current;
      if (document.visibilityState === "visible") render(angle);
      frame = requestAnimationFrame(loop);
    };

    if (reduceMotion) {
      render(angle);
    } else {
      frame = requestAnimationFrame(loop);
    }

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [points, lattice]);

  return (
    <div
      role="img"
      aria-label={`LUMA CORE — estado ${meta.label}`}
      className={cn("relative aspect-square select-none", className)}
      style={
        {
          "--orb-size": `${size}px`,
          width: `min(100%, ${size}px)`,
          maxWidth: "100%",
          ...accentVars,
        } as CSSProperties
      }
    >
      {/* outer bloom */}
      <div
        aria-hidden
        className="absolute inset-[-8%] animate-breathe rounded-full bg-[radial-gradient(circle_at_50%_50%,var(--orb-accent-soft),transparent_68%)]"
      />

      {/* state ripples */}
      {(state === "listening" || state === "executing" || state === "thinking") && (
        <>
          <div
            aria-hidden
            className="absolute inset-[6%] rounded-full border border-[color:var(--orb-ring)] animate-ring"
          />
          <div
            aria-hidden
            className="absolute inset-[6%] rounded-full border border-[color:var(--orb-ring-soft)] animate-ring"
            style={{ animationDelay: "1.4s" }}
          />
        </>
      )}

      {/* gyroscope orbits */}
      {gyroscope && (
        <>
          <OrbitRing rx={46} ry={13} rotate={-22} strength="ring" node />
          <OrbitRing rx={42} ry={17} rotate={32} strength="ring-soft" speed="animate-orbit-reverse" node />
          <OrbitRing rx={14} ry={45} rotate={-18} strength="accent-faint" speed="animate-orbit" />
          <OrbitRing rx={30} ry={30} rotate={0} strength="accent-faint" speed="animate-orbit-reverse" dash="1.8 5" />
        </>
      )}

      {/* neural sphere */}
      {/* neural sphere — the wrapper keeps the canvas square regardless of
          its backing-store attributes (prevents a resize feedback loop). */}
      <div className="absolute inset-x-[11%] top-1/2 aspect-square -translate-y-1/2">
        <canvas ref={canvasRef} aria-hidden className="block size-full" />
      </div>

      {/* inner light + core highlight (never hides the lattice) */}
      <div
        aria-hidden
        className="absolute inset-[13%] rounded-full bg-[radial-gradient(circle_at_36%_22%,var(--orb-accent-faint),transparent_48%)]"
      />
      <div
        aria-hidden
        className="absolute inset-[30%] rounded-full bg-[radial-gradient(circle_at_50%_50%,var(--orb-accent-soft),transparent_76%)]"
      />

      {/* scan sweep */}
      <div aria-hidden className="absolute inset-[13%] overflow-hidden rounded-full opacity-60">
        <div className="absolute inset-x-0 top-0 h-1/2 animate-sweep bg-[linear-gradient(180deg,transparent,var(--orb-accent-soft),transparent)]" />
      </div>

      {showLabel && (
        <div className="absolute inset-0 grid place-items-center">
          <div className="text-center">
            <div className="hud-title pl-[0.42em] text-[clamp(15px,calc(var(--orb-size)*0.135),48px)] leading-none tracking-[0.42em] text-foreground text-glow">
              {label}
            </div>
            <div className="hud-label mt-1 pl-[0.5em] text-[clamp(8px,calc(var(--orb-size)*0.036),13px)] tracking-[0.5em] text-primary/90">
              {sublabel}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
