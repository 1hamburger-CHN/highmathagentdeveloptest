"""Base class for Manim animation templates."""

from abc import ABC, abstractmethod


class BaseManimTemplate(ABC):
    """Each template generates a Manim Scene from params extracted by LLM.

    Subclasses define concept_ids for rule-based matching and implement
    validate/build to handle parameterised animation generation.
    """
    template_name: str = ""
    concept_ids: list[str] = []
    scene_class_name: str = "AnimationScene"

    @abstractmethod
    def validate(self, params: dict) -> bool:
        """Check that extracted params are complete and valid."""

    @abstractmethod
    def build_scene_code(self, params: dict) -> str:
        """Return the full Python source code to render this animation.

        The returned string is written to a temp .py file, then rendered
        via ``manim -pql temp.py SceneClassName``.  Params are injected
        via ``json.loads(sys.argv[1])`` at the top of the file for safety.
        """
