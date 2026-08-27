"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  fetchForecasts,
  fetchHealth,
  fetchPrediction,
  fetchTrends,
  fetchZips,
  type ApiForecast,
  type ApiPrediction,
  type ApiTrends,
  type ApiZip,
} from "./api";
import { FORECAST_YEAR, formatWeekRange } from "./dates";

export const DEFAULT_ZIP = "10310";

type Status = "loading" | "ready" | "error";

type ForecastContextValue = {
  status: Status;
  error: string | null;
  zips: ApiZip[];
  forecastsByZip: Map<string, ApiForecast>;
  forecastWeek: number | null;
  forecastYear: number;
  forecastRange: string;
  getZip: (zip: string) => ApiZip | undefined;
  getForecast: (zip: string) => ApiForecast | undefined;
  loadPrediction: (zip: string) => Promise<ApiPrediction>;
  loadTrends: (zip: string) => Promise<ApiTrends>;
  reload: () => void;
};

const ForecastContext = createContext<ForecastContextValue | null>(null);

export function ForecastProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [zips, setZips] = useState<ApiZip[]>([]);
  const [forecasts, setForecasts] = useState<ApiForecast[]>([]);
  const [forecastWeek, setForecastWeek] = useState<number | null>(null);
  const [forecastYear, setForecastYear] = useState(FORECAST_YEAR);
  const [reloadToken, setReloadToken] = useState(0);

  const predictions = useRef(new Map<string, ApiPrediction>());
  const trends = useRef(new Map<string, ApiTrends>());
  const inFlightPredict = useRef(new Map<string, Promise<ApiPrediction>>());
  const inFlightTrends = useRef(new Map<string, Promise<ApiTrends>>());

  const loadPrediction = useCallback(async (zip: string) => {
    const key = zip.trim().padStart(5, "0");
    const cached = predictions.current.get(key);
    if (cached) return cached;
    const pending = inFlightPredict.current.get(key);
    if (pending) return pending;

    const request = fetchPrediction(key)
      .then((result) => {
        predictions.current.set(key, result);
        setForecastWeek((current) => current ?? result.forecast_week);
        setForecastYear((current) => result.forecast_year ?? current);
        return result;
      })
      .finally(() => {
        inFlightPredict.current.delete(key);
      });

    inFlightPredict.current.set(key, request);
    return request;
  }, []);

  const loadTrends = useCallback(async (zip: string) => {
    const key = zip.trim().padStart(5, "0");
    const cached = trends.current.get(key);
    if (cached) return cached;
    const pending = inFlightTrends.current.get(key);
    if (pending) return pending;

    const request = fetchTrends(key)
      .then((result) => {
        trends.current.set(key, result);
        return result;
      })
      .finally(() => {
        inFlightTrends.current.delete(key);
      });

    inFlightTrends.current.set(key, request);
    return request;
  }, []);

  useEffect(() => {
    let cancelled = false;
    predictions.current.clear();
    trends.current.clear();
    inFlightPredict.current.clear();
    inFlightTrends.current.clear();

    async function load() {
      try {
        await fetchHealth();
        const [zipRows, forecastRows] = await Promise.all([fetchZips(), fetchForecasts()]);
        if (cancelled) return;
        setZips(zipRows);
        setForecasts(forecastRows);
        const sample = forecastRows[0];
        if (sample) {
          setForecastWeek(sample.forecast_week);
          setForecastYear(sample.forecast_year);
        }
        if (!cancelled) setStatus("ready");
      } catch (err) {
        if (cancelled) return;
        const message =
          err instanceof ApiError
            ? err.message
            : "Cannot reach the FastAPI backend. Start it on port 8000.";
        setError(message);
        setStatus("error");
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  const forecastsByZip = useMemo(() => {
    const map = new Map<string, ApiForecast>();
    for (const row of forecasts) map.set(row.zip_code, row);
    return map;
  }, [forecasts]);

  const zipByCode = useMemo(() => {
    const map = new Map<string, ApiZip>();
    for (const row of zips) map.set(row.zip_code, row);
    return map;
  }, [zips]);

  const value = useMemo<ForecastContextValue>(
    () => ({
      status,
      error,
      zips,
      forecastsByZip,
      forecastWeek,
      forecastYear,
      forecastRange:
        forecastWeek != null ? formatWeekRange(forecastYear, forecastWeek) : "Next 7 days",
      getZip: (zip) => zipByCode.get(zip.trim().padStart(5, "0")),
      getForecast: (zip) => forecastsByZip.get(zip.trim().padStart(5, "0")),
      loadPrediction,
      loadTrends,
      reload: () => setReloadToken((n) => n + 1),
    }),
    [
      status,
      error,
      zips,
      forecastsByZip,
      forecastWeek,
      forecastYear,
      zipByCode,
      loadPrediction,
      loadTrends,
    ],
  );

  return <ForecastContext.Provider value={value}>{children}</ForecastContext.Provider>;
}

export function useForecastData() {
  const ctx = useContext(ForecastContext);
  if (!ctx) throw new Error("useForecastData must be used within ForecastProvider");
  return ctx;
}
