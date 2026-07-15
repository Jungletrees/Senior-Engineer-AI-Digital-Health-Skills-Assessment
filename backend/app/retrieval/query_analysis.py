"""Deterministic query analysis for retrieval precision and evidence gating.

This module classifies a user question *before* retrieval so downstream code can
route it correctly: run per-document retrieval for a comparison, prefer inventory
metadata for a structural question, or refuse fast when the question asks for an
external/current fact the corpus cannot contain.

Design constraints (see agents-skills/RAG-retrieval-precision-engineer-SKILL.md):

- Pure, typed, and deterministic. No database access, no hosted-model calls, so it
  is fully unit-testable and safe inside deterministic tests.
- Conservative by construction. A false ``out_of_scope_current_fact`` would refuse a
  legitimate in-corpus question, which is worse than missing one, so the external-fact
  patterns are high-precision and narrow. Anything not confidently external falls
  through to ordinary retrieval and the existing generation-time refusal.

Resolving a detected alias (``"document_1"``, ``"chevron"``) to a concrete document id
needs the corpus, so it lives in :func:`resolve_document_ids`, kept separate from the
pure classifier.
"""

from __future__ import annotations

import re
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class QueryIntent(str, Enum):
    """The retrieval-relevant shape of a question."""

    SINGLE_FACT = "single_fact"
    NUMERIC_FACT = "numeric_fact"
    MULTI_DOCUMENT_COMPARISON = "multi_document_comparison"
    ALL_DOCUMENTS = "all_documents"
    TABLE_OR_FIGURE = "table_or_figure"
    DOCUMENT_INVENTORY = "document_inventory"
    OUT_OF_SCOPE_CURRENT_FACT = "out_of_scope_current_fact"
    ENTITY_PRESENT_ATTRIBUTE_ABSENT = "entity_present_attribute_absent"
    UNKNOWN = "unknown"


class QueryAnalysis(BaseModel):
    """Typed classification of a single user question."""

    intent: QueryIntent
    document_aliases: list[str] = Field(default_factory=list)
    required_entities: list[str] = Field(default_factory=list)
    requested_attributes: list[str] = Field(default_factory=list)
    requires_numeric_evidence: bool = False
    requires_page_citation: bool = True
    # Human-readable markers that drove the classification. Persisted to the trace so a
    # "why did this refuse / why per-document?" question is answerable after the fact.
    matched_signals: list[str] = Field(default_factory=list)

    @property
    def is_out_of_scope(self) -> bool:
        return self.intent is QueryIntent.OUT_OF_SCOPE_CURRENT_FACT

    @property
    def is_multi_document(self) -> bool:
        return self.intent in (
            QueryIntent.MULTI_DOCUMENT_COMPARISON,
            QueryIntent.ALL_DOCUMENTS,
        )


# --- Corpus vocabulary -------------------------------------------------------

# Known entities in the assessment corpus. Used both for entity extraction and to keep
# the external-fact classifier from firing on genuine questions about these subjects.
_KNOWN_ENTITIES: dict[str, tuple[str, ...]] = {
    "LayoutParser": ("layoutparser", "layout parser"),
    "PubLayNet": ("publaynet",),
    "Detectron2": ("detectron2", "detectron 2"),
    "Chevron": ("chevron",),
    "Lorem Ipsum": ("lorem ipsum",),
}

# Alias phrases -> canonical alias label. Ordered so that "all documents" wins over a
# bare "document" reference.
_ALL_DOCUMENT_PHRASES: tuple[str, ...] = (
    "all three documents",
    "all 3 documents",
    "all three docs",
    "all the documents",
    "all documents",
    "all uploaded documents",
    "across the uploaded documents",
    "across the documents",
    "across all documents",
    "each document",
    "every document",
    "each of the documents",
    "all the uploaded",
)

_DOCUMENT_ALIAS_PATTERNS: tuple[tuple[str, str], ...] = (
    ("document_1", r"\b(?:document|doc)\s*(?:1|one)\b"),
    ("document_1", r"\bthe first document\b"),
    ("document_2", r"\b(?:document|doc)\s*(?:2|two)\b"),
    ("document_2", r"\bthe second document\b"),
    ("document_3", r"\b(?:document|doc)\s*(?:3|three)\b"),
    ("document_3", r"\bthe third document\b"),
    ("chevron", r"\bchevron\b"),
    ("lorem_ipsum", r"\blorem ipsum\b"),
    ("layoutparser", r"\blayout\s*parser\b"),
)

# --- Intent signal vocabularies ---------------------------------------------

