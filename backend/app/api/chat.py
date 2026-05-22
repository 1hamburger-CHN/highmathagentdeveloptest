import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.agents.graph import build_tutor_graph
from app.agents.state import AgentState, TutorState

router = APIRouter()

# Build the LangGraph graph once at module level
_tutor_graph = build_tutor_graph()


@router.post("/stream")
async def chat_stream(payload: dict):
    """SSE streaming endpoint. Runs the full LangGraph tutoring pipeline."""
    user_message = payload.get("message", "")
    session_id = payload.get("session_id", uuid4().hex)
    user_id = payload.get("user_id", "anonymous")
    history = payload.get("history", [])
    existing_profile = payload.get("profile", None)

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
                    # Extract messages to stream to client
                    if isinstance(node_output, dict):
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
                        # Stream assessment results
                        if node_output.get("assessment_result"):
                            yield {
                                "event": "assessment",
                                "data": json.dumps(node_output["assessment_result"], ensure_ascii=False),
                            }
                        # Stream generated resources
                        if node_output.get("generated_resources"):
                            yield {
                                "event": "resources",
                                "data": json.dumps(node_output["generated_resources"], ensure_ascii=False),
                            }
                    final_state = node_output

            yield {"event": "done", "data": json.dumps({"status": "complete", "session_id": session_id})}

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())


@router.post("/send")
async def chat_send(payload: dict):
    """Non-streaming endpoint: send a message and get the full response."""
    user_message = payload.get("message", "")
    user_id = payload.get("user_id", "anonymous")
    history = payload.get("history", [])
    existing_profile = payload.get("profile", None)

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
        raise HTTPException(status_code=500, detail=str(e))
