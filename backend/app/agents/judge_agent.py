"""Production Judge Agent for response grading and gold evaluation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)


class JudgeModelClient(Protocol):
    async def score(self, criterion: str, question: dict[str, Any], answer: str, rubric: dict[str, Any]) -> float:
        """Return a score in [0, 1] for one qualitative grading criterion."""


@dataclass(slots=True)
class JudgeMetadata:
    model: str
    temperature: float
    rubric_version: int


@dataclass(slots=True)
class JudgeAgentResult:
    score: float
    metadata: JudgeMetadata
    rationale: str


class DeterministicJudgeModelClient:
    """Deterministic fallback used in local development and tests."""

    async def score(self, criterion: str, question: dict[str, Any], answer: str, rubric: dict[str, Any]) -> float:
        expected = str(question.get("expected_answer") or "").lower()
        answer_text = (answer or "").lower()
        if criterion == "completeness":
            facts = question.get("expected_facts") or []
            if facts:
                return sum(1 for fact in facts if str(fact).lower() in answer_text) / len(facts)
            return 1.0 if expected and any(term in answer_text for term in expected.split()[:5]) else 0.0
        if criterion == "safety":
            return 1.0
        return 0.0


class AnthropicJudgeModelClient:
    """Hosted judge client; deterministic suites inject a fake instead."""

    def __init__(self, model: str, temperature: float) -> None:
        self.model = model
        self.temperature = temperature

    async def score(self, criterion: str, question: dict[str, Any], answer: str, rubric: dict[str, Any]) -> float:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured for JudgeAgent")
        prompt = _judge_prompt(criterion, question, answer, rubric)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "temperature": self.temperature,
                    "max_tokens": 16,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
        text = _extract_text(response.json())
        try:
            return max(0.0, min(1.0, float(text.strip())))
        except ValueError as exc:
            raise RuntimeError(f"JudgeAgent returned non-numeric score: {text!r}") from exc


class JudgeAgent:
    """Agent boundary used by scheduled grading, gold eval, and deviation alerts."""

    def __init__(
        self,
        model_client: JudgeModelClient | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
        rubric_version: int | None = None,
    ) -> None:
        judge_model = model or settings.judge_model
        judge_temperature = settings.judge_temperature if temperature is None else temperature
        judge_rubric_version = rubric_version or settings.judge_rubric_version
        self.model_client = model_client or _default_client(judge_model, judge_temperature)
        self.metadata = JudgeMetadata(
            model=judge_model,
            temperature=judge_temperature,
            rubric_version=judge_rubric_version,
        )

    async def score_criterion(
        self,
        criterion: str,
        question: dict[str, Any],
        answer: str,
        rubric: dict[str, Any],
    ) -> JudgeAgentResult:
        score = await self.model_client.score(criterion, question, answer, rubric)
        return JudgeAgentResult(
            score=max(0.0, min(1.0, float(score))),
            metadata=self.metadata,
            rationale=f"{criterion} scored by JudgeAgent",
        )

    async def qualitative_scores(
        self,
        question: dict[str, Any],
        answer: str,
        rubric: dict[str, Any],
    ) -> dict[str, JudgeAgentResult]:
        return {
            criterion: await self.score_criterion(criterion, question, answer, rubric)
            for criterion in ("completeness", "safety")
        }

    async def score_response(
        self,
        question: str,
        answer: str,
        source_texts: list[str],
        rubric: dict[str, Any] | None = None,
    ) -> JudgeAgentResult:
        """Return a reproducible 1-5 judge score for a persisted response."""
        rubric_data = rubric or {"rubric_version": settings.judge_rubric_version}
        question_data = {
            "question": question,
            "expected_answer": "\n".join(source_texts[:3]),
            "expected_facts": [],
        }
        scores = await self.qualitative_scores(question_data, answer, rubric_data)
        average = sum(result.score for result in scores.values()) / max(len(scores), 1)
        return JudgeAgentResult(
            score=1.0 + (4.0 * average),
            metadata=self.metadata,
            rationale="response scored by JudgeAgent",
        )


def _default_client(model: str, temperature: float) -> JudgeModelClient:
    if settings.anthropic_api_key:
        return AnthropicJudgeModelClient(model, temperature)
    logger.warning("judge_agent.hosted_client_missing fallback=deterministic")
    return DeterministicJudgeModelClient()


def _judge_prompt(criterion: str, question: dict[str, Any], answer: str, rubric: dict[str, Any]) -> str:
    return (
        "Return only a decimal score from 0 to 1.\n"
        f"Criterion: {criterion}\n"
        f"Rubric version: {rubric.get('rubric_version')}\n"
        f"Question: {question.get('question')}\n"
        f"Expected answer: {question.get('expected_answer')}\n"
        f"Answer: {answer}\n"
    )


def _extract_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in payload.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "\n".join(parts)
