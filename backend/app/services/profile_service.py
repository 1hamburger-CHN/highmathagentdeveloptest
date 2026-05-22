from app.models.profile import KnowledgeMastery, LearningProfile


class ProfileService:
    """Bayesian update and management of learning profiles."""

    @staticmethod
    def create_default(user_id: str) -> LearningProfile:
        return LearningProfile(user_id=user_id)

    @staticmethod
    def update_knowledge_mastery(profile: LearningProfile, concept_id: str, score: float, confidence: float):
        """Bayesian update for knowledge mastery scores."""
        for km in profile.knowledge_mastery:
            if km.concept_id == concept_id:
                # Simple Bayesian update (weighted average)
                km.score = 0.3 * km.score + 0.7 * score
                km.confidence = 0.3 * km.confidence + 0.7 * confidence
                return
        profile.knowledge_mastery.append(KnowledgeMastery(concept_id=concept_id, score=score, confidence=confidence))

    @staticmethod
    def add_blind_spot(profile: LearningProfile, concept_id: str, error_type: str, root_concept: str | None = None):
        """Record a newly discovered blind spot."""
        from app.models.profile import BlindSpot
        for bs in profile.blind_spots:
            if bs.concept_id == concept_id and bs.error_type == error_type:
                bs.frequency += 1
                return
        profile.blind_spots.append(BlindSpot(concept_id=concept_id, error_type=error_type, root_concept=root_concept))
