# MosquitoWatch NYC — West Nile Hotspot Predictor

## Problem
On August 19, 2026, NYC reported its first human West Nile case of the year, with West Nile-positive mosquito pools already detected in all five boroughs and running at nearly twice the prior year's level. NYC Health publishes historical surveillance data (positive mosquito pool counts by borough/date), but there's no forward-looking, explainable view of *where* and *when* mosquito activity is likely to spike next.

**MosquitoWatch NYC** is a public-health surveillance dashboard that predicts elevated West Nile-positive mosquito activity by borough and week, using historical mosquito surveillance data combined with weather and seasonality signals — and uses Gemini to explain *why* the model flags an area as high or low risk.

**Important scope boundary:** We predict elevated *mosquito/surveillance* activity in an area/time period — **not** individual human infection risk.

## Core User Flow
1. User selects a **borough** and a **week**
2. Model analyzes surveillance history + weather + seasonality for that borough/week
3. Model outputs a **risk score** (0–100%) and status label (`ELEVATED` / `MODERATE` / `LOW`)
4. Dashboard shows a **trend chart** (monthly/weekly positive mosquito activity) and a **borough comparison** view
5. **Gemini** generates a plain-language explanation of the prediction, grounded in the model's actual feature values (not free-form guessing)

## MVP Feature Scope

### In scope (MVP)
- **Data pipeline**: ingest NYC Health West Nile surveillance data (positive pool counts by borough/date) + a weather dataset (temperature, rainfall) for NYC by date
- **Feature engineering**: weekly aggregation per borough — positive pool counts (current + trailing weeks), temperature, rainfall, seasonal week-of-year indicator
- **Classification model**: binary/multi-class classifier (e.g., logistic regression or gradient boosted trees) predicting "elevated activity" for a given borough/week, trained on historical NYC seasons
- **Model evaluation**: train/test split by season/year (not random shuffle, to avoid leakage across time), report precision/recall/F1, and a simple calibration check on the risk score
- **API layer**: endpoint(s) to (a) get prediction + feature breakdown for a borough/week, (b) get borough comparison for a given week, (c) get trend data for a borough
- **Gemini integration**: given the model's prediction + the specific feature values that drove it (e.g., "positive pools ↑, temp ↑, rainfall ↑, seasonal=HIGH"), Gemini generates a 1–2 sentence natural-language explanation. Gemini explains the model's output — it does not make its own risk judgment.
- **Dashboard frontend**: borough + week selector, risk score gauge, status label, recent indicators (pools/temp/rainfall trend arrows + seasonal level), borough comparison bar list, monthly trend chart, Gemini explanation text block

### Out of scope (MVP) — stretch goals if time allows
- Individual-level infection risk prediction (explicitly excluded — surveillance-only)
- Real-time/live data ingestion (MVP can use a static historical dataset snapshot)
- Sub-borough/neighborhood-level granularity (MVP is borough-level only)
- User accounts, saved searches, alerting/notifications
- Map-based geospatial visualization (nice-to-have if time permits)
- Model retraining pipeline/automation

## Data Sources
- **NYC Health West Nile virus surveillance reports** — positive mosquito pool counts by borough and date, 2026 (and prior years if available for historical training data)
- **Weather data** — daily temperature and rainfall for NYC (e.g., NOAA or a public weather API), joined to surveillance data by date

## Tech Stack (suggested)
- **Data/model**: Python (pandas, scikit-learn) for cleaning, feature engineering, training, evaluation
- **API**: FastAPI (Python) or Express (Node.js) serving model predictions and Gemini explanations
- **LLM**: Google Gemini API for explanation generation
- **Frontend**: React dashboard with chart library (e.g., Recharts) for trend/comparison visuals
- **Storage**: flat files/CSV or lightweight DB (SQLite/Postgres) for processed weekly features — no need for heavy infra at MVP scale

## Success Criteria for Demo
- Selecting a borough + week returns a risk score, status, and 4 indicator arrows/levels within a couple seconds
- Model evaluation metrics are real and reported (not hardcoded)
- Gemini's explanation text changes meaningfully based on the actual feature values for the selected borough/week (not a static template)
- Borough comparison and trend chart render from real processed data, not mock numbers
