"""
generate_sample_artifacts.py
------------------------------
NOT part of the production backend - a dev-only helper.

Generates small, structurally-correct-but-fake artifacts so
data_service.py and model_service.py can be built, run, and tested
*before* the ML teammate delivers the real:
    model.joblib, model_metadata.json, latest_features.csv,
    zip_metadata.csv, history.csv

Run once:
    python generate_sample_artifacts.py

The moment the real ML artifacts arrive, just drop them into
backend/artifacts/ with the same filenames - nothing else needs to change,
since data_service.py and model_service.py only care about filenames and
column names, not where the data came from.
"""

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

ZIPS = [
    ("10310", "Staten Island", "Port Richmond / West Brighton"),
    ("10302", "Staten Island", "Mariners Harbor / Port Richmond"),
    ("11385", "Queens", "Ridgewood"),
    ("11201", "Brooklyn", "Brooklyn Heights"),
    ("10457", "Bronx", "Tremont"),
]

FEATURE_COLUMNS = [
    "week_of_year",
    "avg_temp_prev_7d",
    "rainfall_prev_7d",
    "positives_prev_week",
    "positives_prev_2_weeks",
    "positives_prev_4_weeks",
    "zip_code",
    "borough",
]

rng = np.random.default_rng(42)

# ---- zip_metadata.csv -------------------------------------------------
zip_metadata = pd.DataFrame(ZIPS, columns=["zip_code", "borough", "areas"])
zip_metadata.to_csv(os.path.join(ARTIFACTS_DIR, "zip_metadata.csv"), index=False)

# ---- history.csv (weeks 20-32, 2026, per ZIP) --------------------------
history_rows = []
for zip_code, borough, _ in ZIPS:
    positives = 0
    for week in range(20, 33):
        positives = max(0, positives + int(rng.integers(-1, 3)))
        history_rows.append(
            {"zip_code": zip_code, "year": 2026, "week": week, "positive_detections": positives}
        )
history = pd.DataFrame(history_rows)
history.to_csv(os.path.join(ARTIFACTS_DIR, "history.csv"), index=False)

# ---- latest_features.csv (one row per ZIP = week 32) -------------------
latest_rows = []
for zip_code, borough, _ in ZIPS:
    zip_hist = history[history["zip_code"] == zip_code].sort_values("week")
    prev_week = int(zip_hist.iloc[-1]["positive_detections"])
    prev_2 = int(zip_hist.tail(2)["positive_detections"].sum())
    prev_4 = int(zip_hist.tail(4)["positive_detections"].sum())
    latest_rows.append(
        {
            "zip_code": zip_code,
            "borough": borough,
            "week_of_year": 32,
            "avg_temp_prev_7d": round(float(rng.uniform(75, 88)), 1),
            "rainfall_prev_7d": round(float(rng.uniform(0, 2.5)), 2),
            "positives_prev_week": prev_week,
            "positives_prev_2_weeks": prev_2,
            "positives_prev_4_weeks": prev_4,
        }
    )
latest_features = pd.DataFrame(latest_rows)
latest_features.to_csv(os.path.join(ARTIFACTS_DIR, "latest_features.csv"), index=False)

# ---- train a tiny placeholder model on synthetic training data ---------
n = 400
train = pd.DataFrame(
    {
        "zip_code": rng.choice([z[0] for z in ZIPS], n),
        "week_of_year": rng.integers(20, 40, n),
        "avg_temp_prev_7d": rng.uniform(65, 95, n),
        "rainfall_prev_7d": rng.uniform(0, 3, n),
        "positives_prev_week": rng.integers(0, 6, n),
        "positives_prev_2_weeks": rng.integers(0, 10, n),
        "positives_prev_4_weeks": rng.integers(0, 16, n),
    }
)
train = train.merge(zip_metadata[["zip_code", "borough"]], on="zip_code", how="left")

# Fake target: more likely positive_next_week=1 with more recent activity + heat.
logit = (
    -3.0
    + 0.35 * train["positives_prev_week"]
    + 0.12 * train["positives_prev_2_weeks"]
    + 0.05 * (train["avg_temp_prev_7d"] - 75)
)
prob = 1 / (1 + np.exp(-logit))
train["positive_next_week"] = (rng.uniform(0, 1, n) < prob).astype(int)

X = train[FEATURE_COLUMNS]
y = train["positive_next_week"]

categorical = ["zip_code", "borough"]
numeric = [c for c in FEATURE_COLUMNS if c not in categorical]

preprocessor = ColumnTransformer(
    [
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", "passthrough", numeric),
    ]
)

pipeline = Pipeline(
    [
        ("preprocessing", preprocessor),
        ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000)),
    ]
)
pipeline.fit(X, y)

joblib.dump(pipeline, os.path.join(ARTIFACTS_DIR, "model.joblib"))

metadata = {
    "model_type": "LogisticRegression",
    "feature_columns": FEATURE_COLUMNS,
    "positive_class_label": 1,
    "target": "positive_next_week",
    "trained_on": "synthetic placeholder data - replace with the real model.joblib from the ML teammate",
    "risk_thresholds": {"Low": "<25", "Moderate": "25-49", "Elevated": "50-74", "High": ">=75"},
}
with open(os.path.join(ARTIFACTS_DIR, "model_metadata.json"), "w") as f:
    json.dump(metadata, f, indent=2)

print("Sample artifacts written to:", ARTIFACTS_DIR)
print("Files:", sorted(os.listdir(ARTIFACTS_DIR)))
