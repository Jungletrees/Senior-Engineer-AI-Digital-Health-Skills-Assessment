"""Injectable generation client used by `/chat` and deterministic tests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.agents.orchestrator import GenerationPayload
from app.chainlit_steps import chainlit_step
from app.settings import settings

# The presenter recognizes this wording as a no-answer and returns the canonical
# concise message, so the deterministic client never invents unsupported content.
NO_ANSWER_ANSWER = "I could not find that in the uploaded documents."

MAX_CITED_BLOCKS = 3
MAX_SENTENCE_WORDS = 45

_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from",
        "how", "in", "is", "it", "of", "on", "or", "that", "the", "to", "what", "when",
        "which", "who", "why", "with",
    }
)


@dataclass(slots=True)
class GenerationResult:
    answer: str
    model: str
    token_input: int
    token_output: int
    cost_usd: float


class GenerationClient(Protocol):
    async def generate(self, payload: GenerationPayload, max_tokens: int) -> GenerationResult:
        ...

    async def summarize(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        ...


class DeterministicGenerationClient:
    """Local deterministic fallback that never calls a hosted LLM.

    It obeys the same citation contract as a hosted model: it quotes the
    context sentences that best match the question and marks each one with the
    `[cite:n]` id of the block it came from. It never opens with a document
    name and never emits a number the context does not contain.
    """

    @chainlit_step("generation", "llm")
    async def generate(self, payload: GenerationPayload, max_tokens: int) -> GenerationResult:
        context_text = _payload_text(payload)
        answer = _compose_grounded_answer(payload)
        return GenerationResult(
            answer=answer,
            model=payload.model,
            token_input=_count_tokens(context_text),
            token_output=min(_count_tokens(answer), max_tokens),
            cost_usd=0.0,
        )

    async def summarize(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        text = " ".join(item["content"] for item in messages)
        return " ".join(text.split()[:max_tokens])


def get_generation_client() -> GenerationClient:
    return DeterministicGenerationClient()


def _compose_grounded_answer(payload: GenerationPayload) -> str:
    """Quote the best-matching context sentence per block, cited by block id."""
    if not payload.source_chunks:
        return NO_ANSWER_ANSWER

    query_terms = _terms(_query_text(payload))
    sentences: list[str] = []
    for block_id, chunk in enumerate(payload.source_chunks[:MAX_CITED_BLOCKS], start=1):
        sentence = _best_sentence(chunk.content, query_terms)
        if sentence is None:
            continue
        sentences.append(f"{sentence}[cite:{block_id}]")
    if not sentences:
        return NO_ANSWER_ANSWER
    return " ".join(sentences)


def _best_sentence(content: str, query_terms: set[str]) -> str | None:
    """Pick the context sentence with the most query-term overlap."""
    candidates = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", content) if part.strip()]
    if not candidates:
        return None
    scored = max(candidates, key=lambda sentence: len(_terms(sentence) & query_terms))
    if not _terms(scored) & query_terms:
        scored = candidates[0]
    trimmed = " ".join(scored.split()[:MAX_SENTENCE_WORDS])
    if not trimmed:
        return None
    if trimmed[0].islower():
        trimmed = trimmed[0].upper() + trimmed[1:]
    if trimmed[-1] not in ".!?":
        trimmed = f"{trimmed}."
    return trimmed


def _query_text(payload: GenerationPayload) -> str:
    """The question is appended last to the user content blocks."""
    for message in reversed(payload.messages):
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in reversed(content):
            if isinstance(block, dict) and block.get("type") == "text":
                return str(block.get("text", ""))
    return ""


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", text.lower()) if term not in _STOPWORDS}


def _payload_text(payload: GenerationPayload) -> str:
    parts: list[str] = []
    for block in payload.system:
        parts.append(str(block.get("text", "")))
    for message in payload.messages:
        content = message.get("content", [])
        if isinstance(content, list):
            parts.extend(str(block.get("text", "")) for block in content if isinstance(block, dict))
    return "\n".join(parts)


def _count_tokens(text: str) -> int:
    return len(text.split())
