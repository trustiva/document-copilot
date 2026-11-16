from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database.models import DocumentChunk, SourceDocument


def upsert_source_document(
    session: Session,
    *,
    ticker: str,
    form: str,
    filing_date: date,
    accession_number: str,
    source_url: str,
    markdown: str,
) -> SourceDocument:
    """Insert or update a source document, clearing existing chunks if updating."""
    stmt = select(SourceDocument).where(
        SourceDocument.accession_number == accession_number
    )
    doc = session.execute(stmt).scalar_one_or_none()

    if doc is not None:
        doc.ticker = ticker
        doc.form = form
        doc.filing_date = filing_date
        doc.source_url = source_url
        doc.markdown = markdown
        # Delete prior chunks to replace with fresh ones
        session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
    else:
        doc = SourceDocument(
            id=uuid.uuid4(),
            ticker=ticker,
            form=form,
            filing_date=filing_date,
            accession_number=accession_number,
            source_url=source_url,
            markdown=markdown,
        )
        session.add(doc)

    session.flush()
    return doc


def insert_document_chunks(
    session: Session,
    document_id: uuid.UUID,
    chunks: list[dict],
) -> int:
    """Bulk insert document chunks into document_chunks table."""
    chunk_objs = [
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=document_id,
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            embedding=chunk.get("embedding"),
        )
        for chunk in chunks
    ]
    session.add_all(chunk_objs)
    session.flush()
    return len(chunk_objs)


def count_documents_and_chunks(session: Session) -> dict[str, int]:
    """Return total counts of source documents and document chunks."""
    doc_count = session.execute(
        select(func.count(SourceDocument.id))
    ).scalar_one()
    chunk_count = session.execute(
        select(func.count(DocumentChunk.id))
    ).scalar_one()
    return {
        "source_documents": doc_count,
        "document_chunks": chunk_count,
    }
