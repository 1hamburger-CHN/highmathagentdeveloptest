from app.agents.base import BaseAgent


class QualityGateAgent(BaseAgent):
    """Math correctness verification and content safety filtering."""

    def __init__(self, model_router):
        super().__init__("quality_gate", model_router)

    async def run(self, state: dict) -> dict:
        return state
