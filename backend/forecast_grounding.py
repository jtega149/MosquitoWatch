"""Compact current-week forecast summaries for RAG grounding."""

from __future__ import annotations

from datetime import date

import data_service
import model_service


def _zip_label(zip_code: str, metadata_by_zip: dict[str, dict]) -> str:
    meta = metadata_by_zip.get(zip_code) or {}
    borough = str(meta.get("borough") or "").strip()
    areas = str(meta.get("areas") or "").strip()
    extras = ", ".join(part for part in (borough, areas) if part)
    if extras:
        return f"{zip_code} ({extras})"
    return zip_code


def summarize_forecasts(
    forecasts: list[dict],
    *,
    forecast_week: int,
    forecast_year: int,
    as_of_date: str,
    metadata_by_zip: dict[str, dict] | None = None,
) -> str:
    """Build a short stats paragraph. Safe to store as one vector document."""

    if not forecasts:
        return (
            f"Forecast summary for {as_of_date}, week {forecast_week} of {forecast_year}: "
            "no ZIP forecasts are available."
        )

    metadata_by_zip = metadata_by_zip or {}
    scores = [float(row["risk_score"]) for row in forecasts]
    mean_score = sum(scores) / len(scores)
    min_row = min(forecasts, key=lambda row: float(row["risk_score"]))
    max_row = max(forecasts, key=lambda row: float(row["risk_score"]))
    counts: dict[str, int] = {}
    for row in forecasts:
        level = str(row.get("risk_level") or "Unknown")
        counts[level] = counts.get(level, 0) + 1
    count_text = ", ".join(
        f"{level}={counts[level]}" for level in sorted(counts, key=lambda name: -counts[name])
    )
    top = sorted(forecasts, key=lambda row: float(row["risk_score"]), reverse=True)[:3]
    top_text = "; ".join(
        f"{_zip_label(str(row['zip_code']).zfill(5), metadata_by_zip)} "
        f"{float(row['risk_score']):.1f} {row['risk_level']}"
        for row in top
    )
    return (
        f"Current MosquitoWatch forecast summary as of {as_of_date} for week "
        f"{forecast_week} of {forecast_year}. Coverage: {len(forecasts)} NYC ZIP codes. "
        f"Risk score average {mean_score:.1f}, minimum {float(min_row['risk_score']):.1f} at "
        f"{_zip_label(str(min_row['zip_code']).zfill(5), metadata_by_zip)}, maximum "
        f"{float(max_row['risk_score']):.1f} at "
        f"{_zip_label(str(max_row['zip_code']).zfill(5), metadata_by_zip)}. "
        f"Counts by risk level: {count_text}. Highest likelihood of West Nile-positive "
        f"mosquito activity: {top_text}. These scores describe mosquito surveillance "
        f"activity, not whether any person is infected."
    )


def current_forecast_document() -> dict[str, str]:
    period = data_service.get_forecast_period()
    forecasts = model_service.predict_all()
    metadata_by_zip = {
        str(item["zip_code"]).zfill(5): item for item in data_service.get_all_zips()
    }
    as_of = date.today().isoformat()
    week = int(period["forecast_week"])
    year = int(period["forecast_year"])
    return {
        "id": f"forecast:{as_of}",
        "source": "ml_forecast",
        "doc_type": "forecast",
        "as_of_date": as_of,
        "forecast_week": str(week),
        "forecast_year": str(year),
        "text": summarize_forecasts(
            forecasts,
            forecast_week=week,
            forecast_year=year,
            as_of_date=as_of,
            metadata_by_zip=metadata_by_zip,
        ),
    }
