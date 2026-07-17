"""Tests for ProfileService — Bayesian update and blind spot management."""
import pytest
from app.services.profile_service import ProfileService
from app.models.profile import LearningProfile, KnowledgeMastery


class TestProfileService:
    def test_create_default_profile(self):
        profile = ProfileService.create_default("user-1")
        assert profile.user_id == "user-1"
        assert profile.knowledge_mastery == []
        assert profile.blind_spots == []

    def test_bayesian_update_existing_concept(self):
        profile = LearningProfile(user_id="user-1")
        profile.knowledge_mastery.append(
            KnowledgeMastery(concept_id="complex-1.1", score=0.5, confidence=0.5)
        )
        ProfileService.update_knowledge_mastery(
            profile, "complex-1.1", score=0.8, confidence=0.9
        )
        km = profile.knowledge_mastery[0]
        # Bayesian: 0.3 * 0.5 + 0.7 * 0.8 = 0.15 + 0.56 = 0.71
        assert abs(km.score - 0.71) < 0.01
        # Bayesian: 0.3 * 0.5 + 0.7 * 0.9 = 0.15 + 0.63 = 0.78
        assert abs(km.confidence - 0.78) < 0.01

    def test_bayesian_update_new_concept(self):
        profile = LearningProfile(user_id="user-1")
        ProfileService.update_knowledge_mastery(
            profile, "complex-2.1", score=0.6, confidence=0.7
        )
        assert len(profile.knowledge_mastery) == 1
        assert profile.knowledge_mastery[0].concept_id == "complex-2.1"
        assert profile.knowledge_mastery[0].score == 0.6
