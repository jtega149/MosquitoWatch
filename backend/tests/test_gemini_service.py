from types import SimpleNamespace
from unittest.mock import Mock

import gemini_service


EXPLANATION_ARGS = {
    "zip_code": "10310",
    "risk_score": 76.0,
    "risk_level": "High",
    "positive_prev_week": 2,
    "positive_prev_2_weeks": 4,
    "positive_prev_4_weeks": 7,
    "temperature": 83.0,
    "rainfall": 1.42,
    "seasonality": "Peak",
}


def test_missing_api_key_returns_fallback_without_creating_client(monkeypatch) -> None:
    client = Mock()
    monkeypatch.setattr(gemini_service, "GEMINI_API_KEY", None)
    monkeypatch.setattr(gemini_service.genai, "Client", client)

    result = gemini_service.generate_explanation(**EXPLANATION_ARGS)

    assert result == gemini_service.FALLBACK_EXPLANATION
    client.assert_not_called()


def test_success_returns_trimmed_text_and_sends_guardrails(monkeypatch) -> None:
    response = SimpleNamespace(text="  Supplied forecast explanation.  ")
    client = Mock()
    client.models.generate_content.return_value = response
    monkeypatch.setattr(gemini_service, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_service, "GEMINI_MODEL", "test-model")
    monkeypatch.setattr(gemini_service.genai, "Client", Mock(return_value=client))

    result = gemini_service.generate_explanation(**EXPLANATION_ARGS)

    assert result == "Supplied forecast explanation."
    call = client.models.generate_content.call_args
    assert call.kwargs["model"] == "test-model"
    prompt = call.kwargs["contents"]
    assert "Do not calculate a new forecast probability." in prompt
    assert "Do not change the supplied risk score." in prompt
    assert "Do not change the supplied risk level." in prompt
    assert "Do not predict human infection risk." in prompt
    assert "Do not invent measurements, causes, or facts." in prompt
    assert "Only explain the supplied information." in prompt
    assert "recorded West Nile-positive mosquito detections" in prompt
    client.close.assert_called_once()


def test_request_exception_returns_fallback(monkeypatch) -> None:
    client = Mock()
    client.models.generate_content.side_effect = RuntimeError("network unavailable")
    monkeypatch.setattr(gemini_service, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_service, "GEMINI_MODEL", "test-model")
    monkeypatch.setattr(gemini_service.genai, "Client", Mock(return_value=client))

    result = gemini_service.generate_explanation(**EXPLANATION_ARGS)

    assert result == gemini_service.FALLBACK_EXPLANATION


def test_empty_response_returns_fallback(monkeypatch) -> None:
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(text="   ")
    monkeypatch.setattr(gemini_service, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_service, "GEMINI_MODEL", "test-model")
    monkeypatch.setattr(gemini_service.genai, "Client", Mock(return_value=client))

    result = gemini_service.generate_explanation(**EXPLANATION_ARGS)

    assert result == gemini_service.FALLBACK_EXPLANATION
