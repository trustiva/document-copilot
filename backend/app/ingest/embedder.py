from __future__ import annotations

import hashlib
import math
import random
from typing import Sequence

import structlog
from google import genai
from google.genai import types

from app.config import settings

logger = structlog.get_logger(__name__)


def _generate_mock_embedding(text: str, dim: int = 1536) -> list[float]:
    """Generate a deterministic, unit-normalized float vector from text hash."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    vec = [rng.gauss(0, 1) for _ in range(dim)]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]


def _normalize_dim(vec: list[float], target_dim: int = 1536) -> list[float]:
    """Ensure vector strictly matches target dimension for Postgres pgvector."""
    if len(vec) == target_dim:
        return vec
    if len(vec) > target_dim:
        return vec[:target_dim]
    return vec + [0.0] * (target_dim - len(vec))


def generate_embeddings(
    texts: Sequence[str],
    *,
    batch_size: int = 64,
) -> list[list[float]]:
    """Generate 1536-dim embeddings using Gemini text-embedding-004,

    falling back to deterministic mock vectors if GEMINI_API_KEY is unset.
    """
    if not texts:
        return []

    api_key = settings.effective_gemini_api_key
    if not api_key or api_key.startswith("your-") or api_key == "mock":
        logger.warning(
            "GEMINI_API_KEY is not configured; using deterministic mock embeddings.",
            count=len(texts),
            dimensions=settings.embedding_dimension,
        )
        return [_generate_mock_embedding(t, settings.embedding_dimension) for t in texts]

    client = genai.Client(api_key=api_key)
    results: list[list[float]] = []

    try:
        config = types.EmbedContentConfig(
            output_dimensionality=settings.embedding_dimension,
        )
        for i in range(0, len(texts), batch_size):
            batch = list(texts[i : i + batch_size])
            response = client.models.embed_content(
                model=settings.embedding_model,
                contents=batch,
                config=config,
            )
            if response.embeddings:
                for emb in response.embeddings:
                    vec = emb.values or []
                    results.append(_normalize_dim(vec, settings.embedding_dimension))
            else:
                for t in batch:
                    results.append(_generate_mock_embedding(t, settings.embedding_dimension))
        return results
    except Exception as exc:
        logger.warning(
            "Gemini embeddings call failed (e.g. rate limit / network error); falling back to deterministic mock vectors.",
            error=str(exc),
            count=len(texts),
        )
        return [_generate_mock_embedding(t, settings.embedding_dimension) for t in texts]


def embed_query(query: str) -> list[float]:
    """Generate embedding for a single search query."""
    vectors = generate_embeddings([query])
    if vectors:
        return vectors[0]
    return _generate_mock_embedding(query, settings.embedding_dimension)
