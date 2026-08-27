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


def test_preprocessor_loads_without_error():
    preprocessor = model_service._load_preprocessor()
    assert preprocessor is not None
    assert hasattr(preprocessor, "transform")


def test_portable_artifacts_load_only_once(monkeypatch):
    real_joblib_load = model_service.joblib.load
    real_classifier = model_service.xgb.XGBClassifier
    load_counts = {"preprocessor": 0, "model": 0}

    def tracked_joblib_load(path):
        load_counts["preprocessor"] += 1
        return real_joblib_load(path)

    def tracked_classifier(*args, **kwargs):
        load_counts["model"] += 1
        return real_classifier(*args, **kwargs)

    monkeypatch.setattr(model_service.joblib, "load", tracked_joblib_load)
    monkeypatch.setattr(model_service.xgb, "XGBClassifier", tracked_classifier)

    p1 = model_service._load_preprocessor()
    p2 = model_service._load_preprocessor()
    m1 = model_service._load_model()
    m2 = model_service._load_model()

    assert p1 is p2
    assert m1 is m2
    assert load_counts == {"preprocessor": 1, "model": 1}


def test_reload_model_clears_both_cached_artifacts():
    model_service._load_preprocessor()
    model_service._load_model()

    model_service.reload_model()

    assert model_service._preprocessor is None
    assert model_service._model is None


def test_missing_preprocessor_raises_model_service_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        model_service,
        "PREPROCESSOR_PATH",
        str(tmp_path / "missing-preprocessing.joblib"),
    )

    with pytest.raises(model_service.ModelServiceError, match="Preprocessing artifact not found"):
        model_service._load_preprocessor()


def test_missing_xgboost_model_raises_model_service_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        model_service,
        "XGBOOST_MODEL_PATH",
        str(tmp_path / "missing-model.json"),
    )

    with pytest.raises(model_service.ModelServiceError, match="XGBoost model artifact not found"):
        model_service._load_model()


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
