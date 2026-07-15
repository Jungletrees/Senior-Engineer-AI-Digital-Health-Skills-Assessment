"""Deterministic unit tests for the query analyzer.

No database, no network: analyze_query is a pure function, and these tests pin both the
positive classifications and the false-positive guards that keep it from refusing a
legitimate in-corpus question.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.retrieval.query_analysis import (
    QueryIntent,
    analyze_query,
    resolve_document_ids,
)


@pytest.mark.parametrize(
    "query",
    [
        "What is the current PyPI download count of LayoutParser?",
        "How many downloads does LayoutParser get per month?",
        "What is the boiling point of water?",
        "What is today's date?",
        "What is the capital of France?",
        "What is the latest version of Detectron2 right now?",
    ],
)
def test_external_current_facts_are_out_of_scope(query: str) -> None:
    analysis = analyze_query(query)
    assert analysis.intent is QueryIntent.OUT_OF_SCOPE_CURRENT_FACT
    assert analysis.is_out_of_scope is True


@pytest.mark.parametrize(
    "query",
    [
        # In-corpus questions that share a surface word ("recent", "intensity") with an
        # external marker must NOT be refused as out-of-scope.
        "What carbon intensity does Chevron report on this page?",
        "What datasets does LayoutParser support?",
        "How much oral rehydration solution should a child be given each hour?",
        "What are the main sections of the LayoutParser paper?",
        "Summarise the most recent results described in the paper.",
    ],
)
def test_in_corpus_questions_are_not_out_of_scope(query: str) -> None:
    assert analyze_query(query).intent is not QueryIntent.OUT_OF_SCOPE_CURRENT_FACT


def test_numeric_fact_requires_numeric_evidence() -> None:
    analysis = analyze_query("How many pre-trained models are in the model zoo?")
    assert analysis.intent is QueryIntent.NUMERIC_FACT
    assert analysis.requires_numeric_evidence is True


def test_document_inventory_intent() -> None:
    for query in (
        "How many authors wrote the LayoutParser paper?",
        "How many references are in Document 3?",
        "How many pages does the paper have?",
    ):
        assert analyze_query(query).intent is QueryIntent.DOCUMENT_INVENTORY


def test_table_or_figure_intent() -> None:
    analysis = analyze_query("What operations are listed in Table 2?")
    assert analysis.intent is QueryIntent.TABLE_OR_FIGURE


def test_all_documents_intent_and_alias() -> None:
    analysis = analyze_query("What theme is common across all three documents?")
    assert analysis.intent is QueryIntent.ALL_DOCUMENTS
    assert "all_documents" in analysis.document_aliases


def test_multi_document_comparison_from_two_aliases() -> None:
    analysis = analyze_query("Compare Document 1 and Document 3.")
    assert analysis.intent is QueryIntent.MULTI_DOCUMENT_COMPARISON
    assert "document_1" in analysis.document_aliases
    assert "document_3" in analysis.document_aliases


def test_entity_and_alias_detection() -> None:
    analysis = analyze_query("What does the Chevron page say about LayoutParser?")
    assert "Chevron" in analysis.required_entities
    assert "LayoutParser" in analysis.required_entities
    assert "chevron" in analysis.document_aliases
    assert "layoutparser" in analysis.document_aliases


def test_matched_signals_are_populated() -> None:
    analysis = analyze_query("What is the boiling point of water?")
    assert any(signal.startswith("external:") for signal in analysis.matched_signals)


def test_analyze_query_never_raises_on_odd_input() -> None:
    for query in ("", "   ", "?!?", "12345"):
        assert analyze_query(query).intent in set(QueryIntent)


def test_resolve_document_ids_by_ordinal_and_name() -> None:
    doc1, doc2, doc3 = uuid4(), uuid4(), uuid4()
    documents = [
        (doc1, "4_visual-sparse-text_chevron-sustainability-page.pdf"),
        (doc2, "3_unstructured-no-headings_loremipsum.pdf"),
        (doc3, "2_structured-headings-titles_layout-parser-paper.pdf"),
    ]
    assert resolve_document_ids(["document_1"], documents) == [doc1]
    assert resolve_document_ids(["chevron"], documents) == [doc1]
    assert resolve_document_ids(["layoutparser"], documents) == [doc3]
    assert resolve_document_ids(["all_documents"], documents) == [doc1, doc2, doc3]
    # Deduplicated: alias + ordinal pointing at the same document yields one id.
    assert resolve_document_ids(["document_1", "chevron"], documents) == [doc1]
    assert resolve_document_ids([], documents) == []
