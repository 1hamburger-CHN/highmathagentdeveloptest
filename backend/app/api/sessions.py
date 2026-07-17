"""Session persistence API — save/load/delete chat history."""
import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.db_models import delete_sessions_for_user, get_latest_session, list_resources, upsert_session

logger = logging.getLogger(__name__)

router = APIRouter()


class SessionSavePayload(BaseModel):
    messages: list[dict]


@router.get("/{user_id}/latest")
async def load_latest_session(user_id: str):
    """Load the most recent session messages for a user."""
    try:
        sess = get_latest_session(user_id)
        if not sess or not sess.get("messages_json"):
            return {"user_id": user_id, "session_id": None, "messages": [], "has_history": False}
        messages = json.loads(sess["messages_json"]) if sess["messages_json"] else []
        return {
            "user_id": user_id,
            "session_id": sess["id"],
            "messages": messages,
            "has_history": len(messages) > 0,
        }
    except Exception as e:
        logger.error(f"Failed to load session for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load session")


@router.post("/{user_id}/{session_id}")
async def save_session(user_id: str, session_id: str, payload: SessionSavePayload):
    """Save session messages for a user."""
    try:
        upsert_session(session_id, user_id, json.dumps(payload.messages, ensure_ascii=False))
        return {"session_id": session_id, "status": "saved"}
    except Exception as e:
        logger.error(f"Failed to save session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save session")


@router.get("/{user_id}/resources")
async def user_resources(user_id: str):
    """List all generated resources for a user."""
    try:
        resources = list_resources(user_id)
        return {"resources": resources}
    except Exception as e:
        logger.error(f"Failed to load resources for {user_id}: {e}")
        return {"resources": []}


@router.delete("/{user_id}")
async def delete_all_sessions(user_id: str):
    """Delete all sessions for a user."""
    try:
        deleted = delete_sessions_for_user(user_id)
        return {"user_id": user_id, "deleted_count": deleted, "status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete sessions for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete sessions")
