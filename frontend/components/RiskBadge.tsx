import { riskColor } from "@/lib/risk";
import type { RiskLevel } from "@/lib/types";

type Size = "sm" | "md" | "lg";

export function RiskBadge({
  level,
  size = "sm",
}: {
  level: RiskLevel;
  size?: Size;
}) {
  const color = riskColor(level);
  const pad = size === "lg" ? "px-3 py-1 text-sm" : size === "md" ? "px-2.5 py-0.5 text-xs" : "px-2 py-0.5 text-[11px]";
  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold uppercase tracking-wide ${pad}`}
      style={{ backgroundColor: `${color}22`, color, border: `1px solid ${color}55` }}
    >
      {level}
    </span>
  );
}
