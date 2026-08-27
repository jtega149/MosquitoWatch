from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    """Return a temporary mock prediction until model integration is ready."""

    return PredictionResponse(
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
        explanation="Mock explanation.",
    )
