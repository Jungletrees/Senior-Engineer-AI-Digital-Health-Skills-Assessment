"""Deterministic chunk metadata generation (RAG ingestion-metadata corrective).

Pure, deterministic heuristics that annotate each stored chunk with filterable metadata
so retrieval can select the right candidate bucket (by document, theme, content kind,
entity, or metric) instead of relying on one undifferentiated ANN space. No hosted models,
so this runs inside deterministic tests.

The raw chunk ``content`` is never modified — citations still resolve to truthful source
text. These functions only produce *additional* metadata (content_kind, theme/entity/metric
tags, and a JSONB blob). A metadata-enriched retrieval string is also produced for
observability, but embeddings remain keyed on raw content to preserve embedding-reuse
consistency (see ARCHITECTURE (4).md §18).
"""

from __future__ import annotations

import re

# Corpus + general entities worth tagging. Kept aligned with retrieval/query_analysis.py.
_KNOWN_ENTITIES: dict[str, tuple[str, ...]] = {
    "LayoutParser": ("layoutparser", "layout parser"),
    "PubLayNet": ("publaynet",),
    "Detectron2": ("detectron2", "detectron 2"),
    "Chevron": ("chevron",),
    "Lorem Ipsum": ("lorem ipsum",),
}

# Theme keyword -> theme tag. Deterministic and small; extend as the corpus grows.
_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "document_ai": ("layout", "document image", "ocr", "detectron", "publaynet", "layoutparser"),
    "layout_detection": ("layout detection", "object detection", "bounding box", "region"),
    "sustainability": ("sustainab", "renewable", "climate", "net zero", "net-zero"),
    "emissions": ("carbon", "emission", "co2", "greenhouse", "boe", "intensity"),
    "energy": ("energy", "electricity", "power", "oil", "gas", "offshore"),
    "placeholder_text": ("lorem ipsum", "dolor sit amet", "consectetur"),
}

_REFERENCE_MARKER = re.compile(r"\[\d{1,3}\]")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_AFFILIATION = re.compile(r"\b(?:university|institute|department|laboratory|corporation|inc\.|ltd\.)\b", re.IGNORECASE)
_ACRONYM = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:[A-Z][A-Za-z0-9]*)+\b")  # CamelCase / ALLCAPS-ish

# Metric patterns -> normalized metric tag.
_PERCENT = re.compile(r"~?\s*\d+(?:\.\d+)?\s*%")
_UNIT_VALUE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:kg\s*co2e/boe|co2e/boe|kg|mg|ml|g|l|km|cm|mm|m|tonnes?|tons?|boe|mw|kw|gw|usd|\$)\b",
    re.IGNORECASE,
)
_COUNT_NOUN = re.compile(
    r"\b\d+\s+(?:pre-?trained\s+models?|models?|datasets?|lines?\s+of\s+code|references?|figures?|tables?|authors?|pages?|sections?)\b",
    re.IGNORECASE,
)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

_WHITESPACE = re.compile(r"\s+")


def classify_content_kind(content: str, block_type: str, low_yield_page: bool = False) -> str:
    """Deterministically label the kind of content a chunk holds."""
    if low_yield_page:
        return "sparse_visual_page"
    if block_type == "table":
        return "table"
    lowered = content.lower().strip()
    if lowered.startswith(("references", "bibliography")) or len(_REFERENCE_MARKER.findall(content)) >= 3:
        return "bibliography"
    if (_EMAIL.search(content) or _AFFILIATION.search(content)) and len(content) < 600:
        return "author_block"
    if any(marker in lowered for marker in _THEME_KEYWORDS["placeholder_text"]):
        return "placeholder_text"
    return "prose"


def extract_entity_tags(content: str) -> list[str]:
    lowered = content.lower()
    tags: list[str] = []
    for canonical, variants in _KNOWN_ENTITIES.items():
        if any(variant in lowered for variant in variants) and canonical not in tags:
            tags.append(canonical)
    # A couple of salient CamelCase acronyms not already covered, capped for noise control.
    for match in _ACRONYM.findall(content):
        if match in _KNOWN_ENTITIES:
            continue
        if 3 <= len(match) <= 20 and match not in tags:
            tags.append(match)
        if len(tags) >= 8:
            break
    return tags


def extract_theme_tags(content: str) -> list[str]:
    lowered = content.lower()
    tags: list[str] = []
    for theme, keywords in _THEME_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords) and theme not in tags:
            tags.append(theme)
    return tags


def extract_metric_tags(content: str) -> list[str]:
    """Unit-bearing numbers, percentages, counts, and years, normalized and deduplicated."""
    found: list[str] = []

    def _add(value: str) -> None:
        normalized = _WHITESPACE.sub(" ", value).strip().lower()
        if normalized and normalized not in found:
            found.append(normalized)

    for pattern in (_PERCENT, _UNIT_VALUE, _COUNT_NOUN):
        for match in pattern.findall(content):
            _add(match if isinstance(match, str) else match[0])
    for year in _YEAR.findall(content):
        _add(year)
    return found[:24]


def build_enriched_retrieval_text(
    *,
    title: str | None,
    document_type: str | None,
    page_number: int | None,
    section_path: str | None,
    content_kind: str,
    theme_tags: list[str],
    entity_tags: list[str],
    metric_tags: list[str],
    content: str,
) -> str:
    """Compact, deterministic retrieval string (stored for observability; see module doc)."""
    lines = [
        f"document_title: {title or 'unknown'}",
        f"document_type: {document_type or 'unknown'}",
        f"page: {page_number if page_number is not None else ''}",
        f"section_path: {section_path or ''}",
        f"content_kind: {content_kind}",
        f"themes: {', '.join(theme_tags)}",
        f"entities: {', '.join(entity_tags)}",
        f"metrics: {', '.join(metric_tags)}",
        "",
        content,
    ]
    return "\n".join(lines)


def build_chunk_metadata(
    *,
    title: str | None,
    document_type: str | None,
    page_number: int | None,
    section_path: str | None,
    content: str,
    block_type: str,
    low_yield_page: bool = False,
) -> dict[str, object]:
    """Return (content_kind, theme_tags, entity_tags, metric_tags, metadata) for a chunk."""
    content_kind = classify_content_kind(content, block_type, low_yield_page=low_yield_page)
    theme_tags = extract_theme_tags(content)
    entity_tags = extract_entity_tags(content)
    metric_tags = extract_metric_tags(content)
    retrieval_text = build_enriched_retrieval_text(
        title=title,
        document_type=document_type,
        page_number=page_number,
        section_path=section_path,
        content_kind=content_kind,
        theme_tags=theme_tags,
        entity_tags=entity_tags,
        metric_tags=metric_tags,
        content=content,
    )
    metadata = {
        "title": title,
        "document_type": document_type,
        "page": page_number,
        "section_path": section_path,
        "content_kind": content_kind,
        "themes": theme_tags,
        "entities": entity_tags,
        "metrics": metric_tags,
        "retrieval_text": retrieval_text,
    }
    return {
        "content_kind": content_kind,
        "theme_tags": theme_tags,
        "entity_tags": entity_tags,
        "metric_tags": metric_tags,
        "metadata": metadata,
    }


def infer_document_type(filename: str) -> str:
    """Deterministic coarse document type from the filename."""
    name = filename.lower()
    if any(token in name for token in ("paper", "layout-parser", "layoutparser", "arxiv")):
        return "academic_paper"
    if any(token in name for token in ("chevron", "sustainability", "report", "annual")):
        return "corporate_report"
    if "lorem" in name or "loremipsum" in name:
        return "placeholder"
    return "unknown"
