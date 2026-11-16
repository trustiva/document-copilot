from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import GroundingValidator
from app.retrieval.queries import RetrievedPassage


def _make_sample_passage(
    chunk_id: uuid.UUID,
    content: str = "In fiscal 2026, iPhone net sales increased 21% compared to 2025.",
    ticker: str = "AAPL",
) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        document_id=uuid.uuid4(),
        chunk_index=47,
        content=content,
        ticker=ticker,
        form="10-K",
        filing_date=date(2026, 11, 3),
        accession_number="0000320193-26-000026",
        source_url="https://sec.gov",
        score=0.95,
        rank=1,
        search_method="hybrid",
    )


def test_grounding_valid_answer_passes() -> None:
    chunk_id = uuid.uuid4()
    passage = _make_sample_passage(chunk_id)
    validator = GroundingValidator()

    answer = GroundedAnswer(
        answer="Apple's iPhone net sales increased 21% in fiscal 2026.",
        citations=[Citation(chunk_id=chunk_id, quote="iPhone net sales increased 21%")],
        has_sufficient_evidence=True,
    )

    result = validator.validate(answer, [passage])
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.grounded_answer.cited_passages) == 1
    assert result.grounded_answer.cited_passages[0].chunk_id == chunk_id
    assert result.grounded_answer.cited_passages[0].ticker == "AAPL"


def test_grounding_rejects_hallucinated_chunk_id() -> None:
    valid_id = uuid.uuid4()
    hallucinated_id = uuid.uuid4()
    passage = _make_sample_passage(valid_id)
    validator = GroundingValidator()

    answer = GroundedAnswer(
        answer="Fabricated fact citing an unretrieved chunk.",
        citations=[Citation(chunk_id=hallucinated_id)],
        has_sufficient_evidence=True,
    )

    result = validator.validate(answer, [passage])
    assert result.is_valid is False
    assert any("unretrieved or hallucinated" in err for err in result.errors)


def test_grounding_rejects_sufficient_evidence_without_citations() -> None:
    passage = _make_sample_passage(uuid.uuid4())
    validator = GroundingValidator()

    answer = GroundedAnswer(
        answer="I make a bold claim without citing anything.",
        citations=[],
        has_sufficient_evidence=True,
    )

    result = validator.validate(answer, [passage])
    assert result.is_valid is False
    assert any("zero source citations" in err for err in result.errors)


def test_grounding_allows_insufficient_evidence_refusal() -> None:
    passage = _make_sample_passage(uuid.uuid4())
    validator = GroundingValidator()

    answer = GroundedAnswer(
        answer="The corpus does not contain information about future product roadmaps beyond fiscal 2026.",
        citations=[],
        has_sufficient_evidence=False,
    )

    result = validator.validate(answer, [passage])
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.grounded_answer.has_sufficient_evidence is False


def test_grounding_quote_verification_strict() -> None:
    chunk_id = uuid.uuid4()
    passage = _make_sample_passage(chunk_id, content="iPhone net sales reached $254 billion.")
    validator = GroundingValidator(verify_quotes=True, strict_quote_matching=True)

    # Fabricated quote not in content
    answer = GroundedAnswer(
        answer="Apple reported massive numbers.",
        citations=[Citation(chunk_id=chunk_id, quote="Services profit exploded by 500%")],
        has_sufficient_evidence=True,
    )

    result = validator.validate(answer, [passage])
    assert result.is_valid is False
    assert any("not found in chunk" in err for err in result.errors)


def test_enforce_or_fallback_replaces_hallucinated_answer() -> None:
    passage = _make_sample_passage(uuid.uuid4())
    validator = GroundingValidator()

    bad_answer = GroundedAnswer(
        answer="NVIDIA expects AI revenue to 100x next quarter according to confidential leaks.",
        citations=[Citation(chunk_id=uuid.uuid4())],  # Hallucinated ID
        has_sufficient_evidence=True,
    )

    enforced = validator.enforce_or_fallback(bad_answer, [passage])
    assert enforced.has_sufficient_evidence is False
    assert len(enforced.citations) == 0
    assert len(enforced.cited_passages) == 0
    assert "cannot answer this question with verified citations" in enforced.answer
