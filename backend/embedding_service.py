"""Gemini embeddings shared by the semantic cache and the RAG index."""

from __future__ import annotations

import numpy as np
from google import genai
from google.genai import types

from config import (
    EMBEDDING_DIMENSIONS,
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_MODEL,
)


class EmbeddingError(Exception):
    """Raised when Gemini embeddings cannot be produced."""


def embeddings_configured() -> bool:
    return bool(GEMINI_API_KEY and GEMINI_EMBEDDING_MODEL)


def l2_normalize(values: list[float]) -> list[float]:
    arr = np.asarray(values, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm == 0.0:
        return [float(v) for v in values]
    return (arr / norm).astype(float).tolist()


def cosine_distance_from_similarity(min_similarity: float) -> float:
    """Redis COSINE distance is 1 - cosine similarity, in [0, 2]."""

    return max(0.0, min(2.0, 1.0 - min_similarity))


def similarity_from_cosine_distance(distance: float) -> float:
    return 1.0 - float(distance)


def _embedding_values(item) -> list[float]:
    values = getattr(item, "values", None)
    if not values:
        raise EmbeddingError("Gemini returned an empty embedding.")
    return l2_normalize(list(values))


def embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
    if not texts:
        return []
    if not embeddings_configured():
        raise EmbeddingError("Gemini embeddings are not configured.")

    client = None
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        result = client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIMENSIONS,
            ),
        )
        embeddings = getattr(result, "embeddings", None) or []
        if len(embeddings) != len(texts):
            raise EmbeddingError("Gemini returned an unexpected embedding count.")
        return [_embedding_values(item) for item in embeddings]
    except EmbeddingError:
        raise
    except Exception as exc:
        raise EmbeddingError("Failed to embed text with Gemini.") from exc
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def embed_text(text: str, task_type: str) -> list[float]:
    return embed_texts([text], task_type=task_type)[0]


def embed_for_cache(text: str) -> list[float]:
    return embed_text(text, task_type="SEMANTIC_SIMILARITY")


def embed_for_query(text: str) -> list[float]:
    return embed_text(text, task_type="RETRIEVAL_QUERY")


def embed_for_documents(texts: list[str]) -> list[list[float]]:
    return embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")
