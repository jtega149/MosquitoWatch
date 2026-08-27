from unittest.mock import Mock

from fastapi.testclient import TestClient

import data_service
import gemini_service
import model_service
from app import app


client = TestClient(app)


def patch_prediction_services(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.data_service.get_latest_features",
        lambda _zip: {"week_of_year": 33, "temp_mean": 23.8, "precip_sum": 61.4},
    )
    monkeypatch.setattr(
        "app.data_service.get_zip_metadata",
        lambda _zip: {
            "zip_code": "10310",
            "borough": "Staten Island",
            "areas": "Port Richmond, West Brighton",
        },
    )
    monkeypatch.setattr(
        "app.data_service.get_history",
        lambda _zip: [
            {"year": 2026, "week": 33, "positive_detections": 100},
            {"year": 2026, "week": 30, "positive_detections": 2},
            {"year": 2026, "week": 28, "positive_detections": 8},
            {"year": 2026, "week": 32, "positive_detections": 4},
            {"year": 2026, "week": 29, "positive_detections": 1},
            {"year": 2026, "week": 31, "positive_detections": 3},
        ],
    )
    monkeypatch.setattr(
        "app.model_service.predict_zip",
        lambda _zip: {"risk_score": 33.0, "risk_level": "Moderate"},
    )
    monkeypatch.setattr(
        "app.data_service.get_forecast_period",
        lambda: {
            "feature_week": 33,
            "feature_year": 2026,
            "forecast_week": 34,
            "forecast_year": 2026,
        },
    )


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_vite_development_origin() -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_allows_next_development_origin() -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_zips_returns_only_public_metadata_with_string_zip(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.data_service.get_all_zips",
        lambda: [{
            "zip_code": "10310",
            "zipcode": "10310",
            "borough": "Staten Island",
            "areas": "Port Richmond, West Brighton",
        }],
    )
    response = client.get("/zips")
    assert response.status_code == 200
    assert response.json() == [{
        "zip_code": "10310",
        "borough": "Staten Island",
        "areas": "Port Richmond, West Brighton",
    }]
    assert isinstance(response.json()[0]["zip_code"], str)


def test_predict_maps_real_services_and_prior_history(monkeypatch) -> None:
    patch_prediction_services(monkeypatch)
    gemini = Mock(return_value="Model result explained without changing it.")
    monkeypatch.setattr("app.gemini_service.generate_explanation", gemini)
    response = client.post("/predict", json={"zip_code": "10310"})
    assert response.status_code == 200
    days = data_service.next_7_days(
        2026, 34, 33.0, "Moderate", zip_code="10310", lat=40.75, lon=-73.98, temp_mean=23.8, humidity_mean=70.0, precip_sum=61.4
    )
    body = response.json()
    assert body == {
        "zip_code": "10310",
        "borough": "Staten Island",
        "areas": "Port Richmond, West Brighton",
        "forecast_week": 34,
        "forecast_year": 2026,
        "risk_score": 33.0,
        "risk_level": "Moderate",
        "indicators": {
            "positive_prev_week": 4,
            "positive_prev_2_weeks": 7,
            "positive_prev_4_weeks": 10,
            "temperature": 23.8,
            "rainfall": 61.4,
            "seasonality": "Peak mosquito season (Jun–Sep)",
        },
        "next_7_days": days,
        "explanation": "Model result explained without changing it.",
    }
    gemini.assert_called_once_with(
        zip_code="10310",
        risk_score=33.0,
        risk_level="Moderate",
        positive_prev_week=4,
        positive_prev_2_weeks=7,
        positive_prev_4_weeks=10,
        temperature=23.8,
        rainfall=61.4,
        seasonality="Peak mosquito season (Jun–Sep)",
    )


