"""RedisVL semantic cache for near-duplicate chat prompts."""

from __future__ import annotations

from dataclasses import dataclass

from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import CustomVectorizer

from config import CACHE_MIN_SIMILARITY, REDIS_URL
from embedding_service import (
    cosine_distance_from_similarity,
    embed_for_cache,
    similarity_from_cosine_distance,
)


class CacheError(Exception):
    """Raised when the semantic cache cannot be used."""


@dataclass(frozen=True)
class CacheLookup:
    response: str
    similarity: float
    prompt: str


def _vectorizer() -> CustomVectorizer:
    return CustomVectorizer(embed=lambda text, **_kwargs: embed_for_cache(text))


def build_cache() -> SemanticCache:
    try:
        return SemanticCache(
            name="mw_chat_cache",
            redis_url=REDIS_URL,
            distance_threshold=cosine_distance_from_similarity(CACHE_MIN_SIMILARITY),
            vectorizer=_vectorizer(),
            overwrite=False,
        )
    except Exception as exc:
        raise CacheError("Could not connect to the Redis semantic cache.") from exc


def lookup(cache: SemanticCache, prompt: str) -> CacheLookup | None:
    try:
        hits = cache.check(prompt=prompt, num_results=1)
    except Exception as exc:
        raise CacheError("Semantic cache lookup failed.") from exc
    if not hits:
        return None
    hit = hits[0]
    response = hit.get("response") if isinstance(hit, dict) else getattr(hit, "response", None)
    distance = (
        hit.get("vector_distance")
        if isinstance(hit, dict)
        else getattr(hit, "vector_distance", None)
    )
    cached_prompt = hit.get("prompt") if isinstance(hit, dict) else getattr(hit, "prompt", prompt)
    if not response:
        return None
    similarity = similarity_from_cosine_distance(float(distance or 0.0))
    if similarity < CACHE_MIN_SIMILARITY:
        return None
    return CacheLookup(response=str(response), similarity=similarity, prompt=str(cached_prompt))


def store(cache: SemanticCache, prompt: str, response: str) -> None:
    try:
        cache.store(prompt=prompt, response=response)
    except Exception as exc:
        raise CacheError("Semantic cache store failed.") from exc
