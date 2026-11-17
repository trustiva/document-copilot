from __future__ import annotations

import hashlib
import math
import random
from typing import Sequence

import structlog
from openai import OpenAI

from app.config import settings

logger = structlog.get_logger(__name__)


def _generate_mock_embedding(text: str, dim: int = 1536) -> list[float]:
    """Generate a deterministic, unit-normalized float vector from text hash."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    vec = [rng.gauss(0, 1) for _ in range(dim)]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]


def generate_embeddings(
    texts: Sequence[str],
    *,
    batch_size: int = 64,
) -> list[list[float]]:
    """Generate 1536-dim embeddings using OpenAI text-embedding-3-small,

    falling back to deterministic mock vectors if OPENAI_API_KEY is unset.
    """
    if not texts:
        return []

    api_key = settings.openai_api_key
    if not api_key or api_key.startswith("your-") or api_key == "mock":
        logger.warning(
            "OPENAI_API_KEY is not configured; using deterministic mock embeddings.",
            count=len(texts),
            dimensions=settings.embedding_dimension,
        )
        return [_generate_mock_embedding(t, settings.embedding_dimension) for t in texts]

    client = OpenAI(api_key=api_key)
    results: list[list[float]] = []

    try:
        for i in range(0, len(texts), batch_size):
            batch = list(texts[i : i + batch_size])
            response = client.embeddings.create(
                model=settings.embedding_model,
                input=batch,
            )
            # Sort by index to preserve order
            ordered = sorted(response.data, key=lambda item: item.index)
            results.extend([item.embedding for item in ordered])
        return results
    except Exception as exc:
        logger.warning(
            "OpenAI embeddings call failed (e.g. rate limit / no credits remaining); falling back to deterministic mock vectors.",
            error=str(exc),
            count=len(texts),
        )
        return [_generate_mock_embedding(t, settings.embedding_dimension) for t in texts]


def embed_query(query: str) -> list[float]:
    """Generate embedding for a single search query."""
    return generate_embeddings([query])[0]
