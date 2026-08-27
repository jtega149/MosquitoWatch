import type { ForecastWeekOption, RiskLevel, ZipForecast } from "./types";
import zipsJson from "./zips.json";

/**
 * Mock ZIP forecasts for the dashboard.
 * Swap `ZIPS` / `getZipData` for FastAPI responses later without changing pages.
 */
export const ZIPS: ZipForecast[] = zipsJson as ZipForecast[];

export const DATA_UPDATED = "Aug 21, 2026";

export const FORECAST_WEEKS: ForecastWeekOption[] = [
  { week: 30, label: "Week 30", range: "Jul 28 – Aug 3, 2026" },
  { week: 31, label: "Week 31", range: "Aug 4 – Aug 10, 2026" },
  { week: 32, label: "Next Week (Week 32)", range: "Aug 11 – Aug 17, 2026" },
  { week: 33, label: "Week 33", range: "Aug 18 – Aug 24, 2026" },
];

export const DEFAULT_WEEK = 32;
export const DEFAULT_ZIP = "10310";

const byZip = new Map(ZIPS.map((z) => [z.zip, z]));

export function scoreToLevel(score: number): RiskLevel {
  if (score >= 75) return "High";
  if (score >= 50) return "Elevated";
  if (score >= 25) return "Moderate";
  return "Low";
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

export function getZipData(
  zip: string,
  week: number = DEFAULT_WEEK,
): ZipForecast | undefined {
  const base = byZip.get(zip.trim());
  if (!base) return undefined;

  const point =
    base.weeklyHistory.find((w) => w.week === week) ??
    base.weeklyHistory.find((w) => w.week === base.forecastWeek) ??
    base.weeklyHistory[base.weeklyHistory.length - 1];

  const option = FORECAST_WEEKS.find((w) => w.week === week);
  const riskScore = point?.risk ?? base.riskScore;
  const riskLevel = scoreToLevel(riskScore);

  return {
    ...base,
    riskScore,
    riskLevel,
    forecastWeek: week,
    forecastRange: option?.range ?? base.forecastRange,
  };
}

export function getAllZips(week: number = DEFAULT_WEEK): ZipForecast[] {
  return ZIPS.map((z) => getZipData(z.zip, week)!);
}

export function searchZips(query: string, week: number = DEFAULT_WEEK): ZipForecast[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return getAllZips(week)
    .filter(
      (z) =>
        z.zip.includes(q) ||
        z.neighborhood.toLowerCase().includes(q) ||
        z.borough.toLowerCase().includes(q),
    )
    .slice(0, 8);
}

export const DATA_SOURCES = [
  {
    name: "NYC Health – West Nile Virus Data",
    description:
      "Laboratory-confirmed West Nile-positive mosquito detections by ZIP, published on the NYC Health West Nile Virus Activity page.",
    source: "NYC Department of Health and Mental Hygiene",
    dataType: "Surveillance (positive trap dates)",
    frequency: "Weekly during mosquito season",
    href: "https://www.nyc.gov/site/doh/health/health-topics/west-nile-virus-activity.page",
  },
  {
    name: "NOAA / Open-Meteo – Historical Weather",
    description:
      "Temperature, humidity, and rainfall at ZIP centroids used as lagged weather features for the forecast model.",
    source: "Open-Meteo daily archive (ERA5-style reanalysis)",
    dataType: "Weather (daily → weekly)",
    frequency: "Daily updates; rolled up by week",
    href: "https://open-meteo.com/",
  },
  {
    name: "NYC Open Data – Mosquito Control Events",
    description:
      "Public mosquito-control and spraying event records that can be shown as context alongside ZIP risk (not used in the current mock).",
    source: "NYC Open Data",
    dataType: "Control operations",
    frequency: "As published by the City",
    href: "https://opendata.cityofnewyork.us/",
  },
] as const;

export const PREVENTION_TIPS = [
  {
    title: "Eliminate Standing Water",
    description:
      "Dump buckets, planters, gutters, and toys weekly. Mosquitoes can breed in a bottle cap of water.",
    icon: "droplets" as const,
  },
  {
    title: "Use Repellent",
    description:
      "Apply EPA-registered repellent on exposed skin when outdoors, especially at dusk and dawn.",
    icon: "spray" as const,
  },
  {
    title: "Wear Protective Clothing",
    description:
      "Long sleeves and pants reduce bites during peak feeding hours in the evening.",
    icon: "shirt" as const,
  },
  {
    title: "Install Screens",
    description:
      "Keep windows and doors screened and in good repair so mosquitoes stay outside.",
    icon: "screen" as const,
  },
  {
    title: "Stay Informed",
    description:
      "Check this forecast weekly during mosquito season (May–October) and follow NYC Health advisories.",
    icon: "megaphone" as const,
  },
] as const;
