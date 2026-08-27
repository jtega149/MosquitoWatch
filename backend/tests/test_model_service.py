import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import data_service
import model_service


def setup_function(_):
    data_service.reload_data()
    model_service.reload_model()


def test_model_loads_without_error():
    model = model_service._load_model()
    assert model is not None


def test_model_loads_only_once():
    m1 = model_service._load_model()
    m2 = model_service._load_model()
    assert m1 is m2  # same object -> not reloaded from disk


def test_predict_zip_valid_zip():
    result = model_service.predict_zip("10310")
    assert set(result.keys()) == {"risk_score", "risk_level"}
    assert 0.0 <= result["risk_score"] <= 100.0
    assert result["risk_level"] in {"Low", "Moderate", "Elevated", "High"}


def test_predict_zip_unknown_zip_raises():
    with pytest.raises(data_service.ZipNotFoundError):
        model_service.predict_zip("99999")


def test_predict_all_covers_every_zip():
    results = model_service.predict_all()
    all_zips = {z["zip_code"] for z in data_service.get_all_zips()}
    result_zips = {r["zip_code"] for r in results}
    assert result_zips == all_zips
    for r in results:
        assert 0.0 <= r["risk_score"] <= 100.0


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, "Low"),
        (24.9, "Low"),
        (25, "Moderate"),
        (49.9, "Moderate"),
        (50, "Elevated"),
        (74.9, "Elevated"),
        (75, "High"),
        (100, "High"),
    ],
)
def test_risk_level_thresholds(score, expected):
    assert model_service.get_risk_level(score) == expected
