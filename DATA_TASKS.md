# Data Tasks

**Owner:** Data Engineer  
**Status:** Completed (2026-08-27)  
**Main responsibility:** Ingest, clean, and join NYC Health West Nile surveillance data with weather signals into a modeling-ready table.

**Deliverable (output contract → ML):** `data/processed/training_data.csv`

This file is the handoff for the ML engineer (and any agent training Linear Regression, XGBoost, and Random Forest). Read it before fitting models.

---

## Status

Surveillance + weather join is done. Do **not** re-scrape unless NYC updates the public table. Rebuild with:

```bash
python3 data/build_training_data.py
```

| File | What it is |
|---|---|
| `data/processed/training_data.csv` | **Train on this.** One row per ZIP × week. |
| `data/raw/wnv_positive_mosquitoes_2026.csv` | NYC table as published (one row per ZIP). |
| `data/raw/wnv_positive_trap_dates_long_2026.csv` | Positive trap dates exploded to one row per date. |
| `data/build_training_data.py` | Reproducible ingest (Datawrapper + Census centroids + Open-Meteo). |

**Source:** [NYC DOH West Nile Virus Activity](https://www.nyc.gov/site/doh/health/health-topics/west-nile-virus-activity.page) (Datawrapper chart `Ys9mm` v13, last updated **2026-08-21**). Weather: Open-Meteo daily archive at ZIP centroids (Census 2025 ZCTA; borough centroid fallback for `10048`, `10281`, `11251`; `00083` = Central Park).

---

## What the table is (grain)

**One row = one ZIP code in one week (Monday-start), year 2026 only.**

- 193 ZIPs × 12 weeks = **2,316 rows**
- Weeks: `2026-06-01` through `2026-08-17` (covers the published season through the Aug 21 update)
- 99 ZIPs had ≥1 positive trap date; 94 never did (`Not detected`)
- 531 positive trap dates rolled up into weeks

Zeros are intentional. The public table only lists positive dates, but every ZIP in the city list is kept for every week so models can see non-events.

NYC’s own caveat still applies: *lack of detection in a ZIP does not mean virus is absent.* There is **no trap-effort / pools-tested column**. A zero can mean “traps were negative,” “no traps that week,” or “not reported.” Treat `elevated == 0` as “no reported positive,” not proven absence.

---

## What the 2026 season looks like (for modelers)

Activity ramps through July and peaks in early August, then the last week looks quieter partly because the week of `2026-08-17` is **truncated** (table freeze Aug 21).

| Week start | Elevated ZIPs | Positive trap dates |
|---|---:|---:|
| 2026-06-01 | 0 | 0 |
| 2026-06-08 | 0 | 0 |
| 2026-06-15 | 6 | 6 |
| 2026-06-22 | 8 | 10 |
| 2026-06-29 | 16 | 19 |
| 2026-07-06 | 36 | 46 |
| 2026-07-13 | 58 | 70 |
| 2026-07-20 | 69 | 87 |
| 2026-07-27 | 69 | 86 |
| 2026-08-03 | 75 | 92 |
| 2026-08-10 | 69 | 81 |
| 2026-08-17 | 31 | 34 |

**Class balance:** `elevated` is 437 / 2316 ≈ **18.9% positive**. `positive_count` is sparse: mostly 0, then 1, rarely 2–4 (max 4).

**Geography is not uniform.** Elevated ZIP-week rates:

- Staten Island ~52%
- Queens ~24%
- Brooklyn ~20%
- Bronx ~18%
- Manhattan ~3.7%

Borough (or ZIP) will likely dominate naive models. Weather still matters for week-to-week change, but a model that only learns “Staten Island in August” can look strong and fail next season.

All rows are meteorological **summer**, so `season` has **no variance** in this file. Use `week_of_year` / `week_sin` / `week_cos` for within-season timing.

---

## Targets

Use **one** primary target; do not mix them in the same label.

| Column | Type | Use |
|---|---|---|
| `elevated` | 0/1 | Recommended classification target: any reported positive in that ZIP-week. |
| `positive_count` | integer 0–4 | Optional regression / count model. It is **not** trap count or mosquito count — it is how many **positive trap dates** fell in that week. |

Product language: predict **elevated West Nile-positive mosquito activity by ZIP and week**, not human infection risk.

---

## Feature dictionary

### Identifiers / metadata (not default model inputs)

| Column | Notes |
|---|---|
| `year` | Always 2026. |
| `week_start` | Monday of the week. Use for time-based splits and joins, not as a raw numeric feature. |
| `neighborhoods` | Free text; empty on 1,128 rows (almost all never-detected ZIPs). Do not one-hot. |
| `latitude`, `longitude` | ZIP centroid used for weather. Optional spatial features; trees can use them. |
| `zip_detection_status` | **LEAKAGE. Do not use.** Snapshot as of 2026-08-21 (`Not detected` / `Detected in the past 2 weeks` / `Detected earlier this season`). It is the ZIP’s current public label, not a week-level feature. It perfectly separates ZIPs that ever had a positive this season. |

### Recommended predictors

**Time**

| Column | Notes |
|---|---|
| `week_of_year` | Integer week (Sunday-based `%U`). Strong seasonality. |
| `week_sin`, `week_cos` | Cyclic encoding of week. Prefer these over raw week for Linear Regression. |
| `season` | Constant `summer` in this extract — safe to drop. |

**Place**

| Column | Notes |
|---|---|
| `zipcode` | 5-character string (keep leading zeros; `00083` is Central Park). High cardinality (193). Trees: categorical or integer-encoded. Linear Regression: **do not** dump 193 dummies without regularization; use `borough`, grouped ZIP, or target encoding fit **only on the train fold**. |
| `borough` | Manhattan, Brooklyn, Queens, Bronx, Staten Island. Low-cardinality place effect. |

**Same-week weather** (°C, %, mm; week mean or sum)

| Column | Notes |
|---|---|
| `temp_mean`, `temp_max`, `temp_min` | Daily temps averaged over Mon–Sun. |
| `humidity_mean` | Daily mean relative humidity, averaged over the week. |
| `precip_sum` | Total precipitation that week (mm). |

**Lagged / window weather (prefer these over same-day only)**

Mosquito development lags weather by about 1–2 weeks.

| Column | Window |
|---|---|
| `temp_mean_lag7` | Mean temp, 7 days immediately before `week_start`. |
| `temp_mean_lag14` | Mean temp, days 14–8 before `week_start`. |
| `humidity_mean_lag7` | Mean RH, 7 days before `week_start`. |
| `precip_7d` | Precip sum, 7 days before `week_start`. |
| `precip_14d` | Precip sum from 7 days before `week_start` through week end. |
| `degree_days_14d` | Sum of `max(0, daily_mean_temp_C − 15)` over 14 days ending at week end. |

**Autoregressive history (ZIP-specific; no leakage if you do not shuffle time)**

| Column | Notes |
|---|---|
| `positives_last_1w` | This ZIP’s `positive_count` last week (0 in the first week). |
| `positives_last_2_4w` | Sum of this ZIP’s counts in weeks t−2, t−3, t−4. |

These are valid **only if** rows are ordered in time and the split is forward-chaining. A random row split leaks future activity into the past.

### Suggested default feature set

```
week_sin, week_cos, week_of_year,
borough, zipcode,
temp_mean, temp_mean_lag7, temp_mean_lag14,
humidity_mean, humidity_mean_lag7,
precip_7d, precip_14d, degree_days_14d,
positives_last_1w, positives_last_2_4w
```

Target: `elevated` (primary), optionally also train `positive_count`.

---

## How to train without cheating

1. **Split by time, not by random rows.** Example: train weeks through `2026-07-27`, validate `2026-08-03` and `2026-08-10`, treat `2026-08-17` as incomplete or hold out. With only 12 weeks, consider leave-future-week-out or expanding-window CV.
2. **Do not include** `zip_detection_status`, `elevated`, or `positive_count` as features (except the *lagged* count columns already built).
3. **Imbalanced classification:** ~19% elevated. Report PR-AUC / F1 / recall at a chosen alert threshold, not accuracy alone. Class weights or `scale_pos_weight` are reasonable.
4. **Linear Regression / logistic:** encode borough; cyclic week; scale continuous weather; regularize if using ZIP.
5. **Random Forest / XGBoost:** can take ZIP as a category; still check that importance is not 100% ZIP + week with unused weather.
6. **Compare three models** on the **same** time split and the **same** feature set so the comparison is fair.
7. There is **no prior year** in this file. You cannot yet build “same week last year.” Generalization to 2027 is untested.

---

## Known limitations (do not hide these in model cards)

- Single season (2026, June–mid-August only).
- Positives only from the public table; no negative trap counts, no species, no pool size.
- Last week is truncated by the Aug 21 publication date.
- Weather is reanalysis at ZIP centroid, not a trap-site thermometer. Nearby ZIPs can share similar weather.
- `00083` is not a USPS ZIP; it is NYC’s Central Park code.

---

## Backend contract (after you train)

Write to `ml/artifacts/`:

- `model.joblib`
- `latest_features.csv` — feature rows for the most recent complete week, same schema the model was fit on (no leakage columns)
- `model_metadata.json` — model type, features, target, train weeks, metrics, threshold
- `zip_metadata.csv` — ZIP, borough, neighborhoods, lat/lon for the dashboard
