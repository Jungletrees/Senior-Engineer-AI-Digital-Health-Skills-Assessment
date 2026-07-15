"""Unit tests for deterministic document-inventory extraction (no DB, no network)."""

from __future__ import annotations

from app.documents.chunking import PreparedChunk, StructuredBlock
from app.documents.document_inventory import extract_inventory


def _chunk(content: str, page: int) -> PreparedChunk:
    return PreparedChunk(
        chunk_index=0,
        content=content,
        content_hash="x" * 64,
        section_path=None,
        page_number=page,
        token_count=len(content.split()),
    )


def test_extract_inventory_counts_and_facts() -> None:
    blocks = [
        StructuredBlock("1 Introduction", 1, "heading", "1 Introduction"),
        StructuredBlock("Jane Doe, Stanford University", 1, "paragraph", None),
        StructuredBlock("Table 1 shows results. Table 2 lists operations.", 2, "paragraph", None),
        StructuredBlock("| op | desc |\n| --- | --- |", 2, "table", None),
        StructuredBlock("Figure 1 and Figure 2 illustrate the pipeline.", 3, "paragraph", None),
        StructuredBlock("References [1] A. [2] B. [3] C.", 4, "paragraph", None),
    ]
    chunks = [
        _chunk("The system cut emissions ~70% by 2022.", 1),
        _chunk("It processed 9 pre-trained models.", 2),
    ]
    inv = extract_inventory(
        title="LayoutParser",
        document_type="academic_paper",
        page_count=4,
        blocks=blocks,
        chunks=chunks,
        page_assessments=None,
    )
    assert inv["title"] == "LayoutParser"
    assert inv["page_count"] == 4
    assert inv["table_count"] == 1  # one real table block
    assert inv["figure_count"] == 2  # Figure 1 + Figure 2
    assert inv["reference_count"] == 3  # highest [n] marker
    assert "1 Introduction" in inv["section_headings"]
    assert any("Stanford University" in o for o in inv["organizations"])
    assert "2022" in inv["dates"]
    # numeric facts carry the page they were found on
    values = {f["value"] for f in inv["numeric_facts"]}
    assert any("70%" in v or "%" in v for v in values)
    pages = {f["page"] for f in inv["numeric_facts"]}
    assert 1 in pages


def test_extract_inventory_handles_empty_document() -> None:
    inv = extract_inventory(
        title=None, document_type="unknown", page_count=0, blocks=[], chunks=[], page_assessments=None
    )
    assert inv["author_count"] == 0
    assert inv["table_count"] == 0
    assert inv["numeric_facts"] == []
