"""Injectable generation client used by `/chat` and deterministic tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.agents.orchestrator import GenerationPayload
from app.chainlit_steps import chainlit_step
from app.settings import settings


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
    """Local deterministic fallback that never calls a hosted LLM."""

    @chainlit_step("generation", "llm")
    async def generate(self, payload: GenerationPayload, max_tokens: int) -> GenerationResult:
        context_text = _payload_text(payload)
        if not payload.source_chunks:
            answer = "I could not find document context to answer that safely."
        else:
            first = payload.source_chunks[0]
            snippet = " ".join(first.content.split()[:60])
            answer = f"Based on {first.document_filename}, {snippet}"
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
