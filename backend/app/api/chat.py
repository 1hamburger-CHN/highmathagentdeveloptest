import asyncio
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


@router.post("/stream")
async def chat_stream(payload: dict):
    """SSE streaming endpoint. Accepts user message, streams agent responses."""
    user_message = payload.get("message", "")
    session_id = payload.get("session_id", "default")

    async def event_generator():
        # Placeholder: Orchestrator will generate streaming events
        yield {"event": "start", "data": json.dumps({"session_id": session_id})}
        yield {"event": "message", "data": json.dumps({"role": "coach", "content": "你好！让我们开始今天的数学探索吧。"})}
        yield {"event": "done", "data": json.dumps({"status": "complete"})}

    return EventSourceResponse(event_generator())