# High-precision external/current-fact markers. These almost never appear in a genuine
# question about a static sustainability page, a Lorem Ipsum filler, or the LayoutParser
# paper, and each names information a fixed PDF corpus structurally cannot hold.
_EXTERNAL_FACT_MARKERS: tuple[str, ...] = (
    "pypi",
    "download count",
    "number of downloads",
    "how many downloads",
    "downloads per",
    "github stars",
    "how many stars",
    "stock price",
    "share price",
    "market cap",
    "exchange rate",
    "current weather",
    "today's weather",
    "population of",
    "who is the president",
    "who is the current",
    "what year is it",
    "what is today's date",
    "what's today's date",
    "current date",
    "boiling point",
    "melting point",
    "freezing point",
    "speed of light",
    "atomic number",
    "chemical symbol",
    "capital of",
    "latest version",
    "current version",
    "most recent version",
    "as of today",
    "as of now",
    "right now on",
    "up to date figure",
)

# Weak time markers only count toward external-fact when paired with something that
# reaches outside the corpus (a version/release/price/count noun). Alone, "recent" or
# "current" can legitimately qualify an in-corpus question and must not force a refusal.
_TIME_MARKERS: tuple[str, ...] = (
    "currently",
    "right now",
    "these days",
    "nowadays",
    "at the moment",
    "so far in 2026",
    "in 2026",
    "this year",
    "this month",
    "this week",
)
_EXTERNAL_CONTEXT_NOUNS: tuple[str, ...] = (
    "price",
    "downloads",
    "release",
    "version",
    "news",
    "count",
    "ranking",
    "trending",
    "market",
    "available",
)

_INVENTORY_MARKERS: tuple[str, ...] = (
    "how many documents",
    "number of documents",
    "how many pages",
    "page count",
    "number of pages",
    "how many authors",
    "number of authors",
    "who wrote",
    "who authored",
    "authors of",
    "author of",
    "affiliation",
    "affiliations",
    "institution",
    "institutions",
    "how many references",
    "number of references",
    "how many citations",
    "bibliography",
    "how many sections",
    "number of sections",
    "list the documents",
    "which documents",
    "which document contains",
    "what documents",
)

_TABLE_FIGURE_MARKERS: tuple[str, ...] = (
    "table",
    "tables",
    "figure",
    "figures",
    "chart",
    "charts",
    "diagram",
    "diagrams",
)

_COMPARISON_MARKERS: tuple[str, ...] = (
    "compare",
    "comparison",
    "difference between",
    "differences between",
    "versus",
    " vs ",
    "contrast",
    "in common",
    "common theme",
    "shared theme",
    "both documents",
    "similarities",
    "how do they differ",
)

_NUMERIC_MARKERS: tuple[str, ...] = (
    "how many",
    "how much",
    "what percentage",
    "percentage",
    "percent",
    "what year",
    "which year",
    "what rate",
    "intensity",
    "how long",
    "how old",
    "count of",
    "number of",
    "total number",
)

# Attribute nouns we surface for tracing / evidence-gate hints.
_ATTRIBUTE_KEYWORDS: tuple[str, ...] = (
    "university",
    "college",
    "degree",
    "salary",
    "email",
    "phone",
    "address",
    "birthday",
    "age",
    "author",
    "authors",
    "page",
    "pages",
    "table",
    "figure",
    "reference",
    "references",
    "section",
    "date",
    "year",
    "percentage",
)

_WHITESPACE = re.compile(r"\s+")


def analyze_query(query: str) -> QueryAnalysis:
    """Classify ``query`` deterministically. Never raises on user input."""
    normalized = _normalize(query)
    padded = f" {normalized} "
    signals: list[str] = []

    aliases = _detect_aliases(normalized, signals)
    entities = _detect_entities(normalized, signals)
    attributes = _detect_attributes(padded)
    numeric = _looks_numeric(padded, signals)

    intent = _classify_intent(
        normalized=normalized,
        padded=padded,
        aliases=aliases,
        numeric=numeric,
        signals=signals,
    )

    return QueryAnalysis(
        intent=intent,
        document_aliases=aliases,
        required_entities=entities,
        requested_attributes=attributes,
        requires_numeric_evidence=numeric or intent is QueryIntent.NUMERIC_FACT,
        requires_page_citation=True,
        matched_signals=signals,
    )


