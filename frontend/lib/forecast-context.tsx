"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { DEFAULT_WEEK, FORECAST_WEEKS } from "./mock-data";
import type { ForecastWeekOption } from "./types";

type ForecastContextValue = {
  week: number;
  setWeek: (week: number) => void;
  option: ForecastWeekOption;
};

const ForecastContext = createContext<ForecastContextValue | null>(null);

export function ForecastProvider({ children }: { children: ReactNode }) {
  const [week, setWeek] = useState(DEFAULT_WEEK);
  const option = useMemo(
    () => FORECAST_WEEKS.find((w) => w.week === week) ?? FORECAST_WEEKS[2],
    [week],
  );

  return (
    <ForecastContext.Provider value={{ week, setWeek, option }}>
      {children}
    </ForecastContext.Provider>
  );
}

export function useForecastWeek() {
  const ctx = useContext(ForecastContext);
  if (!ctx) throw new Error("useForecastWeek must be used within ForecastProvider");
  return ctx;
}
