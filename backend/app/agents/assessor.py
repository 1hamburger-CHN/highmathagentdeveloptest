from app.agents.base import BaseAgent


class AssessorAgent(BaseAgent):
    """Evaluates student responses and identifies error patterns."""

    def __init__(self, model_router):
        super().__init__("assessor", model_router)

    async def run(self, state: dict) -> dict:
        return state