def resolve_document_ids(
    aliases: list[str],
    documents: list[tuple[UUID, str]],
) -> list[UUID]:
    """Map detected aliases to document ids.

    ``documents`` is ``[(id, filename), ...]`` in stable upload order. ``document_1`` maps
    to the first uploaded document and so on; a name alias (``chevron``) matches on the
    filename. Kept separate from :func:`analyze_query` so the classifier stays DB-free.
    """
    if not aliases or not documents:
        return []
    resolved: list[UUID] = []

    def _add(doc_id: UUID) -> None:
        if doc_id not in resolved:
            resolved.append(doc_id)

    ordinal = {"document_1": 0, "document_2": 1, "document_3": 2}
    for alias in aliases:
        if alias == "all_documents":
            for doc_id, _ in documents:
                _add(doc_id)
            continue
        if alias in ordinal:
            index = ordinal[alias]
            if index < len(documents):
                _add(documents[index][0])
            continue
        # Name alias: match the token against the filename, ignoring separators so
        # "layoutparser" matches "layout-parser-paper.pdf".
        token = _alphanumeric(alias)
        for doc_id, filename in documents:
            if token and token in _alphanumeric(filename):
                _add(doc_id)
    return resolved


def _alphanumeric(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


# --- internals ---------------------------------------------------------------


def _normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", value or "").strip().lower()


def _detect_aliases(normalized: str, signals: list[str]) -> list[str]:
    aliases: list[str] = []

    def _add(alias: str, signal: str) -> None:
        if alias not in aliases:
            aliases.append(alias)
        if signal not in signals:
            signals.append(signal)

    for phrase in _ALL_DOCUMENT_PHRASES:
        if phrase in normalized:
            _add("all_documents", f"all_documents:{phrase}")
            break

    for alias, pattern in _DOCUMENT_ALIAS_PATTERNS:
        if re.search(pattern, normalized):
            _add(alias, f"alias:{alias}")
    return aliases


def _detect_entities(normalized: str, signals: list[str]) -> list[str]:
    entities: list[str] = []
    for canonical, variants in _KNOWN_ENTITIES.items():
        if any(variant in normalized for variant in variants):
            entities.append(canonical)
            signals.append(f"entity:{canonical}")
    return entities


def _detect_attributes(padded: str) -> list[str]:
    found: list[str] = []
    for keyword in _ATTRIBUTE_KEYWORDS:
        if f" {keyword} " in padded and keyword not in found:
            found.append(keyword)
    return found


def _looks_numeric(padded: str, signals: list[str]) -> bool:
    for marker in _NUMERIC_MARKERS:
        if marker in padded:
            signals.append(f"numeric:{marker}")
            return True
    if "%" in padded:
        signals.append("numeric:%")
        return True
    return False


def _is_external_fact(normalized: str, signals: list[str]) -> bool:
    for marker in _EXTERNAL_FACT_MARKERS:
        if marker in normalized:
            signals.append(f"external:{marker}")
            return True
    # Weak time marker only counts alongside an outside-the-corpus noun.
    time_hit = next((m for m in _TIME_MARKERS if m in normalized), None)
    if time_hit is not None:
        noun_hit = next((n for n in _EXTERNAL_CONTEXT_NOUNS if n in normalized), None)
        if noun_hit is not None:
            signals.append(f"external:{time_hit}+{noun_hit}")
            return True
    return False


def _classify_intent(
    normalized: str,
    padded: str,
    aliases: list[str],
    numeric: bool,
    signals: list[str],
) -> QueryIntent:
    # 1) External/current facts are refused fast and never reach retrieval, so they take
    #    precedence — but only on high-precision markers (see module docstring).
    if _is_external_fact(normalized, signals):
        return QueryIntent.OUT_OF_SCOPE_CURRENT_FACT

    distinct_doc_aliases = {a for a in aliases if a != "all_documents"}

    # 2) Structural / inventory questions want the document inventory, not chunk search.
    if any(marker in normalized for marker in _INVENTORY_MARKERS):
        signals.append("intent:document_inventory")
        return QueryIntent.DOCUMENT_INVENTORY

    # 3) Explicit all-documents scope.
    if "all_documents" in aliases:
        signals.append("intent:all_documents")
        return QueryIntent.ALL_DOCUMENTS

    # 4) Comparison language, or two distinct documents named in one question.
    if any(marker in padded for marker in _COMPARISON_MARKERS) or len(distinct_doc_aliases) >= 2:
        signals.append("intent:multi_document_comparison")
        return QueryIntent.MULTI_DOCUMENT_COMPARISON

    # 5) Table / figure structural lookup.
    if any(f" {marker} " in padded for marker in _TABLE_FIGURE_MARKERS):
        signals.append("intent:table_or_figure")
        return QueryIntent.TABLE_OR_FIGURE

    # 6) Numeric fact.
    if numeric:
        signals.append("intent:numeric_fact")
        return QueryIntent.NUMERIC_FACT

    # 7) A concrete "what/who/which/when/where is ..." is a single fact.
    if re.match(r"^(?:what|who|which|when|where|name|list|does|is|are|how)\b", normalized):
        signals.append("intent:single_fact")
        return QueryIntent.SINGLE_FACT

    return QueryIntent.UNKNOWN
