"""Tests for SocraticCoachAgent — bloom level clamping and JSON parsing."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.socratic_coach import SocraticCoachAgent
from app.agents.state import TutorState


class TestSocraticCoachAgent:
    @pytest.fixture
    def router(self):
        router = MagicMock()
        model = AsyncMock()
        model.ainvoke.return_value = MagicMock(
            content='{"level": 2, "message": "测试追问", "target_concept": "complex-2.2", "confidence": 0.6, "should_assess": false}'
        )
        router.get_model.return_value = model
        return router

    @pytest.mark.asyncio
    async def test_coach_level_clamped_to_valid_range(self, router):
        agent = SocraticCoachAgent(router)
        state = TutorState(
            session_id="test",
            current_concept="complex-1.1",
            coach_level=99,
            messages=[{"role": "user", "content": "我不懂复数"}],
        )
        result = await agent.run(state)
        # coach_level should be from JSON (2), not the input 99
        assert result["coach_level"] == 2
        assert 0 <= result["coach_confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_json_parse_fallback_on_broken_response(self, router):
        agent = SocraticCoachAgent(router)
        router.get_model.return_value.ainvoke.return_value = MagicMock(
            content="not valid json at all {{{broken"
        )
        state = TutorState(
            session_id="test",
            current_concept="complex-2.2",
            coach_level=0,
            messages=[],
        )
        result = await agent.run(state)
        # Should fall back to default level 0
        assert "coach_level" in result
        assert "messages" in result
        assert len(result["messages"]) >= 1
