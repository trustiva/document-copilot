from __future__ import annotations

import uuid
from typing import Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import DocumentChunk, SourceDocument
from app.database.session import SessionLocal
from app.ingest.embedder import embed_query
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import (
    RetrievedPassage,
    search_fulltext,
    search_vector,
)

logger = structlog.get_logger(__name__)


class DocumentRetriever:
    """Hybrid search service combining semantic pgvector, Postgres full-text, and RRF."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def _get_session(self) -> Session:
        if self._session is not None:
            return self._session
        return SessionLocal()

    def search(
        self,
        query: str,
        *,
        ticker: str | None = None,
        limit: int = 10,
        vector_limit: int = 25,
        lexical_limit: int = 25,
        rrf_k: int = 60,
    ) -> list[RetrievedPassage]:
        """Execute hybrid search using pgvector and Postgres full-text with RRF."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        session = self._get_session()
        should_close = self._session is None

        try:
            # 1. Embed query
            query_vector = embed_query(cleaned_query)

            # 2. Run vector and lexical searches
            vector_results = search_vector(
                session,
                query_vector,
                ticker=ticker,
                limit=vector_limit,
            )
            lexical_results = search_fulltext(
                session,
                cleaned_query,
                ticker=ticker,
                limit=lexical_limit,
            )

            # 3. Fuse with Reciprocal Rank Fusion
            fused = reciprocal_rank_fusion(
                vector_results,
                lexical_results,
                k=rrf_k,
                limit=limit,
            )

            logger.info(
                "Hybrid search completed",
                query=cleaned_query,
                ticker=ticker,
                vector_candidates=len(vector_results),
                lexical_candidates=len(lexical_results),
                fused_results=len(fused),
            )
            return fused
        finally:
            if should_close:
                session.close()

    def get_chunk_by_id(self, chunk_id: uuid.UUID) -> RetrievedPassage | None:
        """Fetch a specific chunk by its primary key with document metadata."""
        session = self._get_session()
        should_close = self._session is None

        try:
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
                )
                .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
                .where(DocumentChunk.id == chunk_id)
            )
            row = session.execute(stmt).first()
            if not row:
                return None

            return RetrievedPassage(
                chunk_id=row.id,
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                content=row.content,
                ticker=row.ticker,
                form=row.form,
                filing_date=row.filing_date,
                accession_number=row.accession_number,
                source_url=row.source_url,
                score=1.0,
                rank=1,
                search_method="direct",
            )
        finally:
            if should_close:
                session.close()

    def get_surrounding_chunks(
        self,
        chunk_id: uuid.UUID,
        window: int = 1,
    ) -> list[RetrievedPassage]:
        """Fetch neighboring chunks within +/- window around target chunk for broader grounding context."""
        session = self._get_session()
        should_close = self._session is None

        try:
            # 1. Look up target chunk
            stmt_target = select(DocumentChunk.document_id, DocumentChunk.chunk_index).where(
                DocumentChunk.id == chunk_id
            )
            target = session.execute(stmt_target).first()
            if not target:
                return []

            doc_id, target_idx = target
            min_idx = max(0, target_idx - window)
            max_idx = target_idx + window

            stmt_surrounding = (
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
                )
                .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
                .where(
                    DocumentChunk.document_id == doc_id,
                    DocumentChunk.chunk_index >= min_idx,
                    DocumentChunk.chunk_index <= max_idx,
                )
                .order_by(DocumentChunk.chunk_index.asc())
            )

            rows = session.execute(stmt_surrounding).all()
            return [
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
                    score=1.0,
                    rank=idx,
                    search_method="surrounding",
                )
                for idx, row in enumerate(rows, start=1)
            ]
        finally:
            if should_close:
                session.close()
