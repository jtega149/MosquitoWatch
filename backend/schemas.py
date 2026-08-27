"""Pydantic request and response schemas for the backend API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class ForecastDay(BaseModel):
    """One day inside the next-week (7-day) surveillance forecast window."""

    date: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str


class PredictionResponse(BaseModel):
    """Output contract for the future prediction endpoint."""

    zip_code: str = Field(..., pattern=r"^\d{5}$")
    borough: str
    areas: str
    forecast_week: int
    forecast_year: int
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str
    indicators: Indicators
    next_7_days: list[ForecastDay]
    explanation: str


class ZipResponse(BaseModel):
    """Public ZIP metadata."""

    zip_code: str = Field(..., pattern=r"^\d{5}$")
    borough: str
    areas: str


class ForecastResponse(BaseModel):
    """Map forecast summary without a Gemini explanation."""

    zip_code: str = Field(..., pattern=r"^\d{5}$")
    forecast_week: int
    forecast_year: int
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


class ChatRequest(BaseModel):
    """User question for the Gemini RAG assistant."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=500)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message cannot be blank")
        return cleaned


class ChatResponse(BaseModel):
    """Assistant reply, plus whether Redis served a semantic cache hit."""

    reply: str
    cached: bool
    similarity: float | None = Field(default=None, ge=0.0, le=1.0)


class ChatStatusResponse(BaseModel):
    """Operational flags for the RAG + cache stack."""

    redis_ready: bool
    cache_enabled: bool
    rag_index_enabled: bool
