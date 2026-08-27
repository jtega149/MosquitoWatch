"use client";

import { useMemo, useState } from "react";
import { DEFAULT_ZIP, ZIPS, getZipData } from "@/lib/mock-data";
import { useForecastWeek } from "@/lib/forecast-context";
import { DetectionsBarChart } from "@/components/charts/DetectionsBarChart";
import { RiskLineChart } from "@/components/charts/RiskLineChart";
import type { WeekPoint } from "@/lib/types";

type RangeKey = "6w" | "3m" | "1y";

function sliceHistory(history: WeekPoint[], range: RangeKey, week: number): WeekPoint[] {
  const upTo = history.filter((p) => p.week <= week);
  if (range === "6w") return upTo.slice(-6);
  if (range === "3m") return upTo.slice(-13);
  return upTo;
}

export default function TrendsPage() {
  const { week } = useForecastWeek();
  const [zip, setZip] = useState(DEFAULT_ZIP);
  const [range, setRange] = useState<RangeKey>("6w");
  const data = getZipData(zip, week);
  const series = useMemo(
    () => (data ? sliceHistory(data.weeklyHistory, range, week) : []),
    [data, range, week],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm text-slate-300">
          ZIP
          <select
            value={zip}
            onChange={(e) => setZip(e.target.value)}
            className="h-9 rounded-lg border border-white/10 bg-[#131a2b] px-3 text-sm text-white outline-none ring-[#22c55e] focus:ring-2"
          >
            {ZIPS.map((z) => (
              <option key={z.zip} value={z.zip}>
                {z.zip} — {z.neighborhood}
              </option>
            ))}
          </select>
        </label>
        <div className="flex rounded-lg border border-white/10 bg-[#131a2b] p-1">
          {(
            [
              ["6w", "6 Weeks"],
              ["3m", "3 Months"],
              ["1y", "1 Year"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setRange(key)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                range === key ? "bg-[#22c55e] text-[#052e16]" : "text-slate-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <section className="rounded-2xl border border-white/10 bg-[#131a2b] p-5">
        <h2 className="text-sm font-semibold text-white">Elevated Risk Probability (%)</h2>
        <div className="mt-4 h-64">
          <RiskLineChart data={series} />
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-[#131a2b] p-5">
        <h2 className="text-sm font-semibold text-white">Positive Detections</h2>
        <div className="mt-4 h-56">
          <DetectionsBarChart data={series} />
        </div>
      </section>

      <p className="text-xs text-slate-500">
        Trends are based on laboratory-confirmed positive mosquito detections.
      </p>
    </div>
  );
}
