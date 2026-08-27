#!/usr/bin/env python3
"""Build 2026 WNV ZIP-week training data from NYC DOH Datawrapper + Open-Meteo."""

from __future__ import annotations

import csv
import io
import json
import math
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

YEAR = 2026
SEASON_START = date(YEAR, 6, 1)
SEASON_END = date(YEAR, 8, 21)  # table last updated
LAG_PAD_DAYS = 14
DEGREE_DAY_BASE_C = 15.0

DATAWRAPPER_CSV = "https://datawrapper.dwcdn.net/Ys9mm/13/dataset.csv"
GAZETTEER_ZIP = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2025_Gazetteer/2025_Gaz_zcta_national.zip"
)
OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive"

BOROUGH_CENTROIDS = {
    "Manhattan": (40.7831, -73.9712),
    "Brooklyn": (40.6782, -73.9442),
    "Queens": (40.7282, -73.7949),
    "Bronx": (40.8448, -73.8648),
    "Staten Island": (40.5795, -74.1502),
}
SPECIAL_ZIPS = {
    "00083": (40.7829, -73.9654),  # Central Park (not a Census ZCTA)
}

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw"
PROCESSED_DIR = ROOT / "processed"


def fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "MosquitoWatch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def monday_on_or_before(d: date) -> date:
    return d - timedelta(days=d.weekday())


def meteorological_season(d: date) -> str:
    m = d.month
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    return "fall"


def parse_trap_dates(raw: str, year: int = YEAR) -> list[date]:
    if not raw or not str(raw).strip():
        return []
    out = []
    for token in str(raw).split(","):
        token = token.strip()
        if not token:
            continue
        parsed = datetime.strptime(f"{token}/{year}", "%m/%d/%Y").date()
        out.append(parsed)
    return out


def load_zip_centroids(needed: set[str]) -> dict[str, tuple[float, float]]:
    blob = fetch(GAZETTEER_ZIP)
    coords: dict[str, tuple[float, float]] = dict(SPECIAL_ZIPS)
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        name = zf.namelist()[0]
        with zf.open(name) as fh:
            text = io.TextIOWrapper(fh, encoding="utf-8")
            next(text)  # GEOID|...|INTPTLAT|INTPTLONG
            for line in text:
                parts = line.strip().split("|")
                zcta = parts[0].zfill(5)
                if zcta in needed:
                    coords[zcta] = (float(parts[-2]), float(parts[-1]))
    missing = needed - set(coords)
    return coords, missing


def weather_grid_key(lat: float, lon: float) -> tuple[float, float]:
    return (round(lat, 2), round(lon, 2))


def fetch_daily_weather(lat: float, lon: float, start: date, end: date) -> dict[str, dict]:
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_mean",
                "temperature_2m_min",
                "precipitation_sum",
                "relative_humidity_2m_mean",
            ]
        ),
        "timezone": "America/New_York",
    }
    url = OPEN_METEO + "?" + urllib.parse.urlencode(params)
    payload = json.loads(fetch(url).decode("utf-8"))
    daily = payload["daily"]
    out = {}
    for i, day in enumerate(daily["time"]):
        tmean = daily["temperature_2m_mean"][i]
        tmax = daily["temperature_2m_max"][i]
        tmin = daily["temperature_2m_min"][i]
        precip = daily["precipitation_sum"][i]
        rh = daily["relative_humidity_2m_mean"][i]
        dd = 0.0
        if tmean is not None:
            dd = max(0.0, float(tmean) - DEGREE_DAY_BASE_C)
        out[day] = {
            "temp_max": tmax,
            "temp_mean": tmean,
            "temp_min": tmin,
            "precip": precip,
            "humidity": rh,
            "degree_days": dd,
        }
    return out


def mean(xs: list[float]) -> float | None:
    vals = [x for x in xs if x is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 3)


def total(xs: list[float]) -> float | None:
    vals = [x for x in xs if x is not None]
    if not vals:
        return None
    return round(sum(vals), 3)


