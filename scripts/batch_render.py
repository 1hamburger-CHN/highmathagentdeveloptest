"""Batch render all Manim templates with default params."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, '/opt/mathagent/backend')

from app.animation.renderer import ManimRenderer
from app.animation.templates import ALL_TEMPLATES

DEFAULT_PARAMS = {
    "ResidueTheorem": {"poles": ["i", "-i"], "inside_poles": ["i"], "contour_radius": 2.0},
    "ConformalMapping": {"function": "z**2", "domain": "单位圆盘 |z|<1"},
    "ContourIntegration": {"contour": "circle", "integrand": "f(z) = 1/z", "radius": 2.0},
    "CREquations": {"function": "z**2", "point": "1+i"},
    "TaylorSeries": {"function": "exp(z)", "center": "0", "terms": 5},
    "LaurentSeries": {"function": "1/(z*(z-1))", "inner_radius": 0.5, "outer_radius": 2.0},
    "PoleClassification": {"singularities": [
        {"type": "removable", "point": "0", "label": "可去奇点: sin(z)/z"},
        {"type": "pole", "point": "0", "label": "极点: 1/z"},
        {"type": "essential", "point": "0", "label": "本性奇点: exp(1/z)"},
    ]},
    "BranchCut": {"function": "Ln(z)"},
    "RiemannSphere": {"function": "z"},
    "ComplexPlaneTransform": {"function": "z+1"},
}

async def main():
    renderer = ManimRenderer()
    for template_cls in ALL_TEMPLATES:
        template = template_cls()
        params = DEFAULT_PARAMS.get(template.template_name, {})
        if not template.validate(params):
            print(f"SKIP {template.template_name}: default params invalid")
            continue
        cache_key = hashlib.sha256(
            json.dumps({"t": template.template_name, "p": params}, sort_keys=True).encode()
        ).hexdigest()[:12]
        cache_path = Path("static/animations") / f"{template.template_name}_{cache_key}.mp4"
        if cache_path.exists():
            print(f"SKIP {template.template_name}: already rendered ({cache_path.name})")
            continue
        print(f"RENDERING {template.template_name}...")
        result = await renderer.render(template, params)
        if result:
            print(f"  DONE: {result.mp4_url}")
        else:
            print(f"  FAILED: {template.template_name}")

if __name__ == "__main__":
    asyncio.run(main())
