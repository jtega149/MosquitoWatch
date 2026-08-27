from unittest.mock import Mock

import pytest
from pydantic import ValidationError

import embedding_service
import rag_chat_service
from embedding_service import cosine_distance_from_similarity, similarity_from_cosine_distance
from rag_chat_service import ChatResult
from schemas import ChatRequest, ChatResponse


def test_similarity_threshold_maps_to_redis_cosine_distance() -> None:
    assert round(cosine_distance_from_similarity(0.95), 2) == 0.05
    assert round(similarity_from_cosine_distance(0.05), 2) == 0.95


def test_l2_normalize_unit_length() -> None:
    values = embedding_service.l2_normalize([3.0, 4.0])
    assert round(values[0], 6) == 0.6
    assert round(values[1], 6) == 0.8


def test_answer_returns_cache_hit_without_calling_gemini(monkeypatch) -> None:
    generate = Mock(side_effect=AssertionError("Gemini should not run on a cache hit"))
    monkeypatch.setattr(rag_chat_service, "_generate", generate)
    monkeypatch.setattr(rag_chat_service, "retrieve_chunks", generate)
    monkeypatch.setattr(rag_chat_service, "_cache", object())
    monkeypatch.setattr(
        rag_chat_service.semantic_cache,
        "lookup",
        lambda _cache, _prompt: rag_chat_service.CacheLookup(
            response="Staten Island currently has the highest score.",
            similarity=0.98,
            prompt="which zip is highest risk",
        ),
    )

    result = rag_chat_service.answer("What ZIP has the most West Nile mosquitoes right now?")

    assert result == ChatResult(
        reply="Staten Island currently has the highest score.",
        cached=True,
        similarity=0.98,
    )
    generate.assert_not_called()


def test_answer_cache_miss_generates_and_stores(monkeypatch) -> None:
    cache = object()
    store = Mock()
    monkeypatch.setattr(rag_chat_service, "_cache", cache)
    monkeypatch.setattr(rag_chat_service.semantic_cache, "lookup", lambda *_args: None)
    monkeypatch.setattr(rag_chat_service.semantic_cache, "store", store)
    monkeypatch.setattr(rag_chat_service, "retrieve_chunks", lambda _prompt: ["context"])
    monkeypatch.setattr(rag_chat_service, "_generate", lambda _prompt, _chunks: "Grounded reply.")

    result = rag_chat_service.answer("How does the map work?")

    assert result.cached is False
    assert result.reply == "Grounded reply."
    store.assert_called_once_with(cache, "How does the map work?", "Grounded reply.")


def test_chat_request_rejects_blank_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="   ")


def test_chat_response_accepts_cache_hit_payload() -> None:
    body = ChatResponse(reply="Cached answer.", cached=True, similarity=0.97)
    assert body.model_dump() == {
        "reply": "Cached answer.",
        "cached": True,
        "similarity": 0.97,
    }
