from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.grounding.validator import GroundingValidator
from app.retrieval.queries import RetrievedPassage
from app.retrieval.retriever import DocumentRetriever


@dataclass
class DocumentAgentDeps:
    """Runtime dependencies injected into the PydanticAI Document Copilot Agent."""

    user_id: str
    thread_id: uuid.UUID
    retriever: DocumentRetriever
    grounding_validator: GroundingValidator
    # Accumulator for all passages retrieved during agent tool calls in this turn
    retrieved_passages: list[RetrievedPassage] = field(default_factory=list)
