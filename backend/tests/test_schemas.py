import pytest
from pydantic import ValidationError

from schemas import Indicators, PredictionRequest, PredictionResponse


def make_prediction_response(risk_score: float = 76.0) -> PredictionResponse:
    return PredictionResponse(
        zip_code="10310",
        borough="Staten Island",
        areas="Port Richmond / West Brighton",
        forecast_week=32,
        risk_score=risk_score,
        risk_level="High",
        indicators=Indicators(
            positive_prev_week=2,
            positive_prev_2_weeks=4,
            positive_prev_4_weeks=7,
            temperature=83.0,
            rainfall=1.42,
            seasonality=None,
        ),
        explanation="Mock explanation.",
    )


def test_prediction_contract_accepts_valid_values() -> None:
    request = PredictionRequest(zip_code="10310")
    response = make_prediction_response()

    assert request.model_dump() == {"zip_code": "10310"}
    assert response.risk_score == 76.0
    assert response.indicators.seasonality is None
    assert response.explanation == "Mock explanation."


@pytest.mark.parametrize("zip_code", ["1000", "100001", "ABCDE"])
def test_prediction_request_rejects_invalid_zip_codes(zip_code: str) -> None:
    with pytest.raises(ValidationError):
        PredictionRequest(zip_code=zip_code)


@pytest.mark.parametrize("risk_score", [-0.01, 100.01])
def test_prediction_response_rejects_out_of_range_risk_score(
    risk_score: float,
) -> None:
    with pytest.raises(ValidationError):
        make_prediction_response(risk_score=risk_score)


@pytest.mark.parametrize("risk_score", [0.0, 100.0])
def test_prediction_response_accepts_risk_score_boundaries(
    risk_score: float,
) -> None:
    assert make_prediction_response(risk_score=risk_score).risk_score == risk_score
