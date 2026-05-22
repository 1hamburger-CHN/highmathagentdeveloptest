from app.agents.base import BaseAgent


class ProfileBuilderAgent(BaseAgent):
    """Builds 3-dim learning profile through 3-5 rounds of conversation."""

    def __init__(self, model_router):
        super().__init__("profile_builder", model_router)

    async def run(self, state: dict) -> dict:
        return state
