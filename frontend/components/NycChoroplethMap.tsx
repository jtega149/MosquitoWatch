"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, ZoomControl, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { Layer, PathOptions } from "leaflet";
import { ApiError, type ApiPrediction } from "@/lib/api";
import { useForecastData } from "@/lib/forecast-context";
import { parseRiskLevel, riskColor } from "@/lib/risk";
import { RiskBadge } from "./RiskBadge";
import { SevenDayForecast } from "./SevenDayForecast";

type ZipProps = { MODZCTA: string; label?: string };

const NYC_CENTER: [number, number] = [40.71, -73.98];
const DEFAULT_SELECTED = "10310";

const LEGEND = [
  { label: "High (75–100%)", color: "#ef4444" },
  { label: "Elevated (50–74%)", color: "#f97316" },
  { label: "Moderate (25–49%)", color: "#eab308" },
  { label: "Low (0–24%)", color: "#22c55e" },
];

function zipFromFeature(feature: Feature<Geometry, ZipProps>) {
  return feature.properties?.MODZCTA ?? "";
}

function FitNyc() {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(
      [
        [40.49, -74.27],
        [40.92, -73.68],
      ],
      { padding: [12, 12] },
    );
  }, [map]);
  return null;
}

export function NycChoroplethMap() {
  const {
    status,
    error,
    forecastsByZip,
    getZip,
    getForecast,
    loadPrediction,
    forecastWeek,
    reload,
  } = useForecastData();
  const [geo, setGeo] = useState<FeatureCollection<Geometry, ZipProps> | null>(null);
  const [selectedZip, setSelectedZip] = useState(DEFAULT_SELECTED);
  const [detail, setDetail] = useState<ApiPrediction | null>(null);
  const [failedZip, setFailedZip] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/nyc-modzcta.geo.json")
      .then((r) => r.json())
      .then(setGeo)
      .catch(() => setGeo(null));
  }, []);

  useEffect(() => {
    let cancelled = false;

    void loadPrediction(selectedZip)
      .then((prediction) => {
        if (cancelled) return;
        setDetail(prediction);
        setFailedZip(null);
        setDetailError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setFailedZip(selectedZip);
        if (err instanceof ApiError && err.status === 404) {
          setDetailError("No forecast for this ZIP in the model.");
        } else {
          setDetailError(err instanceof Error ? err.message : "Could not load forecast.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedZip, loadPrediction]);

  const styleFor = (feature?: Feature<Geometry, ZipProps>): PathOptions => {
    const zip = feature ? zipFromFeature(feature) : "";
    const data = zip ? getForecast(zip) : undefined;
    const isSelected = zip === selectedZip;
    return {
      fillColor: data ? riskColor(data.risk_score) : "#1e293b",
      fillOpacity: data ? 0.78 : 0.25,
      color: isSelected ? "#ffffff" : "#0a0e1a",
      weight: isSelected ? 2.4 : 0.6,
    };
  };

  const onEachFeature = (feature: Feature<Geometry, ZipProps>, layer: Layer) => {
    layer.on({
      click: () => setSelectedZip(zipFromFeature(feature)),
      mouseover: (e) => {
        e.target.setStyle({ weight: 2, color: "#ffffff", fillOpacity: 0.9 });
        e.target.bringToFront();
      },
      mouseout: (e) => {
        e.target.setStyle(styleFor(feature));
      },
    });
  };

  const meta = getZip(selectedZip);
  const mapForecast = getForecast(selectedZip);
  const activeDetail = detail?.zip_code === selectedZip ? detail : null;
  const waiting = !activeDetail && failedZip !== selectedZip;
  const level = activeDetail
    ? parseRiskLevel(activeDetail.risk_level, activeDetail.risk_score)
    : mapForecast
      ? parseRiskLevel(mapForecast.risk_level, mapForecast.risk_score)
      : null;

  return (
    <div className="relative h-full min-h-[560px] overflow-hidden rounded-2xl border border-white/10">
      {status === "error" && (
        <div className="absolute inset-x-4 top-4 z-[1100] rounded-xl border border-red-500/30 bg-[#131a2b]/95 p-3 text-sm text-red-300">
          {error}{" "}
          <button type="button" className="underline" onClick={reload}>
            Retry
          </button>
        </div>
      )}
      {geo ? (
        <MapContainer
          center={NYC_CENTER}
          zoom={11}
          zoomControl={false}
          className="h-full w-full"
          style={{ background: "#0a0e1a" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ZoomControl position="topleft" />
          <FitNyc />
          <GeoJSON
            key={`${forecastsByZip.size}-${selectedZip}-${status}`}
            data={geo}
            style={styleFor}
            onEachFeature={onEachFeature}
          />
        </MapContainer>
      ) : (
        <div className="flex h-full items-center justify-center text-sm text-slate-400">
          Loading NYC ZIP map…
        </div>
      )}

      <div className="pointer-events-none absolute left-4 top-20 z-[1000] w-52 rounded-xl border border-white/10 bg-[#131a2b]/95 p-4 shadow-xl backdrop-blur">
        <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Risk Level
        </div>
        <ul className="space-y-2">
          {LEGEND.map((item) => (
            <li key={item.label} className="flex items-center gap-2 text-xs text-slate-200">
              <span className="h-3 w-3 rounded-sm" style={{ background: item.color }} />
              {item.label}
            </li>
          ))}
        </ul>
      </div>

      <div className="absolute bottom-4 right-4 z-[1000] max-h-[70%] w-80 overflow-y-auto rounded-xl border border-white/10 bg-[#131a2b]/95 p-4 shadow-2xl backdrop-blur">
        <div className="text-sm font-semibold text-white">ZIP {selectedZip}</div>
        <div className="mt-0.5 text-xs text-slate-400">
          {activeDetail?.areas ?? meta?.areas ?? "New York City"}
        </div>
        <div className="text-[11px] text-slate-500">{activeDetail?.borough ?? meta?.borough}</div>

        {waiting && (
          <p className="mt-3 text-xs text-slate-400">Loading 7-day West Nile forecast…</p>
        )}
        {failedZip === selectedZip && detailError && (
          <p className="mt-3 text-xs text-red-400">{detailError}</p>
        )}

        {(activeDetail || mapForecast) && level && (
          <>
            <div className="mt-3 flex items-center justify-between">
              <div>
                <div className="text-xs text-slate-500">Next 7 days</div>
                <div className="text-2xl font-semibold" style={{ color: riskColor(level) }}>
                  {(activeDetail?.risk_score ?? mapForecast?.risk_score)}%
                </div>
              </div>
              <RiskBadge level={level} size="md" />
            </div>
            {activeDetail && (
              <div className="mt-3">
                <SevenDayForecast days={activeDetail.next_7_days} />
              </div>
            )}
            {activeDetail?.explanation && (
              <p className="mt-3 text-[11px] leading-relaxed text-slate-400">{activeDetail.explanation}</p>
            )}
          </>
        )}

        {!waiting && !activeDetail && !mapForecast && failedZip !== selectedZip && (
          <p className="mt-3 text-xs text-slate-400">Select a ZIP to see the next-7-day forecast.</p>
        )}

        <Link
          href={`/zip-lookup?zip=${selectedZip}`}
          className="mt-3 inline-flex text-sm font-medium text-[#4ade80] hover:underline"
        >
          View Details →
        </Link>
        {forecastWeek != null && (
          <p className="mt-2 text-[10px] text-slate-600">Surveillance forecast week {forecastWeek}</p>
        )}
      </div>
    </div>
  );
}
