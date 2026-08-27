export type RiskLevel = "High" | "Elevated" | "Moderate" | "Low";

export type Indicator = {
  value: string;
  count?: number;
  severity: RiskLevel;
};

export type WeekPoint = {
  week: number;
  label: string;
  weekStart: string | null;
  risk: number;
  positiveCount: number;
};

export type ZipForecast = {
  zip: string;
  borough: string;
  neighborhood: string;
  lat: number;
  lon: number;
  riskScore: number;
  riskLevel: RiskLevel;
  forecastWeek: number;
  forecastRange: string;
  indicators: {
    recentPositiveDetections: Indicator;
    temperature: Indicator;
    rainfall: Indicator;
    seasonality: Indicator;
  };
  weeklyHistory: WeekPoint[];
  aiInsight: string;
};

export type ForecastWeekOption = {
  week: number;
  label: string;
  range: string;
};
