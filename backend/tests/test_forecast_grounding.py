from forecast_grounding import summarize_forecasts


def test_summarize_forecasts_includes_stats_and_top_zips() -> None:
    text = summarize_forecasts(
        [
            {"zip_code": "10310", "risk_score": 41.2, "risk_level": "Moderate"},
            {"zip_code": "10001", "risk_score": 8.0, "risk_level": "Low"},
            {"zip_code": "11201", "risk_score": 62.5, "risk_level": "Elevated"},
        ],
        forecast_week=34,
        forecast_year=2026,
        as_of_date="2026-08-27",
        metadata_by_zip={
            "11201": {"borough": "Brooklyn", "areas": "Brooklyn Heights"},
            "10310": {"borough": "Staten Island", "areas": "Port Richmond"},
            "10001": {"borough": "Manhattan", "areas": "Chelsea"},
        },
    )
    assert "as of 2026-08-27" in text
    assert "week 34 of 2026" in text
    assert "Coverage: 3 NYC ZIP codes" in text
    assert "average 37.2" in text
    assert "minimum 8.0 at 10001 (Manhattan, Chelsea)" in text
    assert "maximum 62.5 at 11201 (Brooklyn, Brooklyn Heights)" in text
    assert "Elevated=1" in text
    assert "11201 (Brooklyn, Brooklyn Heights) 62.5 Elevated" in text
    assert "not whether any person is infected" in text


def test_summarize_forecasts_empty() -> None:
    text = summarize_forecasts(
        [],
        forecast_week=1,
        forecast_year=2026,
        as_of_date="2026-01-01",
    )
    assert "no ZIP forecasts are available" in text
