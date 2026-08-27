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
    seasonality: str


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
