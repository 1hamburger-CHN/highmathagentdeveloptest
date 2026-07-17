"""Tests for ResourceGeneratorAgent — KB enrichment and source labels."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.resource_generator import ResourceGeneratorAgent
from app.agents.state import TutorState


class TestResourceGeneratorAgent:
    @pytest.fixture
    def router(self):
        router = MagicMock()
        model = AsyncMock()
        model.ainvoke.return_value = MagicMock(
            content='{"resources": [{"type": "lecture", "title": "测试讲义", "content": "这是讲义内容"}]}'
        )
        router.get_model.return_value = model
        return router

    @pytest.fixture
    def retriever(self):
        ret = MagicMock()
        ret.resolve_concept_name.return_value = "复数定义与运算"
        ret.is_concept_in_domain.return_value = True
        ret.search_textbook.return_value = []
        ret.search_handouts.return_value = []
        ret.search_exercises.return_value = []
        return ret

    @pytest.mark.asyncio
    async def test_generate_resource_in_domain(self, router, retriever):
        agent = ResourceGeneratorAgent(router, retriever=retriever)
        state = TutorState(
            session_id="test",
            current_concept="complex-1.1",
            messages=[{"role": "user", "content": "帮我生成复数相关的讲义"}],
        )
        result = await agent.run(state)
        assert "messages" in result
        assert len(result["messages"]) >= 1

    @pytest.mark.asyncio
    async def test_sources_appended_to_last_message(self, router, retriever):
        retriever.search_textbook.return_value = [
            {"content": "复数是形如 a+bi 的数", "score": 0.9}
        ]
        agent = ResourceGeneratorAgent(router, retriever=retriever)
        state = TutorState(
            session_id="test",
            current_concept="complex-1.1",
            messages=[{"role": "user", "content": "帮我生成讲义"}],
        )
        result = await agent.run(state)
        last_msg = result["messages"][-1]["content"]
        # When sources are present, the last message should contain "参考来源"
        assert "参考来源" in last_msg
        assert "哈工大" in last_msg
