"""
data_service.py
----------------
Owned by: Backend Person 1 (Data + ML Inference)

Loads and serves the artifacts produced by the ML pipeline:
    - latest_features.csv   -> one row per ZIP, current week's features to forecast upcoming week
    - zip_metadata.csv      -> borough / neighborhood info per ZIP
    - history.csv           -> historical positive-detection counts per ZIP

Design notes:
    - ZIP codes are ALWAYS treated as strings, zero-padded to 5 digits.
    - Files are read from disk once and cached in memory (lru_cache).
    - Call reload_data() to force a refresh in tests or when artifacts update.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from functools import lru_cache

import pandas as pd

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

LATEST_FEATURES_PATH = os.path.join(ARTIFACTS_DIR, "latest_features.csv")
ZIP_METADATA_PATH = os.path.join(ARTIFACTS_DIR, "zip_metadata.csv")
HISTORY_PATH = os.path.join(ARTIFACTS_DIR, "history.csv")

# Core features expected in latest_features.csv
REQUIRED_FEATURE_COLUMNS = [
    "zip_code",
    "borough",
    "week_of_year",
    "temp_mean",
    "humidity_mean",
    "precip_sum",
    "precip_7d",
    "precip_14d",
    "degree_days_14d",
    "positives_last_1w",
    "positives_last_2_4w",
]
REQUIRED_METADATA_COLUMNS = ["zip_code", "borough", "areas"]
REQUIRED_HISTORY_COLUMNS = ["zip_code", "year", "week", "positive_detections"]


class DataServiceError(Exception):
    """Raised for any data-loading or lookup problem in data_service."""


class ZipNotFoundError(DataServiceError):
    """Raised when a requested ZIP code has no data in a given table."""


def _normalize_zip(zip_code: str) -> str:
    return str(zip_code).strip().zfill(5)


def _read_csv_as_str_zip(path: str, required_columns: list[str]) -> pd.DataFrame:
    if not os.path.exists(path):
        raise DataServiceError(
            f"Required data file not found: {path}. "
            "Confirm the ML teammate has exported this artifact."
        )
    df = pd.read_csv(path, dtype={"zip_code": str, "zipcode": str})
    if "zip_code" not in df.columns and "zipcode" in df.columns:
        df["zip_code"] = df["zipcode"]
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5)

    # Allow alias for areas / neighborhoods
    if "areas" not in df.columns and "neighborhoods" in df.columns:
        df["areas"] = df["neighborhoods"].fillna("New York Metropolitan Area")

    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise DataServiceError(
            f"{os.path.basename(path)} is missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )
    return df


@lru_cache(maxsize=1)
def _load_latest_features() -> pd.DataFrame:
    df = _read_csv_as_str_zip(LATEST_FEATURES_PATH, REQUIRED_FEATURE_COLUMNS)
    if df["zip_code"].duplicated().any():
        dupes = sorted(df[df["zip_code"].duplicated(keep=False)]["zip_code"].unique().tolist())
        raise DataServiceError(
            "latest_features.csv must contain exactly one row per ZIP "
            f"(the latest week only). Duplicate ZIPs found: {dupes}"
        )
    return df


@lru_cache(maxsize=1)
def _load_zip_metadata() -> pd.DataFrame:
    df = _read_csv_as_str_zip(ZIP_METADATA_PATH, REQUIRED_METADATA_COLUMNS)
    return df.drop_duplicates(subset="zip_code").reset_index(drop=True)


@lru_cache(maxsize=1)
def _load_history() -> pd.DataFrame:
    df = _read_csv_as_str_zip(HISTORY_PATH, REQUIRED_HISTORY_COLUMNS)
    return df.sort_values(["zip_code", "year", "week"]).reset_index(drop=True)


def reload_data() -> None:
    """Clear cached in-memory tables and force a re-read from disk on next access."""
    _load_latest_features.cache_clear()
    _load_zip_metadata.cache_clear()
    _load_history.cache_clear()


def get_latest_features(zip_code: str) -> dict:
    """Return the most recent feature row for a ZIP as a dict.

    Raises ZipNotFoundError if the ZIP has no row in latest_features.csv.
    """
    zip_code = _normalize_zip(zip_code)
    df = _load_latest_features()
    row = df[df["zip_code"] == zip_code]
    if row.empty:
        raise ZipNotFoundError(f"No feature data found for ZIP {zip_code}")
    return row.iloc[0].to_dict()


def get_zip_metadata(zip_code: str) -> dict:
    """Return {zip_code, borough, areas} for a ZIP.

    Raises ZipNotFoundError if the ZIP is unsupported.
    """
    zip_code = _normalize_zip(zip_code)
    df = _load_zip_metadata()
    row = df[df["zip_code"] == zip_code]
    if row.empty:
        raise ZipNotFoundError(f"No metadata found for ZIP {zip_code}")
    return row.iloc[0].to_dict()


def get_all_zips() -> list[dict]:
    """Return every supported ZIP with borough + areas, for the /zips endpoint."""
    df = _load_zip_metadata()
    return df[REQUIRED_METADATA_COLUMNS].to_dict("records")


def get_history(zip_code: str) -> list[dict]:
    """Return chronological [{year, week, positive_detections}, ...] for a ZIP.

    Raises ZipNotFoundError if the ZIP has no history rows.
    """
    zip_code = _normalize_zip(zip_code)
    df = _load_history()
    rows = df[df["zip_code"] == zip_code].sort_values(["year", "week"])
    if rows.empty:
        raise ZipNotFoundError(f"No history found for ZIP {zip_code}")
    return rows[["year", "week", "positive_detections"]].to_dict("records")


def get_forecast_period() -> dict:
    """Return the feature week and the next ISO week the model is forecasting."""

    features = _load_latest_features()
    if features.empty:
        raise DataServiceError("latest_features.csv contains no ZIP rows")
    feature_week = int(features.iloc[0]["week_of_year"])
    history = _load_history()
    feature_year = int(history["year"].max()) if not history.empty else date.today().year
    feature_monday = date.fromisocalendar(feature_year, feature_week, 1)
    forecast_monday = feature_monday + timedelta(days=7)
    iso = forecast_monday.isocalendar()
    return {
        "feature_week": feature_week,
        "feature_year": feature_year,
        "forecast_week": int(iso.week),
        "forecast_year": int(iso.year),
    }


def seasonality_label(week: int) -> str:
    """Plain-language mosquito-season label from an ISO week number."""

    if 22 <= week <= 36:
        return "Peak mosquito season (Jun–Sep)"
    if 18 <= week <= 43:
        return "Mosquito season (May–Oct)"
    return "Off-season"


def next_7_days(year: int, week: int, risk_score: float, risk_level: str) -> list[dict]:
    """Expand the weekly forecast across the seven ISO-week dates."""

    monday = date.fromisocalendar(year, week, 1)
    return [
        {
            "date": (monday + timedelta(days=offset)).isoformat(),
            "risk_score": risk_score,
            "risk_level": risk_level,
        }
        for offset in range(7)
    ]
