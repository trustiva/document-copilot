from __future__ import annotations

import uuid
from typing import Sequence

from app.retrieval.queries import RetrievedPassage


def reciprocal_rank_fusion(
    vector_results: Sequence[RetrievedPassage],
    lexical_results: Sequence[RetrievedPassage],
    *,
    k: int = 60,
    limit: int | None = None,
) -> list[RetrievedPassage]:
    """Combine ranked results from vector and lexical searches using Reciprocal Rank Fusion (RRF).

    Formula:
        score(d) = sum_{m in methods} 1 / (k + rank_m(d))
    where rank_m(d) is 1-based.
    """
    scores: dict[uuid.UUID, float] = {}
    passages_by_id: dict[uuid.UUID, RetrievedPassage] = {}
    matched_methods: dict[uuid.UUID, set[str]] = {}

    # 1. Accumulate vector search ranks
    for rank_idx, item in enumerate(vector_results, start=1):
        chunk_id = item.chunk_id
        rrf_contrib = 1.0 / (k + rank_idx)
        scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_contrib
        matched_methods.setdefault(chunk_id, set()).add("vector")
        if chunk_id not in passages_by_id:
            passages_by_id[chunk_id] = item

    # 2. Accumulate lexical search ranks
    for rank_idx, item in enumerate(lexical_results, start=1):
        chunk_id = item.chunk_id
        rrf_contrib = 1.0 / (k + rank_idx)
        scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_contrib
        matched_methods.setdefault(chunk_id, set()).add("fulltext")
        if chunk_id not in passages_by_id:
            passages_by_id[chunk_id] = item

    # 3. Sort chunks by descending RRF score
    sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    if limit is not None:
        sorted_ids = sorted_ids[:limit]

    fused: list[RetrievedPassage] = []
    for new_rank, chunk_id in enumerate(sorted_ids, start=1):
        orig = passages_by_id[chunk_id]
        methods = matched_methods[chunk_id]
        method_str = "hybrid" if len(methods) > 1 else next(iter(methods))

        fused.append(
            RetrievedPassage(
                chunk_id=orig.chunk_id,
                document_id=orig.document_id,
                chunk_index=orig.chunk_index,
                content=orig.content,
                ticker=orig.ticker,
                form=orig.form,
                filing_date=orig.filing_date,
                accession_number=orig.accession_number,
                source_url=orig.source_url,
                score=scores[chunk_id],
                rank=new_rank,
                search_method=method_str,
            )
        )

    return fused
