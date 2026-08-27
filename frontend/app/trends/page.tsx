"use client";

import { useEffect, useMemo, useState } from "react";
import { DEFAULT_ZIP, useForecastData } from "@/lib/forecast-context";
import { parseRiskLevel, riskColor } from "@/lib/risk";
import { DetectionsBarChart } from "@/components/charts/DetectionsBarChart";
import { RiskBadge } from "@/components/RiskBadge";
import type { ApiPrediction, ApiTrendPoint } from "@/lib/api";
import type { WeekPoint } from "@/lib/types";

type RangeKey = "6w" | "3m" | "1y";

function sliceHistory(history: ApiTrendPoint[], range: RangeKey): ApiTrendPoint[] {
  const sorted = [...history].sort((a, b) => a.year - b.year || a.week - b.week);
  if (range === "6w") return sorted.slice(-6);
  if (range === "3m") return sorted.slice(-13);
  return sorted.slice(-52);
}

function toPoints(history: ApiTrendPoint[]): WeekPoint[] {
  return history.map((row) => ({
    week: row.week,
    label: `${String(row.year).slice(2)} W${row.week}`,
    weekStart: null,
    risk: 0,
    positiveCount: row.positive_detections,
  }));
}

export default function TrendsPage() {
  const { zips, loadTrends, loadPrediction, getForecast, forecastRange } = useForecastData();
  const [zip, setZip] = useState(DEFAULT_ZIP);
  const [range, setRange] = useState<RangeKey>("6w");
  const [history, setHistory] = useState<ApiTrendPoint[]>([]);
  const [prediction, setPrediction] = useState<ApiPrediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const selectedZip =
    zips.length === 0 || zips.some((z) => z.zip_code === zip) ? zip : zips[0].zip_code;

  useEffect(() => {
    let cancelled = false;

    void Promise.all([loadTrends(selectedZip), loadPrediction(selectedZip).catch(() => null)])
      .then(([trends, pred]) => {
        if (cancelled) return;
        setHistory(trends.history);
        setPrediction(pred);
        setError(null);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setHistory([]);
        setPrediction(null);
        setLoading(false);
        setError(err instanceof Error ? err.message : "Could not load trends.");
      });

    return () => {
      cancelled = true;
    };
  }, [selectedZip, loadTrends, loadPrediction]);

  const series = useMemo(() => toPoints(sliceHistory(history, range)), [history, range]);
  const mapForecast = getForecast(selectedZip);
  const score = prediction?.risk_score ?? mapForecast?.risk_score;
  const level =
    score != null
      ? parseRiskLevel(prediction?.risk_level ?? mapForecast?.risk_level ?? "", score)
      : null;

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm text-slate-300">
          ZIP
          <select
            value={selectedZip}
            onChange={(e) => setZip(e.target.value)}
            className="h-9 rounded-lg border border-white/10 bg-[#131a2b] px-3 text-sm text-white outline-none ring-[#22c55e] focus:ring-2"
          >
            {zips.map((z) => (
              <option key={z.zip_code} value={z.zip_code}>
                {z.zip_code} — {z.areas}
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
        <h2 className="text-sm font-semibold text-white">Next 7 days — elevated WNV activity</h2>
        {level && score != null ? (
          <div className="mt-4 flex items-end justify-between">
            <div>
              <div className="text-4xl font-semibold" style={{ color: riskColor(level) }}>
                {score}%
              </div>
              <p className="mt-1 text-xs text-slate-500">{forecastRange}</p>
            </div>
            <RiskBadge level={level} size="lg" />
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-400">
            {loading ? "Loading forecast…" : "No next-week risk score for this ZIP."}
          </p>
        )}
        <p className="mt-3 text-xs text-slate-500">
          Historical weekly risk probabilities are not served by the API, so this page shows the
          live next-week score plus confirmed positive detections over time.
        </p>
      </section>

      <section className="rounded-2xl border border-white/10 bg-[#131a2b] p-5">
        <h2 className="text-sm font-semibold text-white">Positive Detections</h2>
        <div className="mt-4 h-56">
          {loading ? (
            <p className="text-sm text-slate-400">Loading history…</p>
          ) : error ? (
            <p className="text-sm text-red-400">{error}</p>
          ) : series.length ? (
            <DetectionsBarChart data={series} />
          ) : (
            <p className="text-sm text-slate-400">No detection history for this ZIP.</p>
          )}
        </div>
      </section>

      <p className="text-xs text-slate-500">
        Trends are based on laboratory-confirmed positive mosquito detections from the backend
        history table.
      </p>
    </div>
  );
}
