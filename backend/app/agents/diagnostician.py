from app.agents.base import BaseAgent


class DiagnosticianAgent(BaseAgent):
    """Detects blind spots via concept graph analysis."""

    def __init__(self, model_router):
        super().__init__("diagnostician", model_router)

    async def run(self, state: dict) -> dict:
        return state
