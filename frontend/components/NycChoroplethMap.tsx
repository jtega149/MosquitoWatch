"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, ZoomControl, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { Layer, PathOptions } from "leaflet";
import { getZipData, riskColor } from "@/lib/mock-data";
import { useForecastWeek } from "@/lib/forecast-context";
import { RiskBadge } from "./RiskBadge";
import type { ZipForecast } from "@/lib/types";

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
  const { week } = useForecastWeek();
  const [geo, setGeo] = useState<FeatureCollection<Geometry, ZipProps> | null>(null);
  const [selectedZip, setSelectedZip] = useState(DEFAULT_SELECTED);

  useEffect(() => {
    fetch("/nyc-modzcta.geo.json")
      .then((r) => r.json())
      .then(setGeo)
      .catch(() => setGeo(null));
  }, []);

  const selected: ZipForecast | undefined = useMemo(
    () => getZipData(selectedZip, week),
    [selectedZip, week],
  );

  const styleFor = (feature?: Feature<Geometry, ZipProps>): PathOptions => {
    const zip = feature ? zipFromFeature(feature) : "";
    const data = zip ? getZipData(zip, week) : undefined;
    const isSelected = zip === selectedZip;
    return {
      fillColor: data ? riskColor(data.riskScore) : "#1e293b",
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

  return (
    <div className="relative h-full min-h-[560px] overflow-hidden rounded-2xl border border-white/10">
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
            key={`${week}-${selectedZip}`}
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

      {selected && (
        <div className="absolute bottom-4 right-4 z-[1000] w-80 rounded-xl border border-white/10 bg-[#131a2b]/95 p-4 shadow-2xl backdrop-blur">
          <div className="text-sm font-semibold text-white">ZIP {selected.zip}</div>
          <div className="mt-0.5 text-xs text-slate-400">
            {selected.neighborhood}
          </div>
          <div className="mt-3 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-500">Risk</div>
              <div className="text-2xl font-semibold" style={{ color: riskColor(selected.riskLevel) }}>
                {selected.riskScore}%
              </div>
            </div>
            <RiskBadge level={selected.riskLevel} size="md" />
          </div>
          <Link
            href={`/zip-lookup?zip=${selected.zip}`}
            className="mt-3 inline-flex text-sm font-medium text-[#4ade80] hover:underline"
          >
            View Details →
          </Link>
        </div>
      )}
    </div>
  );
}
