"""Standalone Manim template render test — runs inside container."""
import sys, os, json, tempfile, subprocess
from pathlib import Path

sys.path.insert(0, "/app")

from app.animation.templates.residue_theorem import ResidueTheoremTemplate
from app.animation.templates.conformal_mapping import ConformalMappingTemplate
from app.animation.templates.contour_integration import ContourIntegrationTemplate

TEST_CASES = [
    (
        ResidueTheoremTemplate(),
        {"poles": ["i", "-i"], "inside_poles": ["i"], "contour_radius": 2.0},
    ),
    (
        ConformalMappingTemplate(),
        {"function": "z**2", "domain": "单位圆盘 |z|<1"},
    ),
    (
        ContourIntegrationTemplate(),
        {"contour": "circle", "integrand": "f(z) = 1/z", "radius": 2},
    ),
]

RESULTS = []
for template, params in TEST_CASES:
    name = template.template_name
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Params: {json.dumps(params, ensure_ascii=False)}")

    if not template.validate(params):
        print(f"  FAIL: param validation failed")
        RESULTS.append((name, "FAIL", "validation"))
        continue

    code = template.build_scene_code(params)
    print(f"  Code generated: {len(code)} bytes")

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", prefix="manim_", delete=False, encoding="utf-8",
    )
    tmp.write(code)
    tmp.close()
    tmp_path = Path(tmp.name)

    try:
        result = subprocess.run(
            ["manim", "-pql", str(tmp_path), template.scene_class_name],
            capture_output=True, text=True, timeout=180,
            cwd="/tmp",
        )
        if result.returncode == 0:
            mp4_files = list(Path("/tmp/media/videos").rglob(
                f"{template.scene_class_name}.mp4"
            ))
            if mp4_files:
                size_kb = mp4_files[0].stat().st_size / 1024
                print(f"  OK: {mp4_files[0]} ({size_kb:.1f} KB)")
                RESULTS.append((name, "OK", str(mp4_files[0])))
            else:
                print(f"  FAIL: no mp4 found")
                print(f"  stdout tail: {result.stdout[-500:]}")
                RESULTS.append((name, "FAIL", "no_mp4"))
        else:
            print(f"  FAIL: manim exit {result.returncode}")
            print(f"  stderr tail: {result.stderr[-500:]}")
            RESULTS.append((name, "FAIL", f"exit_{result.returncode}"))
    except subprocess.TimeoutExpired:
        print(f"  FAIL: timeout (180s)")
        RESULTS.append((name, "FAIL", "timeout"))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

print(f"\n{'='*60}")
print("SUMMARY:")
all_ok = True
for name, status, detail in RESULTS:
    print(f"  {status}: {name} — {detail}")
    if status != "OK":
        all_ok = False
print(f"\nOverall: {'ALL PASSED' if all_ok else 'SOME FAILED'}")
sys.exit(0 if all_ok else 1)
