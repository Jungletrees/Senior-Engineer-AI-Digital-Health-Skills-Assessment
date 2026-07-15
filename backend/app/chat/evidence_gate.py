"""Evidence-sufficiency gate between retrieval and generation.

See agents-skills/RAG-evidence-reliability-engineer-SKILL.md. The gate decides whether
the corpus can support the requested answer *before* the generation model is called, so
an unsupported question becomes a fast, cheap, schema-stable no-answer instead of a slow
round-trip that either hallucinates or fails.

Two decision points:

- :func:`pre_retrieval_decision` runs on the query analysis alone. An external/current
  fact (``out_of_scope_current_fact``) is refused here, so it never touches retrieval or
  generation — the cheapest possible no-answer.
- :func:`post_retrieval_decision` runs on the retrieved chunks. It is deliberately narrow
  and conservative: a false refusal would deny a legitimate answer, which is worse than a
  missed one, so it only fires on a clearly numeric question whose evidence contains no
  number at all. Every other insufficiency still flows to the existing generation-time
  refusal and the numeric-grounding output filter, which stay in place as defense in depth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.retrieval.models import RetrievalCandidate
from app.retrieval.query_analysis import QueryAnalysis, QueryIntent

# Machine-readable no-answer reasons persisted to the trace (agent_trace_log).
NoAnswerReason = Literal[
    "external_current_fact",
    "attribute_absent",
    "low_evidence_confidence",
    "missing_numeric_evidence",
    "missing_required_document",
    "retrieval_unavailable",
    "provider_unavailable",
]

_DIGIT = re.compile(r"\d")


@dataclass(slots=True, frozen=True)
class EvidenceDecision:
    """Outcome of an evidence-sufficiency check."""

    sufficient: bool
    reason: NoAnswerReason | None = None

    @property
    def refused(self) -> bool:
        return not self.sufficient


def pre_retrieval_decision(analysis: QueryAnalysis) -> EvidenceDecision:
    """Refuse external/current-fact questions before any retrieval or generation."""
    if analysis.intent is QueryIntent.OUT_OF_SCOPE_CURRENT_FACT:
        return EvidenceDecision(sufficient=False, reason="external_current_fact")
    return EvidenceDecision(sufficient=True)


def post_retrieval_decision(
    analysis: QueryAnalysis,
    chunks: list[RetrievalCandidate],
) -> EvidenceDecision:
    """Refuse a numeric question whose retrieved evidence contains no number at all.

    Scoped to ``numeric_fact`` intent (not merely ``requires_numeric_evidence``) so a
    structural "how many tables" question — whose evidence may legitimately hold no digit —
    is never refused here. Broader attribute-absent / low-confidence cases are intentionally
    left to generation-time refusal to avoid false negatives.
    """
    if not chunks:
        # Retrieval returned nothing citable; the empty-context path handles messaging.
        return EvidenceDecision(sufficient=False, reason="low_evidence_confidence")

    if analysis.intent is QueryIntent.NUMERIC_FACT and not _any_numeric_evidence(chunks):
        return EvidenceDecision(sufficient=False, reason="missing_numeric_evidence")

    return EvidenceDecision(sufficient=True)


def _any_numeric_evidence(chunks: list[RetrievalCandidate]) -> bool:
    return any(_DIGIT.search(chunk.content or "") for chunk in chunks)
