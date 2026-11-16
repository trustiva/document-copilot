from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.database.models import DocumentChunk, SourceDocument


@dataclass
class RetrievedPassage:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    ticker: str
    form: str
    filing_date: date
    accession_number: str
    source_url: str
    score: float = 0.0
    rank: int = 0
    search_method: str = "vector"

    def to_dict(self) -> dict:
        return {
            "chunk_id": str(self.chunk_id),
            "document_id": str(self.document_id),
            "chunk_index": self.chunk_index,
            "content": self.content,
            "ticker": self.ticker,
            "form": self.form,
            "filing_date": self.filing_date.isoformat(),
            "accession_number": self.accession_number,
            "source_url": self.source_url,
            "score": round(self.score, 6),
            "rank": self.rank,
            "search_method": self.search_method,
        }


def search_vector(
    session: Session,
    query_vector: Sequence[float],
    *,
    ticker: str | None = None,
    limit: int = 20,
) -> list[RetrievedPassage]:
    """Execute semantic cosine-similarity search against document_chunks."""
    distance_expr = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.chunk_index,
            DocumentChunk.content,
            SourceDocument.id.label("document_id"),
            SourceDocument.ticker,
            SourceDocument.form,
            SourceDocument.filing_date,
            SourceDocument.accession_number,
            SourceDocument.source_url,
            distance_expr,
        )
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.embedding.is_not(None))
    )

    if ticker:
        stmt = stmt.where(SourceDocument.ticker == ticker.upper())

    stmt = stmt.order_by("distance").limit(limit)
    rows = session.execute(stmt).all()

    results: list[RetrievedPassage] = []
    for rank_idx, row in enumerate(rows, start=1):
        # Convert cosine distance to approximate similarity score
        dist = row.distance
        similarity = max(0.0, 1.0 - float(dist)) if dist is not None else 0.0
        results.append(
            RetrievedPassage(
                chunk_id=row.id,
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                content=row.content,
                ticker=row.ticker,
                form=row.form,
                filing_date=row.filing_date,
                accession_number=row.accession_number,
                source_url=row.source_url,
                score=similarity,
                rank=rank_idx,
                search_method="vector",
            )
        )
    return results


def search_fulltext(
    session: Session,
    query: str,
    *,
    ticker: str | None = None,
    limit: int = 20,
) -> list[RetrievedPassage]:
    """Execute Postgres lexical full-text search against document_chunks.search_vector."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    # Use websearch_to_tsquery for natural analyst syntax, fallback to plainto_tsquery
    ts_query = func.websearch_to_tsquery("english", cleaned_query)
    rank_expr = func.ts_rank_cd(DocumentChunk.search_vector, ts_query).label("rank")

    select_cols = (
        DocumentChunk.id,
        DocumentChunk.chunk_index,
        DocumentChunk.content,
        SourceDocument.id.label("document_id"),
        SourceDocument.ticker,
        SourceDocument.form,
        SourceDocument.filing_date,
        SourceDocument.accession_number,
        SourceDocument.source_url,
    )

    stmt = (
        select(*select_cols, rank_expr)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.search_vector.op("@@")(ts_query))
    )

    if ticker:
        stmt = stmt.where(SourceDocument.ticker == ticker.upper())

    stmt = stmt.order_by(desc("rank")).limit(limit)
    rows = session.execute(stmt).all()

    # If websearch found no results (e.g. stop words or punctuation), try plainto_tsquery
    if not rows:
        plain_query = func.plainto_tsquery("english", cleaned_query)
        plain_rank_expr = func.ts_rank_cd(DocumentChunk.search_vector, plain_query).label("rank")
        stmt_fallback = (
            select(*select_cols, plain_rank_expr)
            .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
            .where(DocumentChunk.search_vector.op("@@")(plain_query))
        )
        if ticker:
            stmt_fallback = stmt_fallback.where(SourceDocument.ticker == ticker.upper())
        stmt_fallback = stmt_fallback.order_by(desc("rank")).limit(limit)
        rows = session.execute(stmt_fallback).all()

    results: list[RetrievedPassage] = []
    for rank_idx, row in enumerate(rows, start=1):
        score_val = float(row.rank) if row.rank is not None else 0.0
        results.append(
            RetrievedPassage(
                chunk_id=row.id,
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                content=row.content,
                ticker=row.ticker,
                form=row.form,
                filing_date=row.filing_date,
                accession_number=row.accession_number,
                source_url=row.source_url,
                score=score_val,
                rank=rank_idx,
                search_method="fulltext",
            )
        )
    return results
