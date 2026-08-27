from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import data_service
import gemini_service
import model_service
from schemas import (
    ForecastDay,
    ForecastResponse,
    HealthResponse,
    Indicators,
    PredictionRequest,
    PredictionResponse,
    TrendsResponse,
    ZipResponse,
)

app = FastAPI(title="MosquitoWatch NYC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(data_service.ZipNotFoundError)
def handle_zip_not_found(
    _request: Request, _exc: data_service.ZipNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "ZIP code not found"})


@app.exception_handler(data_service.DataServiceError)
def handle_data_service_error(
    _request: Request, _exc: data_service.DataServiceError
) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Data service unavailable"})


@app.exception_handler(model_service.ModelServiceError)
def handle_model_service_error(
    _request: Request, _exc: model_service.ModelServiceError
) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Prediction service unavailable"})


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/zips", response_model=list[ZipResponse])
def zips() -> list[ZipResponse]:
    return [ZipResponse(**item) for item in data_service.get_all_zips()]


def _history_indicators(history: list[dict], feature_week: int) -> tuple[int, int, int]:
    prior_rows = sorted(
        (row for row in history if int(row["week"]) < feature_week),
        key=lambda row: (int(row["year"]), int(row["week"])),
    )
    counts = [int(row["positive_detections"]) for row in prior_rows]
    return sum(counts[-1:]), sum(counts[-2:]), sum(counts[-4:])


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    """Return a real next-week ML forecast with an optional AI explanation."""

    features = data_service.get_latest_features(request.zip_code)
    metadata = data_service.get_zip_metadata(request.zip_code)
    history = data_service.get_history(request.zip_code)
    model_result = model_service.predict_zip(request.zip_code)
    period = data_service.get_forecast_period()
    feature_week = int(features["week_of_year"])
    previous_1, previous_2, previous_4 = _history_indicators(history, feature_week)
    risk_score = float(model_result["risk_score"])
    risk_level = str(model_result["risk_level"])
    forecast_week = int(period["forecast_week"])
    forecast_year = int(period["forecast_year"])
    seasonality = data_service.seasonality_label(forecast_week)
    prediction = PredictionResponse(
        zip_code=request.zip_code,
        borough=str(metadata["borough"]),
        areas=str(metadata["areas"]),
        forecast_week=forecast_week,
        forecast_year=forecast_year,
        risk_score=risk_score,
        risk_level=risk_level,
        indicators=Indicators(
            positive_prev_week=previous_1,
            positive_prev_2_weeks=previous_2,
            positive_prev_4_weeks=previous_4,
            temperature=float(features["temp_mean"]),
            rainfall=float(features["precip_sum"]),
            seasonality=seasonality,
        ),
        next_7_days=[
            ForecastDay(**day)
            for day in data_service.next_7_days(
                forecast_year, forecast_week, risk_score, risk_level
            )
        ],
        explanation=gemini_service.FALLBACK_EXPLANATION,
    )

    try:
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
    except Exception:
        explanation = gemini_service.FALLBACK_EXPLANATION
    return prediction.model_copy(update={"explanation": explanation})


@app.get("/forecasts", response_model=list[ForecastResponse])
def forecasts() -> list[ForecastResponse]:
    period = data_service.get_forecast_period()
    return [
        ForecastResponse(
            **item,
            forecast_week=int(period["forecast_week"]),
            forecast_year=int(period["forecast_year"]),
        )
        for item in model_service.predict_all()
    ]


@app.get("/trends/{zip_code}", response_model=TrendsResponse)
def trends(zip_code: str) -> TrendsResponse:
    return TrendsResponse(zip_code=zip_code, history=data_service.get_history(zip_code))
