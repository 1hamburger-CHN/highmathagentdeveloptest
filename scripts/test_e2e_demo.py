"""E2E test: Complete demo story arc — diagnose -> coach -> generate -> assess.

Tests the full tutoring pipeline:
  1. First message triggers diagnosis (profile building)
  2. Resource generation via chat
  3. Profile persistence check

Usage:
    # Requires a running backend:
    #   docker compose up
    # or:
    #   cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

    python scripts/test_e2e_demo.py
"""

import json
import sys
import uuid

import requests

API = "http://localhost:8000"


def parse_sse(response):
    """Parse SSE stream into list of {event, data} dicts."""
    events = []
    buffer = ""
    for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
        if chunk is None:
            continue
        buffer += chunk if isinstance(chunk, str) else chunk.decode()
        while "\n\n" in buffer:
            event_text, buffer = buffer.split("\n\n", 1)
            event_type = "message"
            for line in event_text.split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        data = line[6:]
                    events.append({"event": event_type, "data": data})
    return events


def test_demo_story_arc():
    """Run the full demo story arc: diagnose, coach, generate, assess."""
    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    passed = 0
    total = 0

    # ------------------------------------------------------------------
    # Step 1: Send first message (triggers diagnose -> coach pipeline)
    # ------------------------------------------------------------------
    total += 1
    print("\n--- Step 1: First message (diagnose + coach) ---")
    resp = requests.post(
        f"{API}/api/chat/stream",
        json={
            "message": "什么是C-R方程？",  # 什么是C-R方程？
            "user_id": user_id,
            "session_id": session_id,
            "profile": None,
            "history": [],
        },
        stream=True,
        timeout=120,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    events = parse_sse(resp)
    assert len(events) > 0, "No SSE events received"
    assert any(e["event"] == "done" for e in events), (
        f"No 'done' event in stream. Events: {[e['event'] for e in events]}"
    )

    # Verify we got at least one assistant message
    assistant_msgs = [
        e for e in events
        if e["event"] == "message"
        and isinstance(e["data"], dict)
        and e["data"].get("role") in ("assistant", "coach")
    ]
    assert len(assistant_msgs) > 0, "No assistant messages in stream"
    print(f"  Received {len(assistant_msgs)} assistant messages")
    passed += 1
    print("  [PASS] Step 1: First message pipeline OK")

    # ------------------------------------------------------------------
    # Step 2: Extract profile from done event for session continuity
    # ------------------------------------------------------------------
    total += 1
    done_events = [e for e in events if e["event"] == "done"]
    profile_from_step1 = None
    if done_events and isinstance(done_events[-1]["data"], dict):
        profile_from_step1 = done_events[-1]["data"].get("profile")
    assert profile_from_step1 is not None, (
        "No profile returned in 'done' event"
    )
    print(f"  Profile has {len(profile_from_step1.get('knowledge_mastery', []))} mastery entries")
    passed += 1
    print("  [PASS] Step 2: Profile extracted from done event")

    # ------------------------------------------------------------------
    # Step 3: Generate a resource via chat
    # ------------------------------------------------------------------
    total += 1
    print("\n--- Step 3: Resource generation ---")

    # Build history from step 1 messages
    history = []
    for e in events:
        if e["event"] == "message" and isinstance(e["data"], dict):
            role = e["data"].get("role", "assistant")
            content = e["data"].get("content", "")
            if content:
                history.append({"role": role, "content": content})

    session_2 = str(uuid.uuid4())
    resp = requests.post(
        f"{API}/api/chat/stream",
        json={
            "message": "帮我生成C-R方程的讲义",  # 帮我生成C-R方程的讲义
            "user_id": user_id,
            "session_id": session_2,
            "profile": profile_from_step1,
            "history": history,
        },
        stream=True,
        timeout=120,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    events2 = parse_sse(resp)
    assert any(e["event"] == "done" for e in events2), "No 'done' event in step 3"

    # Check for resource generation evidence
    has_resource_event = any(e["event"] == "resources" for e in events2)
    has_resource_hint = any(
        "\U0001f4da" in e.get("data", {}).get("content", "")  # 📚
        or "讲义" in e.get("data", {}).get("content", "")  # 讲义
        for e in events2
        if isinstance(e.get("data"), dict)
    )
    if has_resource_event:
        print("  Resource event found in stream")
    if has_resource_hint:
        print("  Resource content hint found")

    # Not a hard fail — resource generation may need more context
    if has_resource_event or has_resource_hint:
        passed += 1
        print("  [PASS] Step 3: Resource generation triggered")
    else:
        print("  [WARN] Step 3: No resource event detected (may need more conversation turns)")

    # ------------------------------------------------------------------
    # Step 4: Check profile persistence via GET endpoint
    # ------------------------------------------------------------------
    total += 1
    print("\n--- Step 4: Profile persistence ---")
    resp = requests.get(f"{API}/api/profile/{user_id}", timeout=30)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "profile" in data, f"No 'profile' key in response: {list(data.keys())}"
    profile = data.get("profile")
    if profile is not None:
        mastery = profile.get("knowledge_mastery", [])
        print(f"  Profile persisted with {len(mastery)} knowledge entries")
        passed += 1
        print("  [PASS] Step 4: Profile persisted in database")
    else:
        print("  [WARN] Step 4: Profile is None (may not have been saved yet)")

    # ------------------------------------------------------------------
    # Step 5: Check session history persistence
    # ------------------------------------------------------------------
    total += 1
    print("\n--- Step 5: Session history ---")
    resp = requests.get(f"{API}/api/sessions/{user_id}/latest", timeout=30)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    sess_data = resp.json()
    has_history = sess_data.get("has_history", False)
    msg_count = len(sess_data.get("messages", []))
    print(f"  Session history: {msg_count} messages, has_history={has_history}")
    passed += 1
    print("  [PASS] Step 5: Session history endpoint OK")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'='*50}")
    print(f"RESULTS: {passed}/{total} passed")
    print(f"{'='*50}")
    return passed == total


if __name__ == "__main__":
    try:
        ok = test_demo_story_arc()
    except requests.exceptions.ConnectionError:
        print("\nERROR: Cannot connect to backend at http://localhost:8000")
        print("Make sure the backend is running:")
        print("  docker compose up")
        print("  or: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(2)
    except AssertionError as e:
        print(f"\nFAIL: {e}")
        sys.exit(1)
    sys.exit(0 if ok else 1)
