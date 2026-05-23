"""Session persistence API — save/load/delete chat history."""
import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.db_models import Session, SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()


class SessionSavePayload(BaseModel):
    messages: list[dict]


@router.get("/{user_id}/latest")
async def load_latest_session(user_id: str):
    """Load the most recent session messages for a user."""
    db = SessionLocal()
    try:
        sess = (
            db.query(Session)
            .filter(Session.user_id == user_id)
            .order_by(Session.id.desc())
            .first()
        )
        if not sess or not sess.messages_json:
            return {"user_id": user_id, "session_id": None, "messages": [], "has_history": False}
        messages = json.loads(sess.messages_json) if sess.messages_json else []
        return {
            "user_id": user_id,
            "session_id": sess.id,
            "messages": messages,
            "has_history": len(messages) > 0,
        }
    except Exception as e:
        logger.error(f"Failed to load session for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load session")
    finally:
        db.close()


@router.post("/{user_id}/{session_id}")
async def save_session(user_id: str, session_id: str, payload: SessionSavePayload):
    """Save session messages for a user."""
    db = SessionLocal()
    try:
        sess = db.query(Session).filter(Session.id == session_id).first()
        if not sess:
            sess = Session(id=session_id, user_id=user_id, messages_json="[]")
            db.add(sess)
        sess.messages_json = json.dumps(payload.messages, ensure_ascii=False)
        db.commit()
        return {"session_id": session_id, "status": "saved"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save session")
    finally:
        db.close()


@router.delete("/{user_id}")
async def delete_all_sessions(user_id: str):
    """Delete all sessions for a user (profile deletion calls this too)."""
    db = SessionLocal()
    try:
        deleted = db.query(Session).filter(Session.user_id == user_id).delete()
        db.commit()
        return {"user_id": user_id, "deleted_count": deleted, "status": "deleted"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete sessions for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete sessions")
    finally:
        db.close()
