"use client";

import { formatDayShort } from "@/lib/dates";
import { parseRiskLevel, riskColor } from "@/lib/risk";
import type { ApiForecastDay } from "@/lib/api";
import { RiskBadge } from "./RiskBadge";

export function SevenDayForecast({
  days,
}: {
  days: ApiForecastDay[];
}) {

  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Next 7 days · WNV mosquito activity
      </div>
      <p className="mt-1 text-[11px] text-slate-500">
        One weekly model score applied across the forecast week (not seven daily models).
      </p>
      <ul className="mt-3 space-y-1.5">
        {days.map((day) => {
          const level = parseRiskLevel(day.risk_level, day.risk_score);
          const date = new Date(`${day.date}T00:00:00Z`);
          return (
            <li
              key={day.date}
              className="flex items-center justify-between rounded-lg border border-white/5 bg-[#0a0e1a] px-2.5 py-1.5"
            >
              <span className="text-xs text-slate-300">{formatDayShort(date)}</span>
              <span className="flex items-center gap-2">
                <span className="text-xs font-semibold" style={{ color: riskColor(level) }}>
                  {day.risk_score}%
                </span>
                <RiskBadge level={level} />
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
