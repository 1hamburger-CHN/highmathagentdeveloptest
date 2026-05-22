from app.agents.base import BaseAgent


class SocraticCoachAgent(BaseAgent):
    """L1/L2/L3 questioning engine with adaptive difficulty and flow control."""

    def __init__(self, model_router):
        super().__init__("socratic_coach", model_router)

    async def run(self, state: dict) -> dict:
        return state
