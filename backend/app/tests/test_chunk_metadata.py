"""Unit tests for deterministic chunk metadata generation (no DB, no network)."""

from __future__ import annotations

from app.documents.chunk_metadata import (
    build_chunk_metadata,
    classify_content_kind,
    extract_entity_tags,
    extract_metric_tags,
    extract_theme_tags,
    infer_document_type,
)


def test_content_kind_table_and_sparse_visual() -> None:
    assert classify_content_kind("| a | b |\n| --- | --- |", "table") == "table"
    assert classify_content_kind("70% renewable", "paragraph", low_yield_page=True) == "sparse_visual_page"


def test_content_kind_bibliography_and_author_block() -> None:
    biblio = "References [1] A. Author. [2] B. Writer. [3] C. Scholar."
    assert classify_content_kind(biblio, "paragraph") == "bibliography"
    author = "Jane Doe, Stanford University, jane@stanford.edu"
    assert classify_content_kind(author, "paragraph") == "author_block"


def test_content_kind_defaults_to_prose() -> None:
    assert classify_content_kind("The treatment protocol is described below.", "paragraph") == "prose"


def test_entity_tags_detect_known_corpus_entities() -> None:
    tags = extract_entity_tags("LayoutParser builds on Detectron2 and PubLayNet.")
    assert "LayoutParser" in tags and "Detectron2" in tags and "PubLayNet" in tags


def test_theme_tags() -> None:
    assert "emissions" in extract_theme_tags("carbon intensity of 2.5 kg CO2e/boe")
    assert "document_ai" in extract_theme_tags("a layout detection toolkit using OCR")


def test_metric_tags_capture_units_percentages_years_counts() -> None:
    tags = extract_metric_tags("It emitted 2.5 kg CO2e/boe, cut ~70% by 2022 across 9 pre-trained models.")
    joined = " | ".join(tags)
    assert "%" in joined
    assert "2022" in tags
    assert any("co2e/boe" in t for t in tags)
    assert any("pre-trained models" in t or "9 pre-trained models" in t for t in tags)


def test_build_chunk_metadata_shape_and_enriched_text() -> None:
    meta = build_chunk_metadata(
        title="LayoutParser",
        document_type="academic_paper",
        page_number=5,
        section_path="3 Layout Detection Models",
        content="LayoutParser ships 9 pre-trained models across 5 datasets.",
        block_type="paragraph",
    )
    assert meta["content_kind"] == "prose"
    assert "LayoutParser" in meta["entity_tags"]
    assert set(meta.keys()) == {"content_kind", "theme_tags", "entity_tags", "metric_tags", "metadata"}
    retrieval_text = meta["metadata"]["retrieval_text"]
    assert "document_title: LayoutParser" in retrieval_text
    assert "page: 5" in retrieval_text
    assert "content_kind: prose" in retrieval_text


def test_infer_document_type() -> None:
    assert infer_document_type("2_layout-parser-paper.pdf") == "academic_paper"
    assert infer_document_type("4_chevron-sustainability-page.pdf") == "corporate_report"
    assert infer_document_type("3_loremipsum.pdf") == "placeholder"
    assert infer_document_type("random.pdf") == "unknown"
