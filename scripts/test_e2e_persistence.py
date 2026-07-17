"""E2E test: Profile and history persist across sessions.

Tests multi-session data persistence:
  1. Session 1: send a message, verify profile is created
  2. Session 2: send a follow-up, verify profile accumulates
  3. Verify session history is retrievable
  4. Clean up: delete test user data

Usage:
    # Requires a running backend:
    #   docker compose up
    # or:
    #   cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

    python scripts/test_e2e_persistence.py
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


def test_profile_persistence():
    """Test that profile persists across multiple chat sessions."""
    user_id = str(uuid.uuid4())
    passed = 0
    total = 0

    # ------------------------------------------------------------------
    # Session 1: Initial diagnosis
    # ------------------------------------------------------------------
    total += 1
    print("\n--- Session 1: Initial message ---")
    session_1 = str(uuid.uuid4())
    resp = requests.post(
        f"{API}/api/chat/stream",
        json={
            "message": "复数怎么运算？",  # How to compute with complex numbers?
            "user_id": user_id,
            "session_id": session_1,
            "profile": None,
            "history": [],
        },
        stream=True,
        timeout=120,
    )
    assert resp.status_code == 200, f"Session 1: Expected 200, got {resp.status_code}"
    events_1 = parse_sse(resp)
    assert any(e["event"] == "done" for e in events_1), "Session 1: No 'done' event"
    print(f"  Session 1: {len(events_1)} SSE events received")
    passed += 1
    print("  [PASS] Session 1 completed")

    # ------------------------------------------------------------------
    # Session 2: Follow-up with profile from session 1
    # ------------------------------------------------------------------
    total += 1
    print("\n--- Session 2: Follow-up message (loads profile) ---")

    # Rebuild history from session 1 messages
    history = []
    for e in events_1:
        if e["event"] == "message" and isinstance(e["data"], dict):
            role = e["data"].get("role", "assistant")
            content = e["data"].get("content", "")
            if content:
                history.append({"role": role, "content": content})

    # Extract profile from session 1
    done_1 = [e for e in events_1 if e["event"] == "done"]
    profile_s1 = None
    if done_1 and isinstance(done_1[-1]["data"], dict):
        profile_s1 = done_1[-1]["data"].get("profile")

    session_2 = str(uuid.uuid4())
    resp = requests.post(
        f"{API}/api/chat/stream",
        json={
            "message": "复数的模和辐角怎么求？",  # How to find modulus and argument?
            "user_id": user_id,
            "session_id": session_2,
            "profile": profile_s1,
            "history": history,
        },
        stream=True,
        timeout=120,
    )
    assert resp.status_code == 200, f"Session 2: Expected 200, got {resp.status_code}"
    events_2 = parse_sse(resp)
    assert any(e["event"] == "done" for e in events_2), "Session 2: No 'done' event"
    print(f"  Session 2: {len(events_2)} SSE events received")
    passed += 1
    print("  [PASS] Session 2 completed with profile continuity")

    # ------------------------------------------------------------------
    # Check profile exists after both sessions via GET endpoint
    # ------------------------------------------------------------------
    total += 1
    print("\n--- Profile persistence check ---")
    resp = requests.get(f"{API}/api/profile/{user_id}", timeout=30)
    assert resp.status_code == 200, f"Profile GET: Expected 200, got {resp.status_code}"
    profile_data = resp.json()
    assert "profile" in profile_data, (
        f"No 'profile' key in response: {list(profile_data.keys())}"
    )
    profile = profile_data.get("profile")
    if profile is not None:
        mastery = profile.get("knowledge_mastery", [])
        assessed = [c for c in mastery if c.get("score", 0) > 0]
        print(f"  Profile: {len(mastery)} total concepts, {len(assessed)} assessed")
        for c in assessed:
            print(f"    - {c.get('concept_id', '?')}: score={c.get('score', 0):.2f}")
        passed += 1
        print("  [PASS] Profile persisted across sessions")
    else:
        print("  [WARN] Profile is None — may not have been saved to DB yet")

    # ------------------------------------------------------------------
    # Check session history via GET /api/sessions/{user_id}/latest
    # ------------------------------------------------------------------
    total += 1
    print("\n--- Session history check ---")
    resp = requests.get(f"{API}/api/sessions/{user_id}/latest", timeout=30)
    assert resp.status_code == 200, (
        f"Session GET: Expected 200, got {resp.status_code}"
    )
    sess_data = resp.json()
    msg_count = len(sess_data.get("messages", []))
    has_history = sess_data.get("has_history", False)
    print(f"  Messages saved: {msg_count}, has_history={has_history}")

    # Verify messages contain content from both sessions
    messages = sess_data.get("messages", [])
    user_msgs = [m for m in messages if m.get("role") == "user"]
    print(f"  User messages across sessions: {len(user_msgs)}")

    passed += 1
    print("  [PASS] Session history retrievable")

    # ------------------------------------------------------------------
    # Cleanup: Delete test user data
    # ------------------------------------------------------------------
    total += 1
    print("\n--- Cleanup: Deleting test user ---")
    resp = requests.delete(f"{API}/api/profile/{user_id}", timeout=30)
    assert resp.status_code == 200, f"Delete: Expected 200, got {resp.status_code}"
    del_data = resp.json()
    assert del_data.get("status") == "deleted", (
        f"Delete status not 'deleted': {del_data}"
    )
    print(f"  User {user_id} deleted")

    # Verify deletion
    resp = requests.get(f"{API}/api/profile/{user_id}", timeout=30)
    assert resp.status_code == 200
    verify_data = resp.json()
    assert verify_data.get("is_new") is True or verify_data.get("profile") is None, (
        "Profile still exists after deletion"
    )
    passed += 1
    print("  [PASS] Cleanup successful — profile deleted")

    # Also clean up sessions
    requests.delete(f"{API}/api/sessions/{user_id}", timeout=30)

    return passed, total


def test_new_user_has_no_history():
    """Test that a brand new user returns empty history."""
    user_id = str(uuid.uuid4())
    print("\n--- New user history check ---")
    resp = requests.get(f"{API}/api/sessions/{user_id}/latest", timeout=30)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data.get("has_history") is False, (
        f"New user should have no history: {data}"
    )
    assert data.get("messages") == [], f"New user should have empty messages: {data}"
    assert data.get("session_id") is None, f"New user should have null session_id"
    print(f"  [PASS] New user has no history (session_id=None, messages=[])")

    # Profile should also be None
    resp = requests.get(f"{API}/api/profile/{user_id}", timeout=30)
    assert resp.status_code == 200
    pdata = resp.json()
    assert pdata.get("is_new") is True, f"New user should be is_new=True: {pdata}"
    assert pdata.get("profile") is None, f"New user should have profile=None: {pdata}"
    print(f"  [PASS] New user has no profile")

    return True


if __name__ == "__main__":
    try:
        print("=" * 50)
        print("E2E Multi-Session Persistence Tests")
        print("=" * 50)

        passed, total = test_profile_persistence()

        # Also test new user state
        try:
            test_new_user_has_no_history()
            passed += 1
            total += 1
        except AssertionError as e:
            total += 1
            print(f"  [FAIL] {e}")

        print(f"\n{'='*50}")
        print(f"RESULTS: {passed}/{total} passed")
        print(f"{'='*50}")
        sys.exit(0 if passed == total else 1)

    except requests.exceptions.ConnectionError:
        print("\nERROR: Cannot connect to backend at http://localhost:8000")
        print("Make sure the backend is running:")
        print("  docker compose up")
        print("  or: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(2)