def window_stats(weather: dict[str, dict], start: date, end: date) -> dict[str, float | None]:
    days = []
    d = start
    while d <= end:
        days.append(weather.get(d.isoformat()))
        d += timedelta(days=1)
    days = [row for row in days if row]
    return {
        "temp_mean": mean([r["temp_mean"] for r in days]),
        "temp_max": mean([r["temp_max"] for r in days]),
        "temp_min": mean([r["temp_min"] for r in days]),
        "humidity_mean": mean([r["humidity"] for r in days]),
        "precip_sum": total([r["precip"] for r in days]),
        "degree_days": total([r["degree_days"] for r in days]),
    }


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_bytes = fetch(DATAWRAPPER_CSV)
    raw_path = RAW_DIR / "wnv_positive_mosquitoes_2026.csv"
    raw_path.write_bytes(raw_bytes)

    reader = csv.DictReader(io.StringIO(raw_bytes.decode("utf-8")))
    zips = []
    for row in reader:
        zipcode = (row["ZIP Code"] or "").strip().zfill(5)
        zips.append(
            {
                "zipcode": zipcode,
                "borough": row["Borough"].strip(),
                "detection_type": row["Detection Type"].strip(),
                "positive_trap_dates": (row.get("All Positive Trap Date(s)") or "").strip(),
                "neighborhoods": (row.get("Neighborhood(s)") or "").strip(),
                "trap_dates": parse_trap_dates(row.get("All Positive Trap Date(s)") or ""),
            }
        )

    needed = {z["zipcode"] for z in zips}
    coords, missing = load_zip_centroids(needed)
    for z in zips:
        if z["zipcode"] not in coords:
            coords[z["zipcode"]] = BOROUGH_CENTROIDS[z["borough"]]

    weather_start = SEASON_START - timedelta(days=LAG_PAD_DAYS + 7)
    week_starts = []
    w = monday_on_or_before(SEASON_START)
    last_week = monday_on_or_before(SEASON_END)
    while w <= last_week:
        week_starts.append(w)
        w += timedelta(days=7)

    grids: dict[tuple[float, float], dict[str, dict]] = {}
    unique_keys = {weather_grid_key(*coords[z["zipcode"]]) for z in zips}
    for i, (lat, lon) in enumerate(sorted(unique_keys)):
        grids[(lat, lon)] = fetch_daily_weather(lat, lon, weather_start, SEASON_END)
        if i + 1 < len(unique_keys):
            time.sleep(0.15)

    positives_by_zip_week: dict[tuple[str, date], int] = defaultdict(int)
    for z in zips:
        for d in z["trap_dates"]:
            positives_by_zip_week[(z["zipcode"], monday_on_or_before(d))] += 1

    rows = []
    for z in zips:
        lat, lon = coords[z["zipcode"]]
        weather = grids[weather_grid_key(lat, lon)]
        history = []
        for week_start in week_starts:
            week_end = week_start + timedelta(days=6)
            count = positives_by_zip_week.get((z["zipcode"], week_start), 0)
            last_1w = history[-1] if history else 0
            last_2to4w = sum(history[-4:-1]) if len(history) > 1 else 0
            same = window_stats(weather, week_start, week_end)
            lag7 = window_stats(
                weather, week_start - timedelta(days=7), week_start - timedelta(days=1)
            )
            lag14 = window_stats(
                weather, week_start - timedelta(days=14), week_start - timedelta(days=8)
            )
            dd_14 = window_stats(
                weather, week_start - timedelta(days=13), week_end
            )["degree_days"]
            precip_14 = window_stats(
                weather, week_start - timedelta(days=7), week_end
            )["precip_sum"]
            week_of_year = int(week_start.strftime("%U"))
            angle = 2 * math.pi * week_of_year / 52
            rows.append(
                {
                    "zipcode": z["zipcode"],
                    "borough": z["borough"],
                    "neighborhoods": z["neighborhoods"],
                    "year": YEAR,
                    "week_start": week_start.isoformat(),
                    "week_of_year": week_of_year,
                    "week_sin": round(math.sin(angle), 4),
                    "week_cos": round(math.cos(angle), 4),
                    "season": meteorological_season(week_start),
                    "latitude": round(lat, 5),
                    "longitude": round(lon, 5),
                    "temp_mean": same["temp_mean"],
                    "temp_max": same["temp_max"],
                    "temp_min": same["temp_min"],
                    "humidity_mean": same["humidity_mean"],
                    "precip_sum": same["precip_sum"],
                    "temp_mean_lag7": lag7["temp_mean"],
                    "temp_mean_lag14": lag14["temp_mean"],
                    "humidity_mean_lag7": lag7["humidity_mean"],
                    "precip_7d": lag7["precip_sum"],
                    "precip_14d": precip_14,
                    "degree_days_14d": dd_14,
                    "positives_last_1w": last_1w,
                    "positives_last_2_4w": last_2to4w,
                    "zip_detection_status": z["detection_type"],
                    "positive_count": count,
                    "elevated": int(count > 0),
                }
            )
            history.append(count)

    long_path = RAW_DIR / "wnv_positive_trap_dates_long_2026.csv"
    with long_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "zipcode",
                "borough",
                "neighborhoods",
                "detection_type",
                "trap_date",
            ],
        )
        writer.writeheader()
        for z in zips:
            if not z["trap_dates"]:
                continue
            for d in z["trap_dates"]:
                writer.writerow(
                    {
                        "zipcode": z["zipcode"],
                        "borough": z["borough"],
                        "neighborhoods": z["neighborhoods"],
                        "detection_type": z["detection_type"],
                        "trap_date": d.isoformat(),
                    }
                )

    out_path = PROCESSED_DIR / "training_data.csv"
    fieldnames = list(rows[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    n_pos_zips = sum(1 for z in zips if z["trap_dates"])
    n_pos_dates = sum(len(z["trap_dates"]) for z in zips)
    n_elevated = sum(r["elevated"] for r in rows)
    print(f"Wrote {raw_path} ({len(zips)} ZIPs)")
    print(f"Wrote {long_path} ({n_pos_dates} positive trap dates from {n_pos_zips} ZIPs)")
    print(f"Wrote {out_path} ({len(rows)} ZIP-weeks, {n_elevated} elevated)")
    print(f"Weather grids: {len(grids)}; gazetteer missing ZIPs used borough centroid: {sorted(missing)}")


if __name__ == "__main__":
    main()
