"""Manim animation templates for complex analysis concepts."""

from app.animation.templates.residue_theorem import ResidueTheoremTemplate
from app.animation.templates.conformal_mapping import ConformalMappingTemplate
from app.animation.templates.contour_integration import ContourIntegrationTemplate
from app.animation.templates.cr_equations import CREquationsTemplate
from app.animation.templates.taylor_series import TaylorSeriesTemplate
from app.animation.templates.laurent_series import LaurentSeriesTemplate
from app.animation.templates.pole_classification import PoleClassificationTemplate
from app.animation.templates.branch_cut import BranchCutTemplate
from app.animation.templates.riemann_sphere import RiemannSphereTemplate
from app.animation.templates.complex_plane_transform import ComplexPlaneTransformTemplate

ALL_TEMPLATES = [
    ResidueTheoremTemplate,
    ConformalMappingTemplate,
    ContourIntegrationTemplate,
    CREquationsTemplate,
    TaylorSeriesTemplate,
    LaurentSeriesTemplate,
    PoleClassificationTemplate,
    BranchCutTemplate,
    RiemannSphereTemplate,
    ComplexPlaneTransformTemplate,
]
