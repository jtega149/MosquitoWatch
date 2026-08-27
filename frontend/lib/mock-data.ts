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
      "Public mosquito-control and spraying event records shown as context. They are not currently consumed by the FastAPI forecast endpoints.",
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
