"""Gemini RAG answers with a Redis semantic cache in front."""

from __future__ import annotations

import os
from dataclasses import dataclass
import logging

from google import genai
from redisvl.extensions.cache.llm import SemanticCache
from redisvl.index import SearchIndex

from config import GEMINI_API_KEY, GEMINI_MODEL
from forecast_grounding import current_forecast_document
from knowledge_corpus import KNOWLEDGE_DOCUMENTS
import rag_index
import semantic_cache
from semantic_cache import CacheLookup

logger = logging.getLogger("uvicorn.error")

FALLBACK_REPLY = (
    "I cannot answer right now. Try again in a moment, or use the dashboard map and ZIP lookup."
)

SYSTEM_RULES = """You are the MosquitoWatch NYC assistant.

Answer only from the retrieved context. If the context is missing the answer, say you do not know.

Rules:
- The app forecasts West Nile-positive mosquito activity by ZIP, not whether a person is infected.
- Do not invent ZIP scores, dates, or medical claims.
- For symptoms: share only the public-health facts in the context and tell the user this is not a diagnosis.
- If they describe emergency signs (high fever, stiff neck, confusion, seizures, muscle weakness, vision loss), tell them to seek emergency care now.
- Keep answers concise, about 4 to 8 sentences.
"""


@dataclass
class ChatResult:
    reply: str
    cached: bool
    similarity: float | None


_cache: SemanticCache | None = None
_index: SearchIndex | None = None
_ready = False


def status() -> dict:
    return {
        "redis_ready": _ready,
        "cache_enabled": _cache is not None,
        "rag_index_enabled": _index is not None,
    }


def startup() -> None:
    """Best-effort Redis wiring so a down cache never blocks the rest of the API."""

    global _cache, _index, _ready
    if os.getenv("RAG_SKIP_STARTUP") == "1":
        _cache = None
        _index = None
        _ready = False
        return
    try:
        index = rag_index.build_index()
        rag_index.seed_knowledge(index)
        rag_index.ground_forecast(index)
        cache = semantic_cache.build_cache()
    except Exception:
        logger.exception("RAG Redis stack unavailable; chat will skip the semantic cache")
        _cache = None
        _index = None
        _ready = False
        return
    _index = index
    _cache = cache
    _ready = True
    logger.info("RAG Redis stack ready: semantic cache + forecast-grounded index")


def _generate(prompt: str, context_chunks: list[str]) -> str:
    if not GEMINI_API_KEY or not GEMINI_MODEL:
        return FALLBACK_REPLY
    context = "\n\n".join(context_chunks) if context_chunks else "No retrieved context."
    payload = (
        f"{SYSTEM_RULES}\n\nRetrieved context:\n{context}\n\nUser question:\n{prompt}\n"
    )
    client = None
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        interaction = client.interactions.create(model=GEMINI_MODEL, input=payload)
        text = getattr(interaction, "output_text", None)
        if not text or not str(text).strip():
            return FALLBACK_REPLY
        return str(text).strip()
    except Exception:
        return FALLBACK_REPLY
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def _fallback_chunks() -> list[str]:
    chunks = [item["text"] for item in KNOWLEDGE_DOCUMENTS]
    try:
        chunks.append(current_forecast_document()["text"])
    except Exception:
        pass
    return chunks


def retrieve_chunks(prompt: str) -> list[str]:
    if _index is not None:
        try:
            chunks = rag_index.retrieve(_index, prompt)
            if chunks:
                return chunks
        except Exception:
            pass
    return _fallback_chunks()


def answer(prompt: str) -> ChatResult:
    cleaned = prompt.strip()
    preview = cleaned if len(cleaned) <= 80 else f"{cleaned[:77]}..."
    if _cache is not None:
        try:
            hit: CacheLookup | None = semantic_cache.lookup(_cache, cleaned)
        except Exception:
            logger.warning("Semantic cache lookup failed; treating as miss")
            hit = None
        if hit is not None:
            logger.info(
                "CACHE HIT similarity=%.3f prompt=%r",
                hit.similarity,
                preview,
            )
            return ChatResult(reply=hit.response, cached=True, similarity=hit.similarity)

    chunks = retrieve_chunks(cleaned)
    reply = _generate(cleaned, chunks)
    stored = False
    if _cache is not None and reply != FALLBACK_REPLY:
        try:
            semantic_cache.store(_cache, cleaned, reply)
            stored = True
        except Exception:
            logger.warning("Semantic cache store failed")
    logger.info(
        "CACHE MISS stored=%s redis=%s chunks=%s prompt=%r",
        stored,
        _cache is not None,
        len(chunks),
        preview,
    )
    return ChatResult(reply=reply, cached=False, similarity=None)
