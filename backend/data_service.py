"""
data_service.py
----------------
Owned by: Backend Person 1 (Data + ML Inference)

Loads and serves the artifacts produced by the ML teammate:
    - latest_features.csv   -> one row per ZIP, most recent week's features
    - zip_metadata.csv      -> borough / neighborhood info per ZIP
    - history.csv           -> historical positive-detection counts per ZIP

Design notes (per the project contract):
    - ZIP codes are ALWAYS treated as strings, zero-padded to 5 digits.
      Never let pandas coerce them to int/float ("10310" -> "10310.0" bugs).
    - Files are read from disk once and cached in memory (lru_cache).
      Call reload_data() to force a refresh (e.g. in tests, or if the ML
      teammate ships updated CSVs mid-hackathon).
    - This module raises clear, typed exceptions instead of returning
      None/empty so that app.py (Person 2) can map them to clean HTTP
      status codes (404 for unknown ZIP, 500 for a broken data file).
"""

from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

LATEST_FEATURES_PATH = os.path.join(ARTIFACTS_DIR, "latest_features.csv")
ZIP_METADATA_PATH = os.path.join(ARTIFACTS_DIR, "zip_metadata.csv")
HISTORY_PATH = os.path.join(ARTIFACTS_DIR, "history.csv")

REQUIRED_FEATURE_COLUMNS = [
    "zip_code",
    "borough",
    "week_of_year",
    "avg_temp_prev_7d",
    "rainfall_prev_7d",
    "positives_prev_week",
    "positives_prev_2_weeks",
    "positives_prev_4_weeks",
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
            "Confirm the ML teammate has exported this artifact, or run "
            "generate_sample_artifacts.py to create placeholder data."
        )
    df = pd.read_csv(path, dtype={"zip_code": str})
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5)

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
