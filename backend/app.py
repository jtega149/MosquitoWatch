from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import gemini_service
from schemas import HealthResponse, Indicators, PredictionRequest, PredictionResponse

app = FastAPI(title="MosquitoWatch NYC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    """Return a mock prediction with a Gemini-generated explanation."""

    prediction = PredictionResponse(
        zip_code=request.zip_code,
        borough="Staten Island",
        areas="Port Richmond / West Brighton",
        forecast_week=32,
        risk_score=76.0,
        risk_level="High",
        indicators=Indicators(
            positive_prev_week=2,
            positive_prev_2_weeks=4,
            positive_prev_4_weeks=7,
            temperature=83.0,
            rainfall=1.42,
            seasonality="Peak",
        ),
        explanation=gemini_service.FALLBACK_EXPLANATION,
    )

    explanation = gemini_service.generate_explanation(
        zip_code=prediction.zip_code,
        risk_score=prediction.risk_score,
        risk_level=prediction.risk_level,
        positive_prev_week=prediction.indicators.positive_prev_week,
        positive_prev_2_weeks=prediction.indicators.positive_prev_2_weeks,
        positive_prev_4_weeks=prediction.indicators.positive_prev_4_weeks,
        temperature=prediction.indicators.temperature,
        rainfall=prediction.indicators.rainfall,
        seasonality=prediction.indicators.seasonality,
    )
    return prediction.model_copy(update={"explanation": explanation})
