from __future__ import annotations

import uuid
from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: uuid.UUID
    quote: str | None = None
    explanation: str | None = None


class SourcePassage(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    ticker: str
    form: str
    filing_date: str
    accession_number: str
    source_url: str
    content: str
    score: float = 0.0


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    cited_passages: list[SourcePassage] = Field(default_factory=list)
    has_sufficient_evidence: bool = True
