export type RiskLevel = "High" | "Elevated" | "Moderate" | "Low";

export type WeekPoint = {
  week: number;
  label: string;
  weekStart: string | null;
  risk: number;
  positiveCount: number;
};
