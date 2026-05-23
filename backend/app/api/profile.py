"""Learning profile CRUD API backed by SQLite."""
import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.db_models import Session, SessionLocal, User
from app.models.profile import LearningProfile

logger = logging.getLogger(__name__)

router = APIRouter()


class ProfileUpdatePayload(BaseModel):
    profile: dict
    session_messages: list[dict] | None = None
    session_id: str | None = None


def _profile_to_dict(profile: LearningProfile) -> dict:
    return profile.model_dump()


def _dict_to_profile(data: dict) -> LearningProfile:
    return LearningProfile(**data)


@router.get("/{user_id}")
async def get_profile(user_id: str):
    """Load a user's learning profile from the database."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"user_id": user_id, "profile": None, "is_new": True}
        profile_data = json.loads(user.profile_json) if user.profile_json else {}
        return {"user_id": user_id, "profile": profile_data, "is_new": False}
    except Exception as e:
        logger.error(f"Failed to load profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load profile")
    finally:
        db.close()


@router.post("/{user_id}")
async def save_profile(user_id: str, payload: ProfileUpdatePayload):
    """Save or update a user's learning profile and optionally their session messages."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, name="", profile_json="{}")
            db.add(user)

        user.profile_json = json.dumps(payload.profile, ensure_ascii=False)

        # Optionally save session messages
        if payload.session_messages and payload.session_id:
            sess = db.query(Session).filter(Session.id == payload.session_id).first()
            if not sess:
                sess = Session(id=payload.session_id, user_id=user_id, messages_json="[]")
                db.add(sess)
            sess.messages_json = json.dumps(payload.session_messages, ensure_ascii=False)

        db.commit()
        return {"user_id": user_id, "status": "saved"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save profile")
    finally:
        db.close()


@router.delete("/{user_id}")
async def delete_profile(user_id: str):
    """Delete a user's profile and all their session history."""
    db = SessionLocal()
    try:
        # Delete all sessions for this user
        db.query(Session).filter(Session.user_id == user_id).delete()
        # Delete the user/profile
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        return {"user_id": user_id, "status": "deleted"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete profile")
    finally:
        db.close()
