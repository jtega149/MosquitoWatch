"use client";

import { Bell } from "lucide-react";
import { FORECAST_WEEKS } from "@/lib/mock-data";
import { useForecastWeek } from "@/lib/forecast-context";

export function Header() {
  const { week, setWeek } = useForecastWeek();

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-white/8 bg-[#0c1220] px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#22c55e] text-lg shadow-[0_0_18px_rgba(34,197,94,0.35)]">
          🦟
        </div>
        <div className="leading-tight">
          <div className="text-[15px] font-semibold tracking-tight text-white">
            MosquitoWatch NYC
          </div>
          <div className="text-xs text-slate-400">West Nile Virus Risk Forecaster</div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label className="sr-only" htmlFor="forecast-week">
          Forecast week
        </label>
        <select
          id="forecast-week"
          value={week}
          onChange={(e) => setWeek(Number(e.target.value))}
          className="h-9 rounded-lg border border-white/10 bg-[#131a2b] px-3 text-sm text-slate-100 outline-none ring-[#22c55e] focus:ring-2"
        >
          {FORECAST_WEEKS.map((w) => (
            <option key={w.week} value={w.week}>
              {w.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          aria-label="Notifications"
          className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-[#131a2b] text-slate-300 hover:text-white"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500" />
        </button>
      </div>
    </header>
  );
}
