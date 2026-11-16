from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.database.session import SessionLocal
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import RetrievedPassage
from app.retrieval.retriever import DocumentRetriever


def _make_dummy_passage(
    chunk_id: uuid.UUID,
    ticker: str = "AAPL",
    content: str = "Dummy text",
    rank: int = 1,
    method: str = "vector",
) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        document_id=uuid.uuid4(),
        chunk_index=rank - 1,
        content=content,
        ticker=ticker,
        form="10-K",
        filing_date=date(2026, 11, 3),
        accession_number=f"0000320193-26-{rank:06d}",
        source_url="https://sec.gov",
        score=0.9,
        rank=rank,
        search_method=method,
    )


def test_reciprocal_rank_fusion_single_list() -> None:
    id1, id2, id3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    v1 = _make_dummy_passage(id1, rank=1)
    v2 = _make_dummy_passage(id2, rank=2)
    v3 = _make_dummy_passage(id3, rank=3)

    fused = reciprocal_rank_fusion([v1, v2, v3], [], k=60)
    assert len(fused) == 3
    assert fused[0].chunk_id == id1
    assert fused[1].chunk_id == id2
    assert fused[2].chunk_id == id3
    assert fused[0].search_method == "vector"
    # RRF score for rank 1 with k=60 is 1/61
    assert pytest.approx(fused[0].score, 1e-5) == 1.0 / 61.0


def test_reciprocal_rank_fusion_boosts_overlap() -> None:
    id_overlap = uuid.uuid4()
    id_vec_only = uuid.uuid4()
    id_lex_only = uuid.uuid4()

    # Overlap item is rank 2 in vector and rank 2 in lexical
    # id_vec_only is rank 1 in vector only
    # id_lex_only is rank 1 in lexical only
    v_overlap = _make_dummy_passage(id_overlap, rank=2, method="vector")
    v_only = _make_dummy_passage(id_vec_only, rank=1, method="vector")

    l_overlap = _make_dummy_passage(id_overlap, rank=2, method="fulltext")
    l_only = _make_dummy_passage(id_lex_only, rank=1, method="fulltext")

    fused = reciprocal_rank_fusion([v_only, v_overlap], [l_only, l_overlap], k=60)

    # Overlap item has score: 1/62 + 1/62 = 2/62 = 0.032258
    # Rank 1 single list has score: 1/61 = 0.016393
    # Therefore, the overlapping item MUST rank first!
    assert fused[0].chunk_id == id_overlap
    assert fused[0].search_method == "hybrid"
    assert pytest.approx(fused[0].score, 1e-5) == (1.0 / 62.0) + (1.0 / 62.0)


def test_reciprocal_rank_fusion_limit() -> None:
    passages = [_make_dummy_passage(uuid.uuid4(), rank=i) for i in range(1, 10)]
    fused = reciprocal_rank_fusion(passages, [], k=60, limit=3)
    assert len(fused) == 3


@pytest.mark.integration
def test_document_retriever_hybrid_search() -> None:
    retriever = DocumentRetriever()
    results = retriever.search("iPhone and Services revenue mix shift", ticker="AAPL", limit=5)

    assert len(results) > 0
    # Every result must be for AAPL
    for r in results:
        assert r.ticker == "AAPL"
        assert r.content
        assert r.score > 0
        assert r.search_method in ("hybrid", "vector", "fulltext")


@pytest.mark.integration
def test_document_retriever_surrounding_chunks() -> None:
    retriever = DocumentRetriever()
    initial_results = retriever.search("iPhone", ticker="AAPL", limit=1)
    assert len(initial_results) == 1

    target_chunk = initial_results[0]
    surrounding = retriever.get_surrounding_chunks(target_chunk.chunk_id, window=1)

    # Should return at least target chunk plus available neighbors
    assert len(surrounding) >= 1
    chunk_indices = [c.chunk_index for c in surrounding]
    assert target_chunk.chunk_index in chunk_indices
    # Must be ordered by chunk_index
    assert chunk_indices == sorted(chunk_indices)
