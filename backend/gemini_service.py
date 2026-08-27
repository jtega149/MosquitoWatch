"""Generate plain-language explanations of completed mosquito forecasts."""

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL

FALLBACK_EXPLANATION = "AI explanation temporarily unavailable."


def generate_explanation(
    zip_code: str,
    risk_score: float,
    risk_level: str,
    positive_prev_week: int,
    positive_prev_2_weeks: int,
    positive_prev_4_weeks: int,
    temperature: float,
    rainfall: float,
    seasonality: str | None,
) -> str:
    """Explain a completed prediction without recalculating or changing it."""

    if not GEMINI_API_KEY:
        return FALLBACK_EXPLANATION

    seasonality_line = f"\n- Seasonality: {seasonality}" if seasonality is not None else ""
    prompt = f"""Explain the supplied MosquitoWatch forecast to a general audience.

The forecast concerns recorded West Nile-positive mosquito detections. It does not
predict human infection risk.

Supplied information:
- ZIP code: {zip_code}
- Risk score: {risk_score}
- Risk level: {risk_level}
- Positive detections in the previous week: {positive_prev_week}
- Positive detections in the previous 2 weeks: {positive_prev_2_weeks}
- Positive detections in the previous 4 weeks: {positive_prev_4_weeks}
- Temperature: {temperature}
- Rainfall: {rainfall}{seasonality_line}

Rules:
- Do not calculate a new forecast probability.
- Do not change the supplied risk score.
- Do not change the supplied risk level.
- Do not predict human infection risk.
- Do not invent measurements, causes, or facts.
- Only explain the supplied information.
- Keep the explanation concise, approximately 2 to 3 sentences.
"""

    client = None
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        explanation = response.text
        if not explanation or not explanation.strip():
            return FALLBACK_EXPLANATION
        return explanation.strip()
    except Exception:  # Gemini must never make a successful prediction fail.
        return FALLBACK_EXPLANATION
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
