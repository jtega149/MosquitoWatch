"""
model_service.py
-----------------
Owned by: Backend Person 1 (Data + ML Inference)

Loads the trained scikit-learn / XGBoost pipeline exactly once (module-level cache),
and turns per-ZIP feature rows into a 0-100 forecast score + risk level for next week.
"""

from __future__ import annotations

import json
import os

import joblib
import pandas as pd

import data_service

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "model.joblib")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "model_metadata.json")

# Score -> risk label. Upper bound is exclusive.
RISK_THRESHOLDS = [
    (25, "Low"),
    (50, "Moderate"),
    (75, "Elevated"),
    (101, "High"),
]

_model = None
_model_metadata: dict | None = None


class ModelServiceError(Exception):
    """Raised for any model-loading or inference problem."""


def _load_model():
    """Load model.joblib once and cache it at module scope."""
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise ModelServiceError(
                f"Model file not found: {MODEL_PATH}. Run train_models.py to export production artifacts."
            )
        try:
            _model = joblib.load(MODEL_PATH)
        except Exception as exc:
            raise ModelServiceError(f"Failed to load model.joblib: {exc}") from exc
    return _model


def _load_metadata() -> dict:
    global _model_metadata
    if _model_metadata is None:
        if not os.path.exists(METADATA_PATH):
            raise ModelServiceError(f"Metadata file not found: {METADATA_PATH}")
        with open(METADATA_PATH, "r") as f:
            _model_metadata = json.load(f)
    return _model_metadata


def reload_model() -> None:
    """Force the model and metadata to be reloaded from disk on next use."""
    global _model, _model_metadata
    _model = None
    _model_metadata = None


def get_risk_level(score: float) -> str:
    """Map a 0-100 forecast score to a risk label using the shared thresholds."""
    for threshold, label in RISK_THRESHOLDS:
        if score < threshold:
            return label
    return RISK_THRESHOLDS[-1][1]


def _positive_class_index(model, metadata: dict) -> int:
    """Find which column of predict_proba() corresponds to positive_next_week=1."""
    classes = list(model.classes_)
    positive_label = metadata.get("positive_class_label", 1)
    if positive_label in classes:
        return classes.index(positive_label)
    return int(len(classes) - 1)


def _feature_row_from_dict(features: dict, expected_columns: list[str]) -> pd.DataFrame:
    row = {}
    missing = []
    for col in expected_columns:
        # Check alias if needed
        value = features.get(col)
        if value is None and col == "zip_code" and "zipcode" in features:
            value = features["zipcode"]
        elif value is None and col == "zipcode" and "zip_code" in features:
            value = features["zip_code"]
        
        if value is None:
            missing.append(col)
        row[col] = value
    if missing:
        raise ModelServiceError(f"Feature row is missing required values: {missing}")
    return pd.DataFrame([row], columns=expected_columns)


def predict_zip(zip_code: str) -> dict:
    """Run inference for a single ZIP to forecast next week's elevated risk.

    Returns {"risk_score": float 0-100, "risk_level": str}.
    Raises data_service.ZipNotFoundError if the ZIP has no feature row,
    or ModelServiceError if the model/metadata can't be loaded or used.
    """
    model = _load_model()
    metadata = _load_metadata()
    expected_columns = metadata.get("feature_columns")
    if not expected_columns:
        raise ModelServiceError("model_metadata.json is missing 'feature_columns'")

    features = data_service.get_latest_features(zip_code)
    X = _feature_row_from_dict(features, expected_columns)

    proba = model.predict_proba(X)[0]
    pos_idx = _positive_class_index(model, metadata)
    score = round(float(proba[pos_idx]) * 100, 1)
    return {"risk_score": score, "risk_level": get_risk_level(score)}


def predict_all() -> list[dict]:
    """Run batch inference for every ZIP, for the /forecasts (map) endpoint.

    Uses a single predict_proba() call across all rows rather than looping per-ZIP.
    """
    model = _load_model()
    metadata = _load_metadata()
    expected_columns = metadata.get("feature_columns")
    if not expected_columns:
        raise ModelServiceError("model_metadata.json is missing 'feature_columns'")

    latest = data_service._load_latest_features()
    # Normalize zip columns if necessary
    if "zip_code" in expected_columns and "zip_code" not in latest.columns:
        latest["zip_code"] = latest["zipcode"]

    missing_cols = [c for c in expected_columns if c not in latest.columns]
    if missing_cols:
        raise ModelServiceError(f"latest_features.csv is missing columns the model needs: {missing_cols}")

    X = latest[expected_columns]
    proba = model.predict_proba(X)
    pos_idx = _positive_class_index(model, metadata)

    results = []
    for zip_code, p in zip(latest["zip_code"], proba[:, pos_idx]):
        score = round(float(p) * 100, 1)
        results.append({"zip_code": str(zip_code).zfill(5), "risk_score": score, "risk_level": get_risk_level(score)})
    return results
