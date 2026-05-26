"""Data models for the animation subsystem."""

from dataclasses import dataclass, field


@dataclass
class AnimationResource:
    mp4_url: str
    thumbnail_url: str | None = None
    duration_seconds: float = 0.0
    title: str = ""
    template_used: str = ""
    params: dict = field(default_factory=dict)


@dataclass
class AnimationRequest:
    concept_id: str
    error_type: str = ""
    wrong_model: str = ""
    correct_model: str = ""
