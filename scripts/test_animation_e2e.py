"""End-to-end animation pipeline test.

Constructs a state where the coach has already detected a blind spot,
then runs animation_render → generate → respond through the graph.
"""
import asyncio, json, sys

sys.path.insert(0, "/app")

from app.agents.state import AgentState, TutorState
from app.agents.graph import build_tutor_graph


async def main():
    # Simulate: student already built profile, coach diagnosed blind spot
    # about residue theorem, confidence < 0.3
    state = TutorState(
        session_id="e2e_anim_test",
        user_id="e2e_anim_test",
        current_state=AgentState.COACH,
        messages=[
            {"role": "user", "content": "留数定理太难了，为什么围道里面有极点积分就不为零？"},
        ],
        profile={
            "knowledge_mastery": [
                {"concept_id": "complex-6.1", "title": "留数定义", "score": 0.2},
            ]
        },
        blind_spots=[
            {
                "concept_id": "complex-6.1",
                "title": "留数定义",
                "description": "学生不理解极点处的留数如何影响围道积分",
                "type": "conceptual",
            }
        ],
        coach_confidence=0.2,
        current_concept="complex-6.1",
        _animation_pending=True,
        _has_profile=True,
    )

    graph = build_tutor_graph()

    print("=== Starting animation E2E test ===")
    print(f"Initial: _animation_pending={state._animation_pending}")
    print(f"Blind spots: {state.blind_spots}")
    print(f"Concept: {state.current_concept}")

    # Build initial state dict from TutorState for graph invocation
    initial = {
        "session_id": state.session_id,
        "user_id": state.user_id,
        "current_state": state.current_state,
        "messages": list(state.messages),
        "profile": state.profile,
        "blind_spots": state.blind_spots,
        "coach_confidence": state.coach_confidence,
        "current_concept": state.current_concept,
        "_animation_pending": state._animation_pending,
        "_has_profile": state._has_profile,
        "_is_direct_question": False,
        "_is_resource_request": False,
        "_pending_out_of_domain_concept": "",
        "_safety_rejected": False,
        "_respond_directly": False,
        "quality_retries": 0,
        "assessment_result": None,
        "generated_resources": [],
        "learning_path": [],
        "animation_resource": None,
    }

    # Run just the animation_render → generate → respond path
    final = await graph.ainvoke(initial)

    # Check results
    animation_resource = final.get("animation_resource")
    messages = final.get("messages", [])

    print(f"\n=== Results ===")
    print(f"animation_resource: {animation_resource}")

    has_animation_msg = False
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        title = m.get("title", "")
        if role == "animation":
            has_animation_msg = True
            print(f"ANIMATION MESSAGE: url={content} title={title}")
        elif isinstance(content, str):
            print(f"[{role}] {content[:100]}...")

    print(f"\n=== Summary ===")
    print(f"Animation generated: {animation_resource is not None}")
    print(f"Animation in messages: {has_animation_msg}")

    if animation_resource:
        mp4_url = animation_resource.mp4_url if hasattr(animation_resource, 'mp4_url') else animation_resource.get('mp4_url', '')
        print(f"MP4 URL: {mp4_url}")
        print(f"E2E PIPELINE: OK")
        return True
    else:
        print(f"E2E PIPELINE: FAILED — no animation resource")
        return False


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
