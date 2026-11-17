from __future__ import annotations

import os

import pytest
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.test import TestModel

from app.assistant.agent import _resolve_model, create_document_agent
from app.config import Settings
from app.ingest.embedder import _generate_mock_embedding, _normalize_dim, generate_embeddings


def test_gemini_config_defaults() -> None:
    s = Settings(
        _env_file=None,
        allowed_origins="*",
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        supabase_url="https://test.supabase.co",
        supabase_anon_key="anon",
    )
    assert "gemini" in s.llm_model
    assert s.embedding_model == "text-embedding-004"
    assert s.embedding_dimension == 1536
    assert s.effective_gemini_api_key is None


def test_gemini_model_resolution_fallback() -> None:
    # When no Gemini API key is set, resolves to TestModel
    model = _resolve_model(None)
    assert isinstance(model, TestModel)


def test_gemini_model_resolution_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key-12345")
    model = _resolve_model(None)
    assert isinstance(model, GoogleModel)
    assert model.model_name == "gemini-2.5-flash"


def test_gemini_embedder_mock_fallback() -> None:
    texts = ["Apple iPhone net sales", "Microsoft Azure cloud growth"]
    vectors = generate_embeddings(texts)
    assert len(vectors) == 2
    for vec in vectors:
        assert len(vec) == 1536
        assert isinstance(vec[0], float)


def test_normalize_dim() -> None:
    short_vec = [1.0] * 768
    padded = _normalize_dim(short_vec, 1536)
    assert len(padded) == 1536
    assert padded[:768] == short_vec
    assert padded[768:] == [0.0] * 768

    long_vec = [2.0] * 2000
    truncated = _normalize_dim(long_vec, 1536)
    assert len(truncated) == 1536

    exact_vec = [3.0] * 1536
    assert _normalize_dim(exact_vec, 1536) == exact_vec
