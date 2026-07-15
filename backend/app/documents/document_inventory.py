"""Deterministic document-inventory extraction and persistence (RAG corrective).

Builds one structured fact row per document (authors, organizations, section headings,
table/figure/reference counts, dates, unit-bearing numeric facts) from the deterministic
ingestion outputs — no hosted models — so document-structure questions are answered from
persisted facts instead of semantic chunk search. Best-effort by design: an approximate
count is more useful than forcing a no-answer, and the facts are additive.
"""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.chunk_metadata import extract_metric_tags

_REFERENCE_MARKER = re.compile(r"\[(\d{1,3})\]")
_FIGURE = re.compile(r"\bfig(?:ure)?\.?\s*(\d{1,3})\b", re.IGNORECASE)
_TABLE = re.compile(r"\btable\s*(\d{1,3})\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ORG = re.compile(
    r"\b(?:[A-Z][A-Za-z&.\-]+\s+){0,4}(?:University|Institute|Laboratory|Corporation|Inc\.|Ltd\.|Company|College|Department)\b"
)
# A plausible personal name: two or three capitalized tokens.
_NAME = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z]\.)?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b")


async def build_and_persist_inventory(
    db: AsyncSession,
    *,
    document: Any,
    title: str | None,
    document_type: str | None,
    blocks: list[Any],
    chunks: list[Any],
    page_assessments: list[Any] | None,
) -> None:
    """Extract structured facts and upsert one ``document_inventory`` row for the document."""
    inventory = extract_inventory(
        title=title,
        document_type=document_type,
        page_count=getattr(document, "page_count", None),
        blocks=blocks,
        chunks=chunks,
        page_assessments=page_assessments,
    )
    await db.execute(
        text(
            """
            INSERT INTO document_inventory (
                document_id, title, document_type, page_count,
                authors, author_count, organizations, section_headings,
                table_count, figure_count, reference_count, dates, numeric_facts
            )
            VALUES (
                :document_id, :title, :document_type, :page_count,
                :authors, :author_count, :organizations, :section_headings,
                :table_count, :figure_count, :reference_count, :dates,
                CAST(:numeric_facts AS jsonb)
            )
            ON CONFLICT (document_id) DO UPDATE SET
                title = EXCLUDED.title,
                document_type = EXCLUDED.document_type,
                page_count = EXCLUDED.page_count,
                authors = EXCLUDED.authors,
                author_count = EXCLUDED.author_count,
                organizations = EXCLUDED.organizations,
                section_headings = EXCLUDED.section_headings,
                table_count = EXCLUDED.table_count,
                figure_count = EXCLUDED.figure_count,
                reference_count = EXCLUDED.reference_count,
                dates = EXCLUDED.dates,
                numeric_facts = EXCLUDED.numeric_facts
            """
        ),
        {
            "document_id": document.id,
            "title": inventory["title"],
            "document_type": inventory["document_type"],
            "page_count": inventory["page_count"],
            "authors": inventory["authors"],
            "author_count": inventory["author_count"],
            "organizations": inventory["organizations"],
            "section_headings": inventory["section_headings"],
            "table_count": inventory["table_count"],
            "figure_count": inventory["figure_count"],
            "reference_count": inventory["reference_count"],
            "dates": inventory["dates"],
            "numeric_facts": json.dumps(inventory["numeric_facts"]),
        },
    )


def extract_inventory(
    *,
    title: str | None,
    document_type: str | None,
    page_count: int | None,
    blocks: list[Any],
    chunks: list[Any],
    page_assessments: list[Any] | None,
) -> dict[str, Any]:
    """Pure deterministic fact extraction (no DB), so it is unit-testable in isolation."""
    section_headings = _dedupe([b.content for b in blocks if getattr(b, "block_type", "") == "heading"])[:60]

    # Scan both the parsed blocks and the persisted chunks, so counts/dates are consistent
    # with what retrieval can actually cite.
    full_text = "\n".join(
        [getattr(b, "content", "") for b in blocks] + [getattr(c, "content", "") for c in chunks]
    )
    first_page_text = "\n".join(
        getattr(b, "content", "") for b in blocks if getattr(b, "page_number", None) in (1, None)
    )

    table_count = _count_tables(blocks, page_assessments, full_text)
    figure_count = _count_figures(page_assessments, full_text)
    reference_count = _count_references(full_text)
    organizations = _dedupe(_ORG.findall(full_text))[:20]
    authors = _extract_authors(first_page_text, organizations)
    dates = _dedupe(_YEAR.findall(full_text))[:30]
    numeric_facts = _collect_numeric_facts(chunks)

    return {
        "title": title,
        "document_type": document_type,
        "page_count": page_count,
        "authors": authors,
        "author_count": len(authors),
        "organizations": organizations,
        "section_headings": section_headings,
        "table_count": table_count,
        "figure_count": figure_count,
        "reference_count": reference_count,
        "dates": dates,
        "numeric_facts": numeric_facts,
    }


def _count_tables(blocks: list[Any], page_assessments: list[Any] | None, full_text: str) -> int:
    from_blocks = sum(1 for b in blocks if getattr(b, "block_type", "") == "table")
    if from_blocks:
        return from_blocks
    if page_assessments:
        by_page = sum(1 for p in page_assessments if getattr(p, "has_table", False))
        if by_page:
            return by_page
    numbered = {int(n) for n in _TABLE.findall(full_text)}
    return len(numbered)


def _count_figures(page_assessments: list[Any] | None, full_text: str) -> int:
    if page_assessments:
        by_page = sum(1 for p in page_assessments if getattr(p, "has_figure", False))
        if by_page:
            return by_page
    numbered = {int(n) for n in _FIGURE.findall(full_text)}
    return len(numbered)


def _count_references(full_text: str) -> int:
    markers = {int(n) for n in _REFERENCE_MARKER.findall(full_text)}
    return max(markers) if markers else 0


def _extract_authors(first_page_text: str, organizations: list[str]) -> list[str]:
    """Best-effort author names from the first page, above the abstract, excluding orgs."""
    head = first_page_text.split("abstract", 1)[0][:1200] if first_page_text else ""
    org_words = {w.lower() for org in organizations for w in org.split()}
    authors: list[str] = []
    for candidate in _NAME.findall(head):
        tokens = candidate.split()
        if any(tok.lower() in org_words for tok in tokens):
            continue
        if candidate not in authors:
            authors.append(candidate)
        if len(authors) >= 25:
            break
    return authors


def _collect_numeric_facts(chunks: list[Any]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    seen: set[tuple[str, Any]] = set()
    for chunk in chunks:
        content = getattr(chunk, "content", "") or ""
        page = getattr(chunk, "page_number", None)
        for metric in extract_metric_tags(content):
            key = (metric, page)
            if key in seen:
                continue
            seen.add(key)
            facts.append({"value": metric, "page": page, "context": _context_for(content, metric)})
            if len(facts) >= 200:
                return facts
    return facts


def _context_for(content: str, metric: str, width: int = 80) -> str:
    lowered = content.lower()
    idx = lowered.find(metric.lower())
    if idx < 0:
        return ""
    start = max(0, idx - width)
    end = min(len(content), idx + len(metric) + width)
    return " ".join(content[start:end].split())


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        v = " ".join((value or "").split())
        if v and v not in out:
            out.append(v)
    return out
