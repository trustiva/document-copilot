from __future__ import annotations

import pytest

from app.database.session import SessionLocal
from app.evals.benchmark_questions import BENCHMARK_QUESTIONS
from app.evals.evaluator import evaluate_question, run_all_evaluations
from app.grounding.validator import GroundingValidator
from app.retrieval.retriever import DocumentRetriever


def test_benchmark_questions_defined() -> None:
    assert len(BENCHMARK_QUESTIONS) == 10
    ids = [q.id for q in BENCHMARK_QUESTIONS]
    assert ids == list(range(1, 11))
    # Question 10 must be the refusal / non-hallucination boundary test
    assert BENCHMARK_QUESTIONS[9].is_refusal_test is True


@pytest.mark.integration
def test_all_10_benchmark_questions_pass() -> None:
    """Execute all 10 Driftwood Capital benchmark questions against the live corpus."""
    with SessionLocal() as session:
        report = run_all_evaluations(session=session)

        assert report["total_questions"] == 10
        assert report["passed"] == 10, f"Failed questions: {[r.title for r in report['results'] if not r.overall_passed]}"
        assert report["pass_rate_pct"] == 100.0
        assert report["retrieval_success_rate_pct"] == 100.0
        assert report["grounding_success_rate_pct"] == 100.0
