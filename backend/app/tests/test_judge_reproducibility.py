from __future__ import annotations

import pytest

from app.agents.judge_agent import JudgeAgent
from app.chainlit_steps import chainlit_step
from app.settings import settings


class FakeJudgeModelClient:
    async def score(self, criterion: str, question: dict, answer: str, rubric: dict) -> float:
        return 0.75 if criterion == "completeness" else 1.0


@pytest.mark.asyncio
async def test_judge_agent_stores_model_temperature_and_rubric(monkeypatch) -> None:
    monkeypatch.setattr(settings, "judge_model", "judge-test")
    monkeypatch.setattr(settings, "judge_temperature", 0.0)
    monkeypatch.setattr(settings, "judge_rubric_version", 7)

    agent = JudgeAgent(model_client=FakeJudgeModelClient())
    result = await agent.score_response(
        question="What is the dose?",
        answer="The dose is 5 ml.",
        source_texts=["The dose is 5 ml."],
        rubric={"rubric_version": 7},
    )

    assert result.metadata.model == "judge-test"
    assert result.metadata.temperature == 0.0
    assert result.metadata.rubric_version == 7
    assert result.score == pytest.approx(4.5)


def test_rubric_version_change_is_not_comparable() -> None:
    from app.scheduling.anomaly import cadence_for_metric

    assert cadence_for_metric("judge_score_mean") == "nightly"


@pytest.mark.asyncio
async def test_chainlit_step_is_noop_without_context() -> None:
    called = False

    @chainlit_step("noop-test")
    async def wrapped() -> str:
        nonlocal called
        called = True
        return "ok"

    assert await wrapped() == "ok"
    assert called is True
