"""RedisVL vector index for knowledge docs and dated forecast summaries."""

from __future__ import annotations

import numpy as np
from redisvl.index import SearchIndex
from redisvl.query import FilterQuery, VectorQuery
from redisvl.query.filter import Tag

from config import EMBEDDING_DIMENSIONS, REDIS_URL
from embedding_service import embed_for_documents, embed_for_query
from forecast_grounding import current_forecast_document
from knowledge_corpus import KNOWLEDGE_DOCUMENTS


class RagIndexError(Exception):
    """Raised when the RAG vector index cannot be used."""


INDEX_SCHEMA = {
    "index": {
        "name": "mw_rag_v1",
        "prefix": "mw:rag",
        "storage_type": "hash",
    },
    "fields": [
        {"name": "text", "type": "text"},
        {"name": "source", "type": "tag"},
        {"name": "doc_type", "type": "tag"},
        {"name": "as_of_date", "type": "tag"},
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {
                "dims": EMBEDDING_DIMENSIONS,
                "distance_metric": "cosine",
                "algorithm": "hnsw",
                "datatype": "float32",
            },
        },
    ],
}


def build_index() -> SearchIndex:
    try:
        index = SearchIndex.from_dict(INDEX_SCHEMA, redis_url=REDIS_URL)
        index.create(overwrite=False)
        return index
    except Exception as exc:
        raise RagIndexError("Could not create the Redis RAG index.") from exc


def _as_float32_bytes(embedding: list[float]) -> bytes:
    return np.asarray(embedding, dtype=np.float32).tobytes()


def _load(index: SearchIndex, documents: list[dict[str, str]]) -> None:
    if not documents:
        return
    embeddings = embed_for_documents([doc["text"] for doc in documents])
    payload = []
    for doc, embedding in zip(documents, embeddings):
        payload.append({**doc, "embedding": _as_float32_bytes(embedding)})
    try:
        index.load(payload, id_field="id")
    except Exception as exc:
        raise RagIndexError("Could not load RAG documents into Redis.") from exc


def _has_knowledge(index: SearchIndex) -> bool:
    try:
        rows = index.query(
            FilterQuery(
                filter_expression=Tag("doc_type") == "knowledge",
                return_fields=["id"],
                num_results=1,
            )
        )
        return bool(rows)
    except Exception:
        return False


def seed_knowledge(index: SearchIndex) -> None:
    if _has_knowledge(index):
        return
    docs = [
        {
            "id": f"knowledge:{item['id']}",
            "text": item["text"],
            "source": item["source"],
            "doc_type": "knowledge",
            "as_of_date": "static",
        }
        for item in KNOWLEDGE_DOCUMENTS
    ]
    _load(index, docs)


def drop_stale_forecasts(index: SearchIndex, keep_date: str) -> int:
    """Delete forecast documents whose as_of_date metadata is not keep_date."""

    try:
        result = index.drop_by_filter(
            (Tag("doc_type") == "forecast") & (Tag("as_of_date") != keep_date)
        )
    except Exception as exc:
        raise RagIndexError("Could not delete stale forecast documents.") from exc
    return int(getattr(result, "processed", 0) or 0)


def ground_forecast(index: SearchIndex) -> dict[str, str]:
    document = current_forecast_document()
    try:
        drop_stale_forecasts(index, document["as_of_date"])
    except RagIndexError:
        pass
    _load(
        index,
        [
            {
                "id": document["id"],
                "text": document["text"],
                "source": document["source"],
                "doc_type": document["doc_type"],
                "as_of_date": document["as_of_date"],
            }
        ],
    )
    return document


def retrieve(index: SearchIndex, query: str, num_results: int = 4) -> list[str]:
    vector = embed_for_query(query)
    try:
        rows = index.query(
            VectorQuery(
                vector=vector,
                vector_field_name="embedding",
                return_fields=["text", "source", "doc_type", "as_of_date"],
                num_results=num_results,
            )
        )
    except Exception as exc:
        raise RagIndexError("RAG retrieval failed.") from exc

    chunks: list[str] = []
    for row in rows:
        text = row.get("text") if isinstance(row, dict) else None
        if text:
            chunks.append(str(text))
    return chunks
