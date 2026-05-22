import json
from uuid import uuid4

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core.llm import ModelRouter

router = APIRouter()
model_router = ModelRouter()


@router.post("/stream")
async def chat_stream(payload: dict):
    """SSE streaming endpoint. Accepts user message, streams Orchestrator response."""
    user_message = payload.get("message", "")
    session_id = payload.get("session_id", uuid4().hex)
    history = payload.get("history", [])

    messages = history + [{"role": "user", "content": user_message}]

    async def event_generator():
        yield {"event": "start", "data": json.dumps({"session_id": session_id})}

        try:
            full_response = ""
            async for chunk in model_router.stream("orchestrator", messages):
                delta = chunk.message.content if hasattr(chunk, "message") else str(chunk)
                full_response += delta
                yield {"event": "message", "data": json.dumps({"role": "coach", "content": delta})}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}
            return

        yield {"event": "done", "data": json.dumps({"status": "complete", "content": full_response})}

    return EventSourceResponse(event_generator())
