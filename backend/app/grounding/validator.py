from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Sequence

import structlog

from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage
from app.retrieval.queries import RetrievedPassage

logger = structlog.get_logger(__name__)


class GroundingValidationError(Exception):
    """Raised when an answer fails the grounding trust contract."""

    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors


@dataclass
class ValidationResult:
    is_valid: bool
    grounded_answer: GroundedAnswer
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class GroundingValidator:
    """Enforces Driftwood Capital's trust contract: every answer is grounded in retrieved passages."""

    def __init__(
        self,
        *,
        verify_quotes: bool = True,
        strict_quote_matching: bool = False,
    ) -> None:
        self.verify_quotes = verify_quotes
        self.strict_quote_matching = strict_quote_matching

    def validate(
        self,
        answer: GroundedAnswer,
        retrieved_passages: Sequence[RetrievedPassage],
    ) -> ValidationResult:
        """Validate that all citations in the answer map to retrieved passages,

        quotes exist in cited text, and evidence rules are respected.
        """
        errors: list[str] = []
        warnings: list[str] = []

        retrieved_map: dict[uuid.UUID, RetrievedPassage] = {
            p.chunk_id: p for p in retrieved_passages
        }

        # Rule 1: Check evidence vs citation requirement
        if answer.has_sufficient_evidence and not answer.citations:
            errors.append(
                "Answer claims sufficient evidence but contains zero source citations."
            )

        verified_citations: list[Citation] = []
        resolved_passages: list[SourcePassage] = []
        seen_chunks: set[uuid.UUID] = set()

        # Rule 2: Verify each citation against retrieved passages
        for citation in answer.citations:
            chunk_id = citation.chunk_id

            if chunk_id not in retrieved_map:
                errors.append(
                    f"Citation references unretrieved or hallucinated chunk_id: {chunk_id}"
                )
                continue

            passage = retrieved_map[chunk_id]

            # Rule 3: Quote verification if quote provided
            if citation.quote and self.verify_quotes:
                quote_valid = self._check_quote(citation.quote, passage.content)
                if not quote_valid:
                    msg = (
                        f"Citation quote '{citation.quote[:60]}...' was not found in "
                        f"chunk {chunk_id} ({passage.ticker} {passage.form})"
                    )
                    if self.strict_quote_matching:
                        errors.append(msg)
                    else:
                        warnings.append(msg)

            verified_citations.append(citation)

            if chunk_id not in seen_chunks:
                seen_chunks.add(chunk_id)
                resolved_passages.append(
                    SourcePassage(
                        chunk_id=passage.chunk_id,
                        document_id=passage.document_id,
                        chunk_index=passage.chunk_index,
                        ticker=passage.ticker,
                        form=passage.form,
                        filing_date=passage.filing_date.isoformat(),
                        accession_number=passage.accession_number,
                        source_url=passage.source_url,
                        content=passage.content,
                        score=passage.score,
                    )
                )

        # Build clean GroundedAnswer
        is_valid = len(errors) == 0
        validated_answer = GroundedAnswer(
            answer=answer.answer,
            citations=verified_citations,
            cited_passages=resolved_passages,
            has_sufficient_evidence=answer.has_sufficient_evidence,
        )

        return ValidationResult(
            is_valid=is_valid,
            grounded_answer=validated_answer,
            errors=errors,
            warnings=warnings,
        )

    def enforce_or_fallback(
        self,
        answer: GroundedAnswer,
        retrieved_passages: Sequence[RetrievedPassage],
    ) -> GroundedAnswer:
        """Validate answer; if invalid, return a controlled, transparent fallback refusal

        rather than an unsupported or hallucinated claim.
        """
        result = self.validate(answer, retrieved_passages)
        if result.is_valid:
            return result.grounded_answer

        logger.warning(
            "Grounding validation failed; returning controlled refusal.",
            errors=result.errors,
        )
        return GroundedAnswer(
            answer=(
                "I cannot answer this question with verified citations from the retrieved SEC filings. "
                "The available filings do not contain sufficient verified evidence to support the claim without risk of hallucination."
            ),
            citations=[],
            cited_passages=[],
            has_sufficient_evidence=False,
        )

    @staticmethod
    def _check_quote(quote: str, content: str) -> bool:
        """Normalized substring check for citation quote."""
        norm_quote = re.sub(r"\s+", " ", quote).strip().lower()
        norm_content = re.sub(r"\s+", " ", content).strip().lower()
        norm_quote_alphanum = re.sub(r"[^\w\s]", "", norm_quote)
        norm_content_alphanum = re.sub(r"[^\w\s]", "", norm_content)
        return norm_quote in norm_content or norm_quote_alphanum in norm_content_alphanum
