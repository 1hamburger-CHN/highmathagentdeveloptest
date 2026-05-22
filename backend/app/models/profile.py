from pydantic import BaseModel, Field


class KnowledgeMastery(BaseModel):
    concept_id: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class BlindSpot(BaseModel):
    concept_id: str
    error_type: str  # concept/calculation/symbol/logic/prerequisite
    frequency: int = 1
    root_concept: str | None = None


class LearningBehavior(BaseModel):
    response_style: str = "cautious"  # cautious/exploratory/impulsive
    resource_preference: str = "visual"  # visual/textual/interactive


class LearningProfile(BaseModel):
    """v1: 3-dimension learning profile."""
    user_id: str
    knowledge_mastery: list[KnowledgeMastery] = Field(default_factory=list)
    blind_spots: list[BlindSpot] = Field(default_factory=list)
    behavior: LearningBehavior = Field(default_factory=LearningBehavior)
