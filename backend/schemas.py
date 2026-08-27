"""Pydantic request and response schemas for the backend API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Response returned by the health-check endpoint."""

    status: Literal["ok"]


class PredictionRequest(BaseModel):
    """Input for the prediction endpoint."""

    model_config = ConfigDict(extra="forbid")

    zip_code: str = Field(
        ...,
        pattern=r"^\d{5}$",
        description="Five-digit NYC ZIP code.",
        examples=["10310"],
    )


class Indicators(BaseModel):
    """Recent surveillance, weather, and seasonal prediction indicators."""

    positive_prev_week: int
    positive_prev_2_weeks: int
    positive_prev_4_weeks: int
    temperature: float
    rainfall: float
    seasonality: str | None = None


class PredictionResponse(BaseModel):
    """Output contract for the future prediction endpoint."""

    zip_code: str = Field(..., pattern=r"^\d{5}$")
    borough: str
    areas: str
    forecast_week: int
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str
    indicators: Indicators
    explanation: str


class ZipResponse(BaseModel):
    """Public ZIP metadata."""

    zip_code: str = Field(..., pattern=r"^\d{5}$")
    borough: str
    areas: str


class ForecastResponse(BaseModel):
    """Map forecast summary without a Gemini explanation."""

    zip_code: str = Field(..., pattern=r"^\d{5}$")
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str


class TrendPoint(BaseModel):
    """One real historical surveillance observation."""

    year: int
    week: int
    positive_detections: int


class TrendsResponse(BaseModel):
    """Historical positive detections for one ZIP."""

    zip_code: str = Field(..., pattern=r"^\d{5}$")
    history: list[TrendPoint]
