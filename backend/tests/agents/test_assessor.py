"""Tests for AssessorAgent — schema validation and error handling."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.assessor import AssessorAgent
from app.agents.state import TutorState


class TestAssessorAgent:
    @pytest.fixture
    def router(self):
        router = MagicMock()
        model = AsyncMock()
        model.ainvoke.return_value = MagicMock(
            content='{"correct": true, "score": 0.85, "error_patterns": [], "recommendation": "pass", "summary": "good"}'
        )
        router.get_model.return_value = model
        return router

    @pytest.mark.asyncio
    async def test_assessment_result_has_required_fields(self, router):
        agent = AssessorAgent(router)
        state = TutorState(
            session_id="test",
            current_concept="complex-4.1",
            coach_level=1,
            messages=[
                {"role": "assistant", "content": "什么是复积分？"},
                {"role": "user", "content": "就是复数平面上的积分"},
            ],
        )
        result = await agent.run(state)
        assert "assessment_result" in result
        ar = result["assessment_result"]
        assert "correct" in ar
        assert "score" in ar
        assert "recommendation" in ar

    @pytest.mark.asyncio
    async def test_assessment_fallback_on_broken_json(self, router):
        agent = AssessorAgent(router)
        router.get_model.return_value.ainvoke.return_value = MagicMock(
            content="garbage not json"
        )
        state = TutorState(
            session_id="test",
            current_concept="complex-4.1",
            coach_level=1,
            messages=[],
        )
        result = await agent.run(state)
        ar = result["assessment_result"]
        assert ar["correct"] is True  # default fallback
        assert ar["score"] == 0.5
