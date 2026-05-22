from app.agents.base import BaseAgent


class OrchestratorAgent(BaseAgent):
    """LangGraph Supervisor — routes intents and aggregates results."""

    def __init__(self, model_router):
        super().__init__("orchestrator", model_router)

    async def run(self, state: dict) -> dict:
        return state
