import json
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.agents.graph import build_tutor_graph
from app.agents.state import AgentState, TutorState
from app.core.safety import SafetyPipeline

logger = logging.getLogger(__name__)

router = APIRouter()

# Build the LangGraph graph once at module level
_tutor_graph = build_tutor_graph()

# Intermediate agents that work silently — their messages are hidden from user
# and stripped from shared history so downstream agents don't reference them
_SILENT_NODES = {"build_profile", "diagnose", "profile_check"}


@router.post("/stream")
async def chat_stream(payload: dict):
    """SSE streaming endpoint. Runs the full LangGraph tutoring pipeline."""
    user_message = payload.get("message", "")
    session_id = payload.get("session_id", uuid4().hex)
    user_id = payload.get("user_id", "anonymous")
    history = payload.get("history", [])
    existing_profile = payload.get("profile", None)

    # Belt-and-suspenders: safety check at endpoint level
    safety_result = SafetyPipeline.filter(user_message)
    if not safety_result["allowed"]:
        async def rejected_generator():
            yield {"event": "start", "data": json.dumps({"session_id": session_id})}
            yield {"event": "message", "data": json.dumps({"role": "assistant", "content": safety_result["content"], "node": "safety_check"}, ensure_ascii=False)}
            yield {"event": "done", "data": json.dumps({"status": "complete", "session_id": session_id})}
        return EventSourceResponse(rejected_generator())

    initial_state = TutorState(
        session_id=session_id,
        user_id=user_id,
        current_state=AgentState.INIT,
        messages=history + [{"role": "user", "content": user_message}],
        profile=existing_profile,
    )

    async def event_generator():
        yield {"event": "start", "data": json.dumps({"session_id": session_id})}

        try:
            final_state = None
            async for event in _tutor_graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    # Always send node progress so frontend shows spinner
                    yield {"event": "node", "data": json.dumps({"node": node_name})}

                    if isinstance(node_output, dict):
                        # Skip messages from background agents — only coach/generate speak to user
                        if node_name not in _SILENT_NODES:
                            msgs = node_output.get("messages", [])
                            for msg in msgs:
                                yield {
                                    "event": "message",
                                    "data": json.dumps({
                                        "role": msg.get("role", "assistant"),
                                        "content": msg.get("content", ""),
                                        "node": node_name,
                                    }, ensure_ascii=False),
                                }
                        if node_output.get("assessment_result"):
                            yield {
                                "event": "assessment",
                                "data": json.dumps(node_output["assessment_result"], ensure_ascii=False),
                            }
                        if node_output.get("generated_resources"):
                            yield {
                                "event": "resources",
                                "data": json.dumps(node_output["generated_resources"], ensure_ascii=False),
                            }
                    final_state = node_output

            yield {"event": "done", "data": json.dumps({"status": "complete", "session_id": session_id})}

        except Exception as e:
            logger.error(f"Chat stream error (session={session_id}): {type(e).__name__}: {e}")
            yield {"event": "error", "data": json.dumps({"message": "服务暂时不可用，请稍后重试"})}

    return EventSourceResponse(event_generator())


@router.post("/send")
async def chat_send(payload: dict):
    """Non-streaming endpoint: send a message and get the full response."""
    user_message = payload.get("message", "")
    user_id = payload.get("user_id", "anonymous")
    history = payload.get("history", [])
    existing_profile = payload.get("profile", None)

    safety_result = SafetyPipeline.filter(user_message)
    if not safety_result["allowed"]:
        return {"messages": [{"role": "assistant", "content": safety_result["content"]}], "rejected": True, "reason": safety_result["reason"]}

    initial_state = TutorState(
        session_id=uuid4().hex,
        user_id=user_id,
        current_state=AgentState.INIT,
        messages=history + [{"role": "user", "content": user_message}],
        profile=existing_profile,
    )

    try:
        final_state = await _tutor_graph.ainvoke(initial_state)
        return {
            "messages": final_state.get("messages", []),
            "profile": final_state.get("profile"),
            "assessment": final_state.get("assessment_result"),
            "resources": final_state.get("generated_resources"),
        }
    except Exception as e:
        logger.error(f"Chat send error (user={user_id}): {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="服务暂时不可用，请稍后重试")
