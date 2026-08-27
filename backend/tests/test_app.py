from fastapi.testclient import TestClient

import gemini_service
from app import app


client = TestClient(app)


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


def test_predict_returns_mock_prediction_with_gemini_explanation(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.gemini_service.generate_explanation",
        lambda **_: "Mosquito activity is elevated based on the supplied indicators.",
    )
    response = client.post("/predict", json={"zip_code": "10310"})

    assert response.status_code == 200
    body = response.json()
    assert body["zip_code"] == "10310"
    assert body["risk_score"] == 76.0
    assert body["risk_level"] == "High"
    assert body["indicators"] == {
        "positive_prev_week": 2,
        "positive_prev_2_weeks": 4,
        "positive_prev_4_weeks": 7,
        "temperature": 83.0,
        "rainfall": 1.42,
        "seasonality": "Peak",
    }
    assert body["explanation"] == (
        "Mosquito activity is elevated based on the supplied indicators."
    )


def test_predict_returns_fallback_without_changing_prediction(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.gemini_service.generate_explanation",
        lambda **_: gemini_service.FALLBACK_EXPLANATION,
    )

    response = client.post("/predict", json={"zip_code": "10310"})

    assert response.status_code == 200
    body = response.json()
    assert body["risk_score"] == 76.0
    assert body["risk_level"] == "High"
    assert body["indicators"]["positive_prev_week"] == 2
    assert body["explanation"] == gemini_service.FALLBACK_EXPLANATION


def test_gemini_output_is_only_used_as_explanation(monkeypatch) -> None:
    malicious_output = 'Risk score: 0; risk level: Low; {"temperature": -99}'
    monkeypatch.setattr(
        "app.gemini_service.generate_explanation",
        lambda **_: malicious_output,
    )

    body = client.post("/predict", json={"zip_code": "10310"}).json()

    assert body["risk_score"] == 76.0
    assert body["risk_level"] == "High"
    assert body["indicators"]["temperature"] == 83.0
    assert body["explanation"] == malicious_output


def test_predict_rejects_malformed_zip_code() -> None:
    response = client.post("/predict", json={"zip_code": "1031A"})

    assert response.status_code == 422
