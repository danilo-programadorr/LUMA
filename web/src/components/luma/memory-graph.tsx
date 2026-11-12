import { cn } from "@/lib/utils";
import { toneColor, toneHsl } from "@/luma/tokens";
import type { Tone } from "@/luma/types";
import { Panel, PanelHeader } from "@/components/luma/panel";
import { Radar } from "lucide-react";

interface GraphNode {
  id: string;
  label: string;
  tone: Tone;
  weight: number;
  angle: number;
  radius: number;
}

const nodes: GraphNode[] = [
  { id: "produto", label: "produto", tone: "cyan", weight: 34, angle: -78, radius: 118 },
  { id: "engenharia", label: "engenharia", tone: "blue", weight: 41, angle: -22, radius: 128 },
  { id: "marketing", label: "marketing", tone: "green", weight: 18, angle: 34, radius: 112 },
  { id: "seguranca", label: "segurança", tone: "red", weight: 12, angle: 96, radius: 126 },
  { id: "conteudo", label: "conteúdo", tone: "violet", weight: 16, angle: 154, radius: 116 },
  { id: "preferencias", label: "preferências", tone: "amber", weight: 22, angle: 208, radius: 124 },
];

const CENTER_X = 220;
const CENTER_Y = 148;

const project = (angle: number, radius: number) => {
  const radians = (angle * Math.PI) / 180;
  return {
    x: CENTER_X + Math.cos(radians) * radius,
    y: CENTER_Y + Math.sin(radians) * radius * 0.62,
  };
};

interface MemoryGraphProps {
  className?: string;
}

/** Visual map of indexed memory collections orbiting the core. */
export const MemoryGraph = ({ className }: MemoryGraphProps) => (
  <Panel corners className={cn("animate-fade-up", className)}>
    <PanelHeader
      icon={Radar}
      title="Mapa de Conexões"
      hint="Coleções indexadas ao redor do núcleo"
      meta={<span className="hud-numeric text-[10px] text-subtle">48.210 vetores</span>}
    />
    <div className="p-3">
      <svg viewBox="0 0 440 300" className="h-[260px] w-full" role="img" aria-label="Mapa de conexões da memória">
        <defs>
          <radialGradient id="memory-core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={toneColor("cyan", 0.9)} />
            <stop offset="100%" stopColor={toneColor("cyan", 0.05)} />
          </radialGradient>
        </defs>

        {[0.34, 0.62, 0.9].map((scale) => (
          <ellipse
            key={scale}
            cx={CENTER_X}
            cy={CENTER_Y}
            rx={140 * scale}
            ry={92 * scale}
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth="0.6"
            strokeDasharray="2 5"
          />
        ))}

        {nodes.map((node) => {
          const point = project(node.angle, node.radius);
          return (
            <g key={`link-${node.id}`}>
              <line
                x1={CENTER_X}
                y1={CENTER_Y}
                x2={point.x}
                y2={point.y}
                stroke={toneColor(node.tone, 0.4)}
                strokeWidth="0.9"
                strokeDasharray="3 7"
                style={{ animation: `luma-dash ${16 + node.weight / 2}s linear infinite` }}
              />
            </g>
          );
        })}

        <circle cx={CENTER_X} cy={CENTER_Y} r="34" fill="url(#memory-core)" opacity="0.5" />
        <circle cx={CENTER_X} cy={CENTER_Y} r="20" fill="none" stroke={toneColor("cyan", 0.65)} strokeWidth="1" />
        <circle
          cx={CENTER_X}
          cy={CENTER_Y}
          r="27"
          fill="none"
          stroke={toneColor("cyan", 0.3)}
          strokeWidth="0.7"
          strokeDasharray="4 6"
          style={{ animation: "luma-spin-slow 22s linear infinite", transformOrigin: `${CENTER_X}px ${CENTER_Y}px` }}
        />
        <circle cx={CENTER_X} cy={CENTER_Y} r="7" fill={toneColor("cyan", 0.95)} />
        <text
          x={CENTER_X}
          y={CENTER_Y + 40}
          textAnchor="middle"
          fill="hsl(var(--foreground))"
          fontSize="9"
          letterSpacing="2.4"
          fontFamily="Rajdhani, sans-serif"
          fontWeight="600"
        >
          LUMA CORE
        </text>

        {nodes.map((node) => {
          const point = project(node.angle, node.radius);
          return (
            <g key={node.id}>
              <circle cx={point.x} cy={point.y} r="16" fill={toneColor(node.tone, 0.12)} />
              <circle cx={point.x} cy={point.y} r="16" fill="none" stroke={toneColor(node.tone, 0.5)} strokeWidth="0.8" />
              <circle cx={point.x} cy={point.y} r="4.4" fill={toneColor(node.tone, 0.95)} />
              <text
                x={point.x}
                y={point.y + 27}
                textAnchor="middle"
                fill={`hsl(${toneHsl[node.tone]})`}
                fontSize="8"
                letterSpacing="1.6"
                fontFamily="Rajdhani, sans-serif"
                fontWeight="600"
              >
                {node.label.toUpperCase()}
              </text>
              <text
                x={point.x}
                y={point.y + 38}
                textAnchor="middle"
                fill="hsl(var(--muted-foreground))"
                fontSize="7.5"
                fontFamily="JetBrains Mono, monospace"
              >
                {node.weight}%
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  </Panel>
);
