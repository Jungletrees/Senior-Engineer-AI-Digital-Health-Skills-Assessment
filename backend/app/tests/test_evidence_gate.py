"""Unit tests for the evidence-sufficiency gate (pure, no database)."""

from __future__ import annotations

from uuid import uuid4

from app.chat.evidence_gate import post_retrieval_decision, pre_retrieval_decision
from app.retrieval.models import RetrievalCandidate
from app.retrieval.query_analysis import analyze_query


def _candidate(content: str) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_filename="source.pdf",
        document_status="indexed",
        content=content,
        page_number=1,
    )


def test_pre_retrieval_refuses_external_current_fact() -> None:
    decision = pre_retrieval_decision(analyze_query("What is the boiling point of water?"))
    assert decision.refused is True
    assert decision.reason == "external_current_fact"


def test_pre_retrieval_allows_in_corpus_question() -> None:
    decision = pre_retrieval_decision(analyze_query("What datasets does LayoutParser use?"))
    assert decision.sufficient is True
    assert decision.reason is None


def test_post_retrieval_numeric_question_with_number_is_sufficient() -> None:
    analysis = analyze_query("How many models are in the model zoo?")
    decision = post_retrieval_decision(analysis, [_candidate("The zoo ships 9 pre-trained models.")])
    assert decision.sufficient is True


def test_post_retrieval_numeric_question_without_any_number_refuses() -> None:
    analysis = analyze_query("How many models are in the model zoo?")
    decision = post_retrieval_decision(
        analysis, [_candidate("The toolkit provides a unified interface for layout analysis.")]
    )
    assert decision.refused is True
    assert decision.reason == "missing_numeric_evidence"


def test_post_retrieval_non_numeric_question_is_not_refused_without_numbers() -> None:
    analysis = analyze_query("What datasets does LayoutParser use?")
    decision = post_retrieval_decision(
        analysis, [_candidate("It supports PubLayNet and other datasets.")]
    )
    assert decision.sufficient is True


def test_post_retrieval_empty_chunks_is_low_confidence() -> None:
    analysis = analyze_query("How many models are in the model zoo?")
    decision = post_retrieval_decision(analysis, [])
    assert decision.refused is True
    assert decision.reason == "low_evidence_confidence"
