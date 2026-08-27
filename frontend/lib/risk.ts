import type { RiskLevel } from "./types";

export function scoreToLevel(score: number): RiskLevel {
  if (score >= 75) return "High";
  if (score >= 50) return "Elevated";
  if (score >= 25) return "Moderate";
  return "Low";
}

export function parseRiskLevel(value: string, score?: number): RiskLevel {
  if (value === "High" || value === "Elevated" || value === "Moderate" || value === "Low") {
    return value;
  }
  return scoreToLevel(score ?? 0);
}

export function riskColor(levelOrScore: RiskLevel | number): string {
  const level =
    typeof levelOrScore === "number" ? scoreToLevel(levelOrScore) : levelOrScore;
  switch (level) {
    case "High":
      return "#ef4444";
    case "Elevated":
      return "#f97316";
    case "Moderate":
      return "#eab308";
    case "Low":
      return "#22c55e";
  }
}

export function countSeverity(count: number): RiskLevel {
  if (count >= 6) return "High";
  if (count >= 3) return "Elevated";
  if (count >= 1) return "Moderate";
  return "Low";
}

export function temperatureSeverity(celsius: number): RiskLevel {
  if (celsius >= 27) return "High";
  if (celsius >= 24) return "Elevated";
  if (celsius >= 20) return "Moderate";
  return "Low";
}

export function rainfallSeverity(mm: number): RiskLevel {
  if (mm >= 50) return "High";
  if (mm >= 25) return "Elevated";
  if (mm >= 10) return "Moderate";
  return "Low";
}

export function seasonalityFromWeek(week: number): { value: string; severity: RiskLevel } {
  if (week >= 22 && week <= 36) {
    return { value: "Peak mosquito season (Jun–Sep)", severity: "Elevated" };
  }
  if (week >= 18 && week <= 43) {
    return { value: "Mosquito season (May–Oct)", severity: "Moderate" };
  }
  return { value: "Off-season", severity: "Low" };
}