def test_gemini_output_cannot_modify_prediction(monkeypatch) -> None:
    patch_prediction_services(monkeypatch)
    malicious_output = 'Risk score: 0; risk level: Low; {"temperature": -99}'
    monkeypatch.setattr("app.gemini_service.generate_explanation", lambda **_: malicious_output)
    body = client.post("/predict", json={"zip_code": "10310"}).json()
    assert body["risk_score"] == 33.0
    assert body["risk_level"] == "Moderate"
    assert body["forecast_week"] == 34
    assert body["indicators"]["temperature"] == 23.8
    assert body["explanation"] == malicious_output


def test_gemini_failure_returns_fallback_and_http_200(monkeypatch) -> None:
    patch_prediction_services(monkeypatch)

    def fail(**_kwargs):
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr("app.gemini_service.generate_explanation", fail)
    response = client.post("/predict", json={"zip_code": "10310"})
    assert response.status_code == 200
    assert response.json()["risk_score"] == 33.0
    assert response.json()["explanation"] == gemini_service.FALLBACK_EXPLANATION


def test_predict_unknown_zip_returns_404(monkeypatch) -> None:
    def unknown(_zip):
        raise data_service.ZipNotFoundError("unknown")

    monkeypatch.setattr("app.data_service.get_latest_features", unknown)
    response = client.post("/predict", json={"zip_code": "99999"})
    assert response.status_code == 404
    assert response.json() == {"detail": "ZIP code not found"}


def test_predict_rejects_malformed_zip_code() -> None:
    assert client.post("/predict", json={"zip_code": "1031A"}).status_code == 422


def test_forecasts_returns_model_output_without_calling_gemini(monkeypatch) -> None:
    predictions = [
        {"zip_code": "10310", "risk_score": 33.0, "risk_level": "Moderate"},
        {"zip_code": "10001", "risk_score": 2.6, "risk_level": "Low"},
    ]
    monkeypatch.setattr("app.model_service.predict_all", lambda: predictions)
    monkeypatch.setattr(
        "app.data_service.get_forecast_period",
        lambda: {
            "feature_week": 33,
            "feature_year": 2026,
            "forecast_week": 34,
            "forecast_year": 2026,
        },
    )
    gemini = Mock()
    monkeypatch.setattr("app.gemini_service.generate_explanation", gemini)
    response = client.get("/forecasts")
    assert response.status_code == 200
    assert response.json() == [
        {
            "zip_code": "10310",
            "forecast_week": 34,
            "forecast_year": 2026,
            "risk_score": 33.0,
            "risk_level": "Moderate",
        },
        {
            "zip_code": "10001",
            "forecast_week": 34,
            "forecast_year": 2026,
            "risk_score": 2.6,
            "risk_level": "Low",
        },
    ]
    gemini.assert_not_called()


def test_trends_returns_real_history(monkeypatch) -> None:
    history = [
        {"year": 2026, "week": 32, "positive_detections": 1},
        {"year": 2026, "week": 33, "positive_detections": 0},
    ]
    monkeypatch.setattr("app.data_service.get_history", lambda _zip: history)
    response = client.get("/trends/10310")
    assert response.status_code == 200
    assert response.json() == {"zip_code": "10310", "history": history}


def test_trends_unknown_zip_returns_404(monkeypatch) -> None:
    def unknown(_zip):
        raise data_service.ZipNotFoundError("unknown")

    monkeypatch.setattr("app.data_service.get_history", unknown)
    assert client.get("/trends/99999").status_code == 404


def test_data_service_error_returns_controlled_500(monkeypatch) -> None:
    def fail():
        raise data_service.DataServiceError("private filesystem detail")

    monkeypatch.setattr("app.data_service.get_all_zips", fail)
    response = client.get("/zips")
    assert response.status_code == 500
    assert response.json() == {"detail": "Data service unavailable"}
    assert "filesystem" not in response.text


def test_model_service_error_returns_controlled_500(monkeypatch) -> None:
    def fail():
        raise model_service.ModelServiceError("private model detail")

    monkeypatch.setattr("app.model_service.predict_all", fail)
    response = client.get("/forecasts")
    assert response.status_code == 500
    assert response.json() == {"detail": "Prediction service unavailable"}
    assert "private model" not in response.text
