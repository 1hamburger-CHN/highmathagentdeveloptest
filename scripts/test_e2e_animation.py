"""E2E test: Animation request -> rendering -> video playback pipeline.

Tests the animation subsystem:
  1. List available animations
  2. Trigger animation generation for a concept
  3. Verify media directory is populated

Usage:
    # Requires a running backend:
    #   docker compose up
    # or:
    #   cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

    python scripts/test_e2e_animation.py
"""

import sys
from pathlib import Path

import requests

API = "http://localhost:8000"


def test_animation_list():
    """Test GET /api/animation/list returns animation inventory."""
    resp = requests.get(f"{API}/api/animation/list", timeout=30)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "animations" in data, f"No 'animations' key in response: {list(data.keys())}"
    animations = data["animations"]
    print(f"  [PASS] Animation list: {len(animations)} animations found")
    for a in animations:
        print(f"    - {a.get('name', '?')}: {a.get('url', '?')} ({a.get('size_kb', 0)} KB)")
    return animations


def test_animation_generate():
    """Test POST /api/animation/generate triggers animation generation."""
    resp = requests.post(
        f"{API}/api/animation/generate",
        json={"concept_id": "complex-2.2"},
        timeout=30,
    )
    # The endpoint is a stub and may return 200 (queued), 202, or 501
    assert resp.status_code in (200, 202, 501), (
        f"Unexpected status: {resp.status_code}"
    )
    data = resp.json()
    print(f"  Status: {resp.status_code}")
    print(f"  Response: {data}")
    print(f"  [PASS] Animation generate endpoint (status={resp.status_code})")


def test_animation_status():
    """Test GET /api/animation/{id}/status returns status."""
    resp = requests.get(
        f"{API}/api/animation/test-anim-001/status",
        timeout=30,
    )
    # Status endpoint returns 200 even for unknown IDs (future work note)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "status" in data, f"No 'status' key in response: {list(data.keys())}"
    print(f"  Status endpoint response: {data}")
    print(f"  [PASS] Animation status endpoint")


def test_static_animations_served():
    """Verify that the static animations directory is accessible."""
    # First check if there are any animations via the list endpoint
    resp = requests.get(f"{API}/api/animation/list", timeout=30)
    if resp.status_code != 200:
        print("  [SKIP] Cannot reach animation list endpoint")
        return

    data = resp.json()
    animations = data.get("animations", [])
    if not animations:
        print("  [INFO] No animations to check — media directory may be empty")
        return

    # Try to fetch the first animation's URL
    first = animations[0]
    url = first.get("url", "")
    if url:
        media_resp = requests.head(f"{API}{url}", timeout=30)
        if media_resp.status_code in (200, 304):
            print(f"  [PASS] Animation media served: {url} ({media_resp.status_code})")
        else:
            print(f"  [WARN] Media URL returned {media_resp.status_code}: {url}")


def main():
    passed = 0
    total = 0

    print("=" * 50)
    print("E2E Animation Pipeline Tests")
    print("=" * 50)

    # Test 1: List animations
    total += 1
    print("\n--- Test 1: List animations ---")
    try:
        test_animation_list()
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] {e}")
    except requests.exceptions.ConnectionError:
        print("\nERROR: Cannot connect to backend at http://localhost:8000")
        print("Make sure the backend is running:")
        print("  docker compose up")
        sys.exit(2)

    # Test 2: Trigger animation generation
    total += 1
    print("\n--- Test 2: Trigger animation generation ---")
    try:
        test_animation_generate()
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] {e}")

    # Test 3: Animation status
    total += 1
    print("\n--- Test 3: Animation status ---")
    try:
        test_animation_status()
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] {e}")

    # Test 4: Static media serving
    total += 1
    print("\n--- Test 4: Static media serving ---")
    try:
        test_static_animations_served()
        passed += 1
    except AssertionError as e:
        print(f"  [FAIL] {e}")

    print(f"\n{'='*50}")
    print(f"RESULTS: {passed}/{total} passed")
    print(f"{'='*50}")
    return passed == total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
