"""Learning profile CRUD API backed by Turso/libsql."""
import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.db_models import (
    count_resources_by_type, count_total_resources,
    delete_sessions_for_user, delete_user, get_user, upsert_user,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ProfileUpdatePayload(BaseModel):
    profile: dict
    session_messages: list[dict] | None = None
    session_id: str | None = None


@router.get("/{user_id}")
async def get_profile(user_id: str):
    """Load a user's learning profile from the database."""
    try:
        user = get_user(user_id)
        if not user:
            return {"user_id": user_id, "profile": None, "is_new": True}
        profile_data = json.loads(user["profile_json"]) if user.get("profile_json") else {}
        # Attach resource usage stats for the summary card
        resource_counts = count_resources_by_type(user_id)
        profile_data["_stats"] = {
            "total_resources": count_total_resources(user_id),
            "resource_counts": resource_counts,
        }
        return {"user_id": user_id, "profile": profile_data, "is_new": False}
    except Exception as e:
        logger.error(f"Failed to load profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load profile")


@router.post("/{user_id}")
async def save_profile(user_id: str, payload: ProfileUpdatePayload):
    """Save or update a user's learning profile and optionally their session messages."""
    try:
        upsert_user(user_id, json.dumps(payload.profile, ensure_ascii=False))

        if payload.session_messages and payload.session_id:
            from app.models.db_models import upsert_session
            upsert_session(
                payload.session_id,
                user_id,
                json.dumps(payload.session_messages, ensure_ascii=False),
            )

        return {"user_id": user_id, "status": "saved"}
    except Exception as e:
        logger.error(f"Failed to save profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {e}")


@router.delete("/{user_id}")
async def delete_profile(user_id: str):
    """Delete a user's profile and all their session history."""
    try:
        delete_sessions_for_user(user_id)
        delete_user(user_id)
        return {"user_id": user_id, "status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete profile")
